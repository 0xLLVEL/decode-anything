"""Full static opcode dump for IonCube PHP 8.1-8.4 plain-encoded files.

Decodes all top-level functions and the main script block from an encoded
PHP file that uses no per-function dynamic keys.  Produces:
  - <stem>.icdump.json    normalized icdump-ir-v1 (all methods)
  - <stem>.icdump.txt     human-readable opcode listing (all methods)

Usage:
    python dump_plain_file_static.py sample.php [--out-dir DIR]
"""

from __future__ import annotations

import argparse
import json
import re
import struct
import sys
from dataclasses import asdict
from pathlib import Path

from decode_hrc_header import decode_file, decode_payload_body, read_encoded_payload
from loader_static_to_icdump_ir import (
    build_op_array_entry,
    resolve_function_calls,
    safe_value,
)
from decode_php_body import (
    LoaderHandlerTables,
    LoaderInternedStringResolver,
    apply_php81_handler_opcode_decode,
    build_php81_opcode_xor_stream,
    decode_encoded_zval,
    decode_opcode_block,
    decrypt_cipher0,
    dynamic_fallback_cipher0_key,
    extract_dynamic_main_record,
    handler_key_dword_for_index,
    load_opcode_names,
    read_inner_op_array_record,
    resolve_interned_literal_strings,
    resolve_interned_type_names,
    render_opcode_text,
    ParseError,
)

_DEFAULT_DLL_PATHS = [
    Path(__file__).resolve().parents[1] / "runtime" / "ext" / "ioncube_loader_win_8.1.dll",
    Path(__file__).resolve().parent / "ioncube_loader_win_8.1.dll",
]


def _load_handler_tables(dll_path: Path | None, php_version: int = 81) -> LoaderHandlerTables | None:
    candidates = [dll_path] if dll_path else (_DEFAULT_DLL_PATHS if php_version == 81 else [])
    for p in candidates:
        if p and p.exists():
            try:
                ht = LoaderHandlerTables.from_dll(p, php_version=php_version)
                print(f"handler tables: {p.name}")
                return ht
            except Exception as exc:
                print(f"  warning: handler tables failed for {p}: {exc}")
    print("handler tables: not available (opcodes will not be handler-lane decoded)")
    return None


def _detect_handler_variant(
    handler_tables: LoaderHandlerTables,
    decoded,
    xor_stream,
) -> int:
    """Try all 7 handler variants; return the one with fewest ambiguous decodes (ties: most ok)."""
    import struct as _struct

    def u32(v: int) -> int:
        return v & 0xFFFFFFFF

    opcodes = decoded.opcodes
    opcode_count = len(opcodes)

    best_variant = 0
    best_ambig = 10 ** 9
    best_ok = -1

    for variant in range(len(handler_tables.VARIANT_TABLES)):
        ok = 0
        ambig = 0
        for i, opline in enumerate(opcodes):
            if opline.handler_word is None:
                continue
            hk = handler_key_dword_for_index(xor_stream.key_bytes, opcode_count, i)
            if opline.handler_word == u32(~hk):
                continue  # direct-handler — always correct
            next_opline = opcodes[i + 1] if i + 1 < opcode_count else None
            try:
                hidx = handler_tables.decode_handler_index(opline.handler_word, hk, variant)
                cands = handler_tables.opcode_candidates_for_handler_index(hidx, opline, next_opline)
                if len(cands) == 1:
                    ok += 1
                else:
                    ambig += 1
            except Exception:
                ambig += 1

        if ambig < best_ambig or (ambig == best_ambig and ok > best_ok):
            best_ambig = ambig
            best_ok = ok
            best_variant = variant

    print(f"handler variant: {best_variant}  (ok={best_ok}, ambig={best_ambig})")
    return best_variant


def _parse_try_catch_records(raw_bytes: bytes) -> list[dict]:
    """Parse raw 16-byte try/catch records: [try_op, catch_op, finally_op, finally_end].

    In IonCube's encoding the values are 1-based opline indices; 0 means "not present".
    catch_op/finally_op/finally_end of 0 → None so IR consumers skip the entry
    instead of matching opline 0.
    """
    entries = []
    count = len(raw_bytes) // 16
    for i in range(count):
        t, c, f, fe = struct.unpack_from("<IIII", raw_bytes, i * 16)
        entries.append({
            "try_op":      t - 1 if t else 0,
            "catch_op":    (c - 1) if c else None,
            "finally_op":  (f - 1) if f else None,
            "finally_end": (fe - 1) if fe else None,
        })
    return entries


def _materialize_switch_literals(literals: list[dict], opcodes: list[dict]) -> None:
    """Apply Zend's x86 relative-offset conversion to switch jump tables."""

    for op in opcodes:
        if op.get("opcode") not in (187, 188, 195):
            continue
        op2 = op.get("op2")
        literal_index = op2.get("literal_index") if isinstance(op2, dict) else None
        if not isinstance(literal_index, int) or not 0 <= literal_index < len(literals):
            continue
        value = literals[literal_index].get("value")
        op_index = op.get("index")
        if not isinstance(op_index, int):
            continue

        def materialize(target):
            return (target - op_index) * 28 if type(target) is int else target

        if isinstance(value, list):
            literals[literal_index]["value"] = [materialize(item) for item in value]
        elif isinstance(value, dict):
            literals[literal_index]["value"] = {
                key: materialize(item) for key, item in value.items()
            }


def _load_resolver(dll_path: Path | None, php_version: int = 81) -> LoaderInternedStringResolver | None:
    candidates = [dll_path] if dll_path else (_DEFAULT_DLL_PATHS if php_version == 81 else [])
    for p in candidates:
        if p and p.exists():
            try:
                r = LoaderInternedStringResolver.from_dll(p, php_version=php_version)
                print(f"interned-string resolver: {p.name}")
                return r
            except Exception as exc:
                print(f"  warning: resolver failed for {p}: {exc}")
    print("interned-string resolver: not available (null literals will remain unresolved)")
    return None


def _parse_function_records(body: bytes, *, php_flags: int, start_offset: int, count: int):
    """Yield (name, DynamicMainRecord) for each of *count* plain function records."""
    offset = start_offset
    for _ in range(count):
        rec = extract_dynamic_main_record(
            b"\x00\x00\x00\x00" + body[offset:],
            php_flags=php_flags,
            offset=0,
        )
        real_blob_offset = offset + rec.blob_offset - 4
        real_end         = offset + rec.end_offset   - 4
        rec.start_offset = offset
        rec.blob_offset  = real_blob_offset
        rec.end_offset   = real_end
        yield rec.table_name or f"<fn@{offset:#x}>", rec
        offset = real_end


def _decrypt_blob(rec):
    """Try plain → cipher0-fallback.  Returns (blob, state_str, inner)."""
    try:
        inner = read_inner_op_array_record(rec.blob, outer=rec)
        return rec.blob, "plain", inner
    except ParseError:
        pass
    blob = decrypt_cipher0(rec.blob, dynamic_fallback_cipher0_key())
    try:
        inner = read_inner_op_array_record(blob, outer=rec)
        return blob, "cipher0-fallback", inner
    except ParseError:
        return blob, "failed", None


def _detect_dynamic_cipher_type(rec) -> str:
    """Detect IonCube dynamic-key cipher type from blob geometry.

    IonCube Rijndael ("random") encryption prepends a 16-byte IV, making
    blob_len = blob_tag + 16.  Seed-based ("basic") stream ciphers have no
    block overhead, so blob_len == blob_tag.
    """
    blob_len = len(rec.blob)
    if blob_len == rec.blob_tag + 16:
        return "random"
    if blob_len == rec.blob_tag:
        return "basic"
    return f"unknown(tag={rec.blob_tag:#x},len={blob_len})"


def _make_stub_raw(rec, cipher_type: str) -> dict:
    """Build a minimal raw dict for a dynamic-key function that could not be decoded."""
    md = rec.metadata
    variables = list(md.variables) if md.variables else []
    num_args = md.num_args or 0

    opcodes = []
    for i in range(num_args):
        var = variables[i] if i < len(variables) else f"arg{i}"
        opcodes.append({
            "index": i,
            "lineno": md.line_start or 0,
            "opcode": 63, "opcode_name": "ZEND_RECV",
            "op1": {"type": 0, "type_name": "IS_UNUSED", "serialized_value": i + 1, "zend_value": i + 1},
            "op2": {"type": 0, "type_name": "IS_UNUSED", "serialized_value": 0, "zend_value": 0},
            "result": {
                "type": 8, "type_name": "IS_CV",
                "serialized_value": i, "zend_value": i,
                "variable_index": i, "variable_name": f"${var}",
            },
            "extended_value": 0, "handler_word": None,
        })

    opcodes.append({
        "index": num_args,
        "lineno": md.line_end or 0,
        "opcode": 62, "opcode_name": "ZEND_RETURN",
        "op1": {"type": 1, "type_name": "IS_CONST", "serialized_value": 0, "zend_value": 0, "literal_index": 0},
        "op2": {"type": 0, "type_name": "IS_UNUSED", "serialized_value": 0, "zend_value": 0},
        "result": {"type": 0, "type_name": "IS_UNUSED", "serialized_value": 0, "zend_value": 0},
        "extended_value": 0, "handler_word": None,
    })

    null_literal = {
        "index": 0, "type": 1, "type_name": "IS_NULL",
        "raw_type_info": 0, "raw_fields": [0, 0, 0], "value": None,
        "encoded_payload": None, "string_offset": None, "string_offset_raw": None,
        "string_length": None, "string_flags": 0, "unresolved": None,
    }

    return {
        "method": rec.table_name,
        "table_name": rec.table_name,
        "record_start": rec.start_offset,
        "blob_offset": rec.blob_offset,
        "blob_length": len(rec.blob),
        "temp_variable_count": rec.temp_variable_count,
        "outer_key_words": [f"0x{w:08X}" for w in (rec.outer_key_words or (0, 0))],
        "metadata": {
            "last_var": md.last_var,
            "literal_count": 1,
            "fn_flags": md.fn_flags,
            "line_start": md.line_start,
            "line_end": md.line_end,
            "num_args": num_args,
            "required_num_args": md.required_num_args or num_args,
            "variables": variables,
            "arg_type_info": [],
        },
        "opcode_xor_stream": {"request_key": "0x00000000", "seed_a": "0x00000000", "seed_b": "0x00000000", "source": "none"},
        "try_catch_raw": [],
        "literals": [null_literal],
        "opcodes": opcodes,
        "dynamic_key_stub": True,
        "dynamic_key_cipher_type": cipher_type,
        "status": {"failed": True, "reason": f"dynamic_key:{cipher_type}", "blob_tag": rec.blob_tag, "blob_len": len(rec.blob)},
    }



# The serialized IS_LONG adjustment is part of the target PHP ABI, not the
# serialization version or php_flags (8.1 and 8.4 can share both while using
# different rules). Confirmed against the same source encoded for 8.1..8.4:
#   8.1:     ZEND_ASSIGN_OP stores value + 2
#   8.2/8.3: ZEND_ASSIGN and ZEND_ASSIGN_OP store value + 2
#   8.4:     both store the value verbatim
# Unknown/newer ABIs therefore default to no adjustment.
_ASSIGN_INT_BIAS_BY_PHP_VERSION = {
    81: {"ZEND_ASSIGN_OP": 2},
    82: {"ZEND_ASSIGN": 2, "ZEND_ASSIGN_OP": 2},
    83: {"ZEND_ASSIGN": 2, "ZEND_ASSIGN_OP": 2},
}


def _unbias_assign_int_literals(decoded, literals, *, php_version: int) -> None:
    """Normalize ABI-specific assignment biases in serialized IS_LONG values."""
    biases = _ASSIGN_INT_BIAS_BY_PHP_VERSION.get(php_version, {})
    adjusted: set[int] = set()
    for op in decoded.opcodes:
        bias = biases.get(op.opcode_name, 0)
        if not bias:
            continue
        if op.op2.type_name != "IS_CONST" or op.op2.literal_index is None:
            continue
        idx = op.op2.literal_index
        if idx in adjusted:
            continue
        if 0 <= idx < len(literals):
            lit = literals[idx]
            if lit.type == 4 and isinstance(lit.value, int):
                lit.value -= bias
                adjusted.add(idx)


def _dump_function(
    rec,
    inner,
    *,
    request_key: int,
    serialization_version: int,
    opcode_names: dict,
    handler_tables: LoaderHandlerTables | None = None,
    handler_variant: int | None = None,
    php_flags: int = 0,
    php_version: int = 81,
):
    """Decode opcodes and return (raw_dict, text_str)."""
    xor_stream = build_php81_opcode_xor_stream(
        inner.block, inner.metadata,
        outer=rec,
        request_key=request_key,
        serialization_version=serialization_version,
        header_flags=php_flags,
    )
    decoded = decode_opcode_block(
        inner.block, inner.metadata,
        serialization_version=serialization_version,
        opcode_xor=xor_stream.xor_bytes,
        opcode_names=opcode_names,
        header_flags=php_flags,
    )

    if handler_tables is not None and handler_variant is not None and serialization_version >= 6:
        apply_php81_handler_opcode_decode(
            decoded,
            opcode_xor_stream=xor_stream,
            handler_tables=handler_tables,
            handler_variant=handler_variant,
            opcode_names=opcode_names,
        )

    _unbias_assign_int_literals(
        decoded,
        inner.literals,
        php_version=php_version,
    )

    try_catch = _parse_try_catch_records(inner.try_catch_records)
    literals = [asdict(lit) for lit in inner.literals]
    opcodes = decoded.to_dict()["opcodes"]
    _materialize_switch_literals(literals, opcodes)
    for index, op in enumerate(opcodes):
        if index < len(xor_stream.raw_opcode_bytes):
            op["opcode_raw_byte"] = xor_stream.raw_opcode_bytes[index]

    raw = {
        "method": inner.metadata.function_name or rec.table_name,
        "table_name": rec.table_name,
        "record_start": rec.start_offset,
        "blob_offset": rec.blob_offset,
        "blob_length": len(rec.blob),
        "temp_variable_count": rec.temp_variable_count,
        "outer_key_words": [f"0x{w:08X}" for w in (rec.outer_key_words or (0, 0))],
        "metadata": {
            "last_var": inner.metadata.last_var,
            "literal_count": inner.metadata.literal_count,
            "fn_flags": inner.metadata.fn_flags,
            "line_start": inner.metadata.line_start,
            "line_end": inner.metadata.line_end,
            "num_args": inner.metadata.num_args,
            "required_num_args": inner.metadata.required_num_args,
            "variables": inner.metadata.variables,
            "arg_type_info": inner.arg_type_info,
        },
        "opcode_xor_stream": {
            "request_key": f"0x{xor_stream.request_key:08X}",
            "seed_a": f"0x{xor_stream.seed_a:08X}",
            "seed_b": f"0x{xor_stream.seed_b:08X}",
            "source": xor_stream.source,
        },
        "try_catch_raw": try_catch,
        "literals": literals,
        "opcodes": opcodes,
    }
    text = _render_function_text(rec, inner, literals, decoded)
    return raw, text


def _render_function_text(rec, inner, literals, decoded):
    lines = [
        f"function {inner.metadata.function_name or rec.table_name or '<main>'}",
        f"  lines:    {inner.metadata.line_start}..{inner.metadata.line_end}",
        f"  opcodes:  {inner.block.opcode_count}",
        f"  literals: {inner.metadata.literal_count}",
        f"  args:     {inner.metadata.num_args} (required {inner.metadata.required_num_args})",
        "",
        "variables:",
    ]
    for idx, name in enumerate(inner.metadata.variables):
        lines.append(f"  CV{idx}: ${name}")
    lines += ["", "literals:"]
    for lit in literals:
        v = lit.get("value")
        lines.append(f"  [{lit['index']:3d}] {lit['type_name']:12s} = {v!r}")
    lines += ["", "opcodes:"]
    lines.append(render_opcode_text(decoded).rstrip())
    return "\n".join(lines) + "\n"


def _read_serialized_string_at(buf: bytes, off: int) -> "tuple[bytes | None, int]":
    """Port of the loader's serialized-string reader (8.3 ``sub_1009FD70``).

    Layout: ``u32 raw``; bit ``0x80000000`` marks a null string (no payload);
    otherwise the byte length is ``raw & 0x9FFFFFFF`` (the ``0x20000000`` bit is
    a no-rehash flag, not part of the length). Returns ``(bytes|None, next_off)``.
    """
    if off + 4 > len(buf):
        raise ParseError("eof reading serialized-string length")
    raw = struct.unpack_from("<I", buf, off)[0]
    off += 4
    if raw & 0x80000000:
        return None, off  # null sentinel
    ln = raw & 0x9FFFFFFF
    if off + ln > len(buf):
        raise ParseError(f"serialized-string length {ln} out of range")
    return buf[off:off + ln], off + ln


def _parse_class_record_header(buf: bytes, off: int) -> dict:
    """Structural parse of a class record header — port of ``sub_100A2D30``
    up to the method table. No heuristics; this is the loader's exact layout:

      u8                       class kind
      serialized-string        class name
      u32                      ce_flags
      serialized-string|null   parent name
      u16 n + (n+1) bytes      lowercased-name / source-location blob (sub_100A2500)
      u32                      interface count           (ce+268)
      serialized-string × N    interface names           (sub_100A2CB0)
      u16                      method count (incl. inherited)

    Returns a dict; ``first_method_offset`` is where the method records begin.
    """
    start = off
    kind = buf[off]
    off += 1
    name, off = _read_serialized_string_at(buf, off)
    ce_flags = struct.unpack_from("<I", buf, off)[0]
    off += 4
    parent, off = _read_serialized_string_at(buf, off)

    blob_n = struct.unpack_from("<H", buf, off)[0]
    off += 2
    if blob_n:
        off += (blob_n + 1) & 0xDFFFFFFF  # sub_1000A050 read size

    iface_count = struct.unpack_from("<I", buf, off)[0]
    off += 4
    if iface_count > 0x10000:
        raise ParseError(f"implausible interface count {iface_count}")
    interfaces: list[bytes] = []
    for _ in range(iface_count):
        s, off = _read_serialized_string_at(buf, off)
        if s is not None:
            interfaces.append(s)

    method_count = struct.unpack_from("<H", buf, off)[0]
    off += 2
    return {
        "start": start,
        "kind": kind,
        "name": name,
        "ce_flags": ce_flags,
        "parent": parent,
        "interfaces": interfaces,
        "method_count": method_count,
        "first_method_offset": off,
    }


def _decode_class_name(raw: bytes | None, fallback: str | None) -> str | None:
    """Return a valid PHP identifier from a (possibly obfuscated) name blob."""
    if raw:
        try:
            text = raw.decode("ascii")
        except UnicodeDecodeError:
            text = ""
        if text and re.fullmatch(r"\\?[A-Za-z_\x80-\xff][A-Za-z0-9_\\\x80-\xff]*", text):
            return text
    return fallback


# ── class-record tail parser ───────────────────────────────────────────────
# Exact port of sub_100A2D30's tail (everything after the method table):
# default-value tables, properties, constants, trait uses, attributes, and the
# class doc-comment. Parsing it consumes the precise byte count so the next
# class record begins exactly where this one ends — the basis for multi-class
# files. Helpers below mirror the loader's stream primitives.

def _read_buffer_value_at(buf: bytes, off: int) -> "tuple[bytes | None, int]":
    """Port the loader buffer reader (sub_1000A0A0): u32 raw; bit 0x80000000 →
    empty; else ``raw & 0x9FFFFFFF`` payload bytes, plus one trailing byte when
    the ``0x20000000`` flag is clear. Returns ``(payload_or_None, next_off)``."""
    if off + 4 > len(buf):
        raise ParseError("eof reading buffer length")
    raw = struct.unpack_from("<I", buf, off)[0]
    off += 4
    if raw & 0x80000000:
        return None, off
    ln = raw & 0x9FFFFFFF
    if not (raw & 0x20000000):
        ln += 1
    if off + ln > len(buf):
        raise ParseError("buffer payload out of range")
    return buf[off:off + ln], off + ln


def _read_buffer_at(buf: bytes, off: int) -> int:
    """Like :func:`_read_buffer_value_at` but only returns the next offset."""
    _, off = _read_buffer_value_at(buf, off)
    return off


def _decode_property_default(payload: bytes | None) -> "tuple[bool, object]":
    """Decode an ionCube default-value buffer (an IC_ENCODED_ZVAL).

    The payload is the compact zval text optionally prefixed by a high-bit
    format marker byte (e.g. ``0x81``). Returns ``(has_default, value)``;
    ``has_default`` is False when the value is absent or an implicit null.
    """
    if not payload:
        return False, None
    text = payload.decode("latin1")
    if text and ord(text[0]) >= 0x80:   # strip the format-marker byte
        text = text[1:]
    if not text:
        return False, None
    try:
        value = decode_encoded_zval(text)
    except ParseError:
        return False, None
    # An implicit null default (untyped property with no initializer) is not
    # worth rendering as ``= null`` — keep the bare declaration instead.
    if value is None:
        return False, None
    return True, value


def _read_attributes(buf: bytes, off: int) -> int:
    """sub_100A0240: u32 count (signed; ``<= 0`` → none) + count attribute entries
    (sub_100A0150)."""
    count = struct.unpack_from("<I", buf, off)[0]
    off += 4
    if count & 0x80000000 or count == 0 or count > 0x2710:
        return off
    for _ in range(count):
        # sub_100A0150: u32 v13 + sstring + 3×u32 + v13×(sstring + buffer)
        v13 = struct.unpack_from("<I", buf, off)[0]
        off += 4
        _, off = _read_serialized_string_at(buf, off)
        off += 12  # three u32 fields
        if v13 > 0x10000:
            raise ParseError("implausible attribute member count")
        for _ in range(v13 & 0x7FFFFFFF if not (v13 & 0x80000000) else 0):
            _, off = _read_serialized_string_at(buf, off)
            off = _read_buffer_at(buf, off)
    return off


def _read_type(buf: bytes, off: int) -> int:
    """sub_1009FE30 (zend_type): u32 mask; bit 0x01000000 → one name string;
    bit 0x00400000 → u32 n + n nested types; otherwise nothing more."""
    mask = struct.unpack_from("<I", buf, off)[0]
    off += 4
    if mask & 0x01000000:
        _, off = _read_serialized_string_at(buf, off)
    elif mask & 0x00400000:
        n = struct.unpack_from("<I", buf, off)[0]
        off += 4
        if n > 0x10000:
            raise ParseError("implausible type-list count")
        for _ in range(n):
            off = _read_type(buf, off)
    return off


def _read_value_table(buf: bytes, off: int) -> "tuple[int, list]":
    """sub_100A2BC0: u32 count + count default-value buffers.

    Returns ``(next_off, [payload_bytes | None, ...])``."""
    count = struct.unpack_from("<I", buf, off)[0]
    off += 4
    cap = min(count, 10000) if count <= 0x2710 else 10000
    values: list = []
    for _ in range(cap):
        payload, off = _read_buffer_value_at(buf, off)
        values.append(payload)
    return off, values


def _read_trait_uses(buf: bytes, off: int) -> int:
    """sub_10001930: u32 a + a names; sub_10001490: u32 b + b×(2 buffers + sstring
    + u32); sub_10001630: u32 c + c×(2 buffers + u32 d + d names)."""
    def u32(o: int) -> "tuple[int, int]":
        return struct.unpack_from("<I", buf, o)[0], o + 4

    a, off = u32(off)
    if a > 0x10000:
        raise ParseError("implausible trait-name count")
    for _ in range(a):
        _, off = _read_serialized_string_at(buf, off)
    b, off = u32(off)
    if b > 0x10000:
        raise ParseError("implausible trait-method count")
    for _ in range(b):
        off = _read_buffer_at(buf, off)
        off = _read_buffer_at(buf, off)
        _, off = _read_serialized_string_at(buf, off)
        _, off = u32(off)
    c, off = u32(off)
    if c > 0x10000:
        raise ParseError("implausible trait-rule count")
    for _ in range(c):
        off = _read_buffer_at(buf, off)
        off = _read_buffer_at(buf, off)
        d, off = u32(off)
        if d > 0x10000:
            raise ParseError("implausible trait-insteadof count")
        for _ in range(d):
            _, off = _read_serialized_string_at(buf, off)
    return off


_PROP_VISIBILITY = {1: "public", 2: "protected", 4: "private"}


def _consume_class_tail(buf: bytes, off: int, *, php_version: int) -> dict:
    """Parse the class-record tail starting at the first byte after the methods.

    Returns ``{"next_offset", "doc_comment", "properties", "constants"}``.
    ``next_offset`` is where the following class record begins.
    """
    off, default_props   = _read_value_table(buf, off)   # instance defaults
    off, default_statics = _read_value_table(buf, off)    # static defaults

    # properties (sub_100A03C0): u32 count + count×(buffer name, u32 flags,
    # sstring, attributes, type). Default values live in the two tables above —
    # instance properties draw from the first, static ones from the second, each
    # in declaration order.
    properties: list[dict] = []
    prop_count = struct.unpack_from("<I", buf, off)[0]
    off += 4
    if prop_count > 0x2710:
        raise ParseError("implausible property count")
    inst_idx = static_idx = 0
    for _ in range(prop_count):
        name_off = off + 4
        name_raw = struct.unpack_from("<I", buf, off)[0]
        off = _read_buffer_at(buf, off)
        flags = struct.unpack_from("<I", buf, off)[0]
        off += 4
        doc_raw, off = _read_serialized_string_at(buf, off)  # property doc-comment
        off = _read_attributes(buf, off)
        off = _read_type(buf, off)
        nm = None
        if not (name_raw & 0x80000000):
            nlen = name_raw & 0x9FFFFFFF
            nm = _decode_class_name(buf[name_off:name_off + nlen], None)
        is_static = bool(flags & 0x10)
        if is_static:
            payload = default_statics[static_idx] if static_idx < len(default_statics) else None
            static_idx += 1
        else:
            payload = default_props[inst_idx] if inst_idx < len(default_props) else None
            inst_idx += 1
        has_default, default_value = _decode_property_default(payload)
        properties.append({
            "name": nm,
            "visibility": _PROP_VISIBILITY.get(flags & 0x7, "public"),
            "is_static": is_static,
            "has_default": has_default,
            "default": default_value,
            "doc_comment": doc_raw.decode("utf-8", "replace") if doc_raw else None,
        })

    # class constants: u32 count + count×(sstring name, value buffer, sstring,
    # attributes, [type on PHP 8.3])
    constants: list[str] = []
    const_count = struct.unpack_from("<I", buf, off)[0]
    off += 4
    if const_count > 0x2710:
        raise ParseError("implausible constant count")
    for _ in range(const_count):
        cname, off = _read_serialized_string_at(buf, off)
        off = _read_buffer_at(buf, off)
        _, off = _read_serialized_string_at(buf, off)
        off = _read_attributes(buf, off)
        if php_version >= 83:
            off = _read_type(buf, off)
        if cname is not None:
            constants.append(cname.decode("latin1", "replace"))

    off = _read_trait_uses(buf, off)
    off = _read_attributes(buf, off)    # class-level attributes

    info_a = struct.unpack_from("<I", buf, off)[0]
    off += 4
    if info_a:
        off = _read_buffer_at(buf, off)
    off += 8                            # two metadata u32s (info[77]/info[78])

    doc_raw, off = _read_serialized_string_at(buf, off)
    doc_comment = doc_raw.decode("utf-8", "replace") if doc_raw else None

    return {
        "next_offset": off,
        "doc_comment": doc_comment,
        "properties": properties,
        "constants": constants,
    }


def _extract_nested_closures(
    blob: bytes,
    parent_inner,
    parent_id: str,
    *,
    source_file: str,
    request_key: int,
    serialization_version: int,
    opcode_names: dict,
    php_flags: int,
    php_version: int,
    handler_tables=None,
    handler_variant=None,
    resolver=None,
    op_arrays: dict,
    all_methods_text: list,
    report_methods: list,
    closure_counter: list,
) -> None:
    if not parent_inner or getattr(parent_inner, "nested_function_count", 0) <= 0:
        return

    sub = blob[parent_inner.end_offset:]
    offset = 0
    count = parent_inner.nested_function_count

    for _ in range(count):
        if offset + 4 >= len(sub):
            break
        try:
            rec = extract_dynamic_main_record(b"\x00\x00\x00\x00" + sub[offset:], php_flags=php_flags, offset=0)
            real_end = offset + rec.end_offset - 4
        except Exception:
            break

        _, state, inner = _decrypt_blob(rec)
        if inner is not None:
            if resolver:
                resolve_interned_literal_strings(inner.literals, resolver)
                resolve_interned_type_names(inner.arg_type_info, resolver)

            try:
                raw, text = _dump_function(
                    rec, inner,
                    request_key=request_key,
                    serialization_version=serialization_version,
                    opcode_names=opcode_names,
                    handler_tables=handler_tables,
                    handler_variant=handler_variant,
                    php_flags=php_flags,
                    php_version=php_version,
                )
            except Exception:
                offset = real_end
                continue

            closure_counter[0] += 1
            idx = closure_counter[0]
            fn_id, fn_op = build_op_array_entry(raw, source_file, kind="closure")
            fn_id = f"{fn_id}#closure_{idx}"
            fn_op["id"] = fn_id
            fn_op["meta"]["parent"] = parent_id
            op_arrays[fn_id] = fn_op
            all_methods_text.append(text)
            report_methods.append({
                "name": f"{parent_id}#closure_{idx}",
                "state": state,
                "opcodes": inner.block.opcode_count,
                "literals": inner.metadata.literal_count,
                "lines": f"{inner.metadata.line_start}..{inner.metadata.line_end}",
            })

            _extract_nested_closures(
                rec.blob, inner, fn_id,
                source_file=source_file,
                request_key=request_key,
                serialization_version=serialization_version,
                opcode_names=opcode_names,
                php_flags=php_flags,
                php_version=php_version,
                handler_tables=handler_tables,
                handler_variant=handler_variant,
                resolver=resolver,
                op_arrays=op_arrays,
                all_methods_text=all_methods_text,
                report_methods=report_methods,
                closure_counter=closure_counter,
            )

        offset = real_end


def dump_file_to_ir(
    source: Path,
    *,
    out_dir: Path | None = None,
    serialization_version: int | None = None,
    loader_dll: Path | None = None,
    php_version: int | None = None,
    save_files: bool = True,
) -> tuple[dict, str, dict]:
    # ── header decode ─────────────────────────────────────────────────────────
    header_report, decrypted_header = decode_file(
        source, target_php=php_version
    )
    payload = read_encoded_payload(source, target_php=php_version)
    body_obj = decode_payload_body(
        payload,
        int(header_report["body_offset"]),
        int(header_report["initial_header"]["version"]),
    )
    body = body_obj.decompressed

    request_key = int(str(header_report["initial_header"]["bytecode_xor_key"]), 16)
    php_flags   = int(str(header_report["header_trailer"]["php_flags"]), 16)
    sv = serialization_version or int(header_report["initial_header"]["version"])
    header_php_version = int(header_report["header_trailer"]["php_version_code"])
    target_php_version = php_version or header_php_version
    if php_version and php_version != header_php_version:
        print(f"warning: target php {php_version} conflicts with header target {header_php_version}")

    opcode_names    = load_opcode_names()
    resolver        = _load_resolver(loader_dll, php_version=target_php_version)
    handler_tables  = _load_handler_tables(loader_dll, php_version=target_php_version)
    handler_variant: int | None = None
    closure_counter = [0]

    op_arrays: dict      = {}   # id → icdump op_array entry
    function_index: dict = {}  # table_hex → fn_id
    all_methods_text    = []   # for combined TXT
    report_methods      = []   # for summary

    # ── main record ───────────────────────────────────────────────────────────
    main_rec = extract_dynamic_main_record(body, php_flags=php_flags, offset=0)
    _, main_state, main_inner = _decrypt_blob(main_rec)
    if main_inner is not None:
        if resolver:
            resolve_interned_literal_strings(main_inner.literals, resolver)
            resolve_interned_type_names(main_inner.arg_type_info, resolver)

        # Detect handler variant once from the main op array
        if handler_tables is not None and sv >= 6:
            _xor_tmp = build_php81_opcode_xor_stream(
                main_inner.block, main_inner.metadata,
                outer=main_rec,
                request_key=request_key,
                serialization_version=sv,
                header_flags=php_flags,
            )
            _dec_tmp = decode_opcode_block(
                main_inner.block, main_inner.metadata,
                serialization_version=sv,
                opcode_xor=_xor_tmp.xor_bytes,
                opcode_names=opcode_names,
                header_flags=php_flags,
            )
            handler_variant = _detect_handler_variant(handler_tables, _dec_tmp, _xor_tmp)

        raw, text = _dump_function(
            main_rec, main_inner,
            request_key=request_key,
            serialization_version=sv,
            opcode_names=opcode_names,
            handler_tables=handler_tables,
            handler_variant=handler_variant,
            php_flags=php_flags,
            php_version=php_version,
        )
        main_id, main_op = build_op_array_entry(raw, str(source), kind="main")
        op_arrays[main_id] = main_op
        all_methods_text.append(text)
        report_methods.append({
            "name": "<main>", "state": main_state,
            "opcodes": main_inner.block.opcode_count,
            "literals": main_inner.metadata.literal_count,
            "lines": f"{main_inner.metadata.line_start}..{main_inner.metadata.line_end}",
        })
        _extract_nested_closures(
            main_rec.blob, main_inner, main_id,
            source_file=str(source),
            request_key=request_key,
            serialization_version=sv,
            opcode_names=opcode_names,
            handler_tables=handler_tables,
            handler_variant=handler_variant,
            php_flags=php_flags,
            php_version=target_php_version,
            resolver=resolver,
            op_arrays=op_arrays,
            all_methods_text=all_methods_text,
            report_methods=report_methods,
            closure_counter=closure_counter,
        )
    else:
        report_methods.append({"name": "<main>", "state": "failed"})

    after_main = main_rec.end_offset

    # ── standalone functions ───────────────────────────────────────────────────
    fn_count = struct.unpack_from("<H", body, after_main)[0]
    fn_offset = after_main + 2
    print(f"function_count: {fn_count}")

    after_fns = fn_offset  # updated per-record below; stays fn_offset if fn_count=0

    for name, rec in _parse_function_records(body, php_flags=php_flags,
                                              start_offset=fn_offset, count=fn_count):
        _, state, inner = _decrypt_blob(rec)

        if inner is None:
            cipher_type = _detect_dynamic_cipher_type(rec)
            print(f"  STUB {name}: dynamic key ({cipher_type})")
            stub_raw = _make_stub_raw(rec, cipher_type)
            fn_id, fn_op = build_op_array_entry(stub_raw, str(source), kind="function")
            fn_op["meta"]["static_dump_status"] = {
                "failed": True, "dynamic_key_stub": True,
                "cipher_type": cipher_type,
                "blob_tag": rec.blob_tag, "blob_len": len(rec.blob),
            }
            op_arrays[fn_id] = fn_op
            function_index[fn_op["meta"]["function_table_key_hex"]] = fn_id
            report_methods.append({"name": name, "state": f"stub:{cipher_type}"})
            continue

        if resolver:
            resolve_interned_literal_strings(inner.literals, resolver)
            resolve_interned_type_names(inner.arg_type_info, resolver)

        try:
            raw, text = _dump_function(
                rec, inner,
                request_key=request_key,
                serialization_version=sv,
                opcode_names=opcode_names,
                handler_tables=handler_tables,
                handler_variant=handler_variant,
                php_flags=php_flags,
                php_version=php_version,
            )
        except Exception as exc:
            print(f"  FAIL {name}: {exc}")
            report_methods.append({"name": name, "state": f"opcode_error: {exc}"})
            continue

        fn_id, fn_op = build_op_array_entry(raw, str(source), kind="function")
        op_arrays[fn_id] = fn_op
        function_index[fn_op["meta"]["function_table_key_hex"]] = fn_id
        all_methods_text.append(text)
        report_methods.append({
            "name": name, "state": state,
            "opcodes": inner.block.opcode_count,
            "literals": inner.metadata.literal_count,
            "lines": f"{inner.metadata.line_start}..{inner.metadata.line_end}",
        })
        print(f"  OK  {name}: {inner.block.opcode_count} opcodes  "
              f"{inner.metadata.literal_count} literals  "
              f"lines {inner.metadata.line_start}..{inner.metadata.line_end}")

        _extract_nested_closures(
            rec.blob, inner, fn_id,
            source_file=str(source),
            request_key=request_key,
            serialization_version=sv,
            opcode_names=opcode_names,
            handler_tables=handler_tables,
            handler_variant=handler_variant,
            php_flags=php_flags,
            php_version=target_php_version,
            resolver=resolver,
            op_arrays=op_arrays,
            all_methods_text=all_methods_text,
            report_methods=report_methods,
            closure_counter=closure_counter,
        )

        after_fns = rec.end_offset

    # ── class methods ─────────────────────────────────────────────────────────
    class_count = 0
    if after_fns + 2 <= len(body):
        class_count = struct.unpack_from("<H", body, after_fns)[0]

    class_index: dict = {}

    if class_count:
        print(f"class_count: {class_count}")
        scan = after_fns + 2
        class_method_count = 0
        classes_parsed = 0

        for cls_idx in range(class_count):
            # Structural class-header parse (exact loader layout, no heuristics).
            # If it does not validate we have run past the real class records
            # into trailing constant/property data the loader emits inside a
            # class record but that we do not decode yet — stop cleanly.
            try:
                hdr = _parse_class_record_header(body, scan)
                first_method_ok = False
                try:
                    extract_dynamic_main_record(
                        b"\x00\x00\x00\x00" + body[hdr["first_method_offset"]:],
                        php_flags=php_flags, offset=0,
                    )
                    first_method_ok = True
                except Exception:
                    first_method_ok = (hdr["method_count"] == 0)
                plausible = (
                    hdr["name"] and len(hdr["name"]) <= 255 and first_method_ok
                )
            except Exception:
                hdr = None
                plausible = False

            if not plausible:
                # class_count consistently over-counts the real classes by one
                # (a trailing record the loader emits). Reaching ~EOF here is the
                # expected, clean end — no warning. A failure with substantial
                # data still remaining means a real class we could not parse.
                remaining = class_count - classes_parsed
                if classes_parsed > 0 and remaining > 1 and scan < len(body) - 16:
                    print(f"  note: {remaining} of {class_count} class record(s) "
                          f"not parsed (stopped at {scan:#x} of {len(body):#x})")
                break

            classes_parsed += 1
            class_name  = _decode_class_name(hdr["name"], f"Class{cls_idx + 1}")
            parent_name = _decode_class_name(hdr["parent"], None)
            interfaces  = [
                n for n in (_decode_class_name(i, None) for i in hdr["interfaces"]) if n
            ]
            ce_flags = hdr["ce_flags"]
            ce_flags_decoded = {
                "is_interface": bool(ce_flags & 0x1),
                "is_trait":     bool(ce_flags & 0x2),
                "is_final":     bool(ce_flags & 0x20),
                "is_abstract":  bool(ce_flags & 0x40),
            }
            kind_kw = "interface" if ce_flags_decoded["is_interface"] else (
                "trait" if ce_flags_decoded["is_trait"] else "class")
            extends = f" extends {parent_name}" if parent_name else ""
            impl    = f" implements {', '.join(interfaces)}" if interfaces else ""
            print(f"  {kind_kw} {class_name}{extends}{impl}")

            method_idx    = 0
            class_methods: dict = {}  # method name → op_array id
            scan = hdr["first_method_offset"]

            def _register_method(nm: str, fid: str) -> None:
                key = nm or f"m{len(class_methods)}"
                while key in class_methods:
                    key += "_"
                class_methods[key] = fid

            # Parse method records sequentially until one fails (class end).
            while scan < len(body) - 50:
                try:
                    rec = extract_dynamic_main_record(
                        b"\x00\x00\x00\x00" + body[scan:],
                        php_flags=php_flags, offset=0,
                    )
                    real_end        = scan + rec.end_offset   - 4
                    rec.start_offset = scan
                    rec.end_offset   = real_end
                    rec.blob_offset  = scan + rec.blob_offset - 4
                except Exception:
                    break  # no more method records; class ended

                # Successfully parsed a method record.
                name = rec.table_name or f"<cls{cls_idx}.m{method_idx}@{scan:#x}>"
                _, state, inner = _decrypt_blob(rec)

                if inner is None:
                    cipher_type = _detect_dynamic_cipher_type(rec)
                    print(f"  STUB {name}: dynamic key ({cipher_type})")
                    stub_raw = _make_stub_raw(rec, cipher_type)
                    fn_id, fn_op = build_op_array_entry(stub_raw, str(source), kind="method")
                    if fn_id in op_arrays:
                        fn_id = f"{fn_id}@{scan:#x}"
                        fn_op["id"] = fn_id
                    fn_op["meta"]["static_dump_status"] = {
                        "failed": True, "dynamic_key_stub": True,
                        "cipher_type": cipher_type,
                        "blob_tag": rec.blob_tag, "blob_len": len(rec.blob),
                    }
                    op_arrays[fn_id] = fn_op
                    _register_method(name, fn_id)
                    report_methods.append({"name": name, "state": f"stub:{cipher_type}"})
                else:
                    if resolver:
                        resolve_interned_literal_strings(inner.literals, resolver)
                        resolve_interned_type_names(inner.arg_type_info, resolver)
                    try:
                        raw, text = _dump_function(
                            rec, inner,
                            request_key=request_key,
                            serialization_version=sv,
                            opcode_names=opcode_names,
                            handler_tables=handler_tables,
                            handler_variant=handler_variant,
                            php_flags=php_flags,
                            php_version=php_version,
                        )
                    except Exception as exc:
                        safe_name = (name or "").encode("ascii", "replace").decode()
                        print(f"  FAIL {safe_name}: {exc}")
                        report_methods.append({"name": name, "state": f"opcode_error: {exc}"})
                        scan = real_end
                        method_idx += 1
                        class_method_count += 1
                        continue

                    fn_id, fn_op = build_op_array_entry(raw, str(source), kind="method")
                    if fn_id in op_arrays:
                        fn_id = f"{fn_id}@{scan:#x}"
                        fn_op["id"] = fn_id
                    op_arrays[fn_id] = fn_op
                    _register_method(name, fn_id)
                    all_methods_text.append(text)
                    report_methods.append({
                        "name": name, "state": state,
                        "opcodes": inner.block.opcode_count,
                        "literals": inner.metadata.literal_count,
                        "lines": f"{inner.metadata.line_start}..{inner.metadata.line_end}",
                    })
                    safe_name = (name or "").encode("ascii", "replace").decode()
                    print(f"    OK  {safe_name}: {inner.block.opcode_count} opcodes  "
                          f"{inner.metadata.literal_count} literals  "
                          f"lines {inner.metadata.line_start}..{inner.metadata.line_end}")

                    _extract_nested_closures(
                        rec.blob, inner, fn_id,
                        source_file=str(source),
                        request_key=request_key,
                        serialization_version=sv,
                        opcode_names=opcode_names,
                        handler_tables=handler_tables,
                        handler_variant=handler_variant,
                        php_flags=php_flags,
                        php_version=target_php_version,
                        resolver=resolver,
                        op_arrays=op_arrays,
                        all_methods_text=all_methods_text,
                        report_methods=report_methods,
                        closure_counter=closure_counter,
                    )

                scan = real_end
                method_idx += 1
                class_method_count += 1

            # Parse the class-record tail (default values, properties, constants,
            # trait uses, attributes, doc-comment). This consumes the exact byte
            # count so the next class record begins where this one ends.
            doc_comment = None
            properties_info: dict = {}
            try:
                tail = _consume_class_tail(body, scan, php_version=php_version)
                scan = tail["next_offset"]
                doc_comment = tail["doc_comment"]
                for p in tail["properties"]:
                    pname = p["name"]
                    if not pname:
                        continue
                    entry = {
                        "flags_decoded": {
                            "visibility": p["visibility"],
                            "is_static": p["is_static"],
                        },
                        "is_static": p["is_static"],
                        "has_default_value": p.get("has_default", False),
                    }
                    if p.get("has_default"):
                        entry["default_value"] = safe_value(p["default"])
                    if p.get("doc_comment"):
                        entry["doc_comment"] = p["doc_comment"]
                    properties_info[pname] = entry
                if tail["properties"] or tail["constants"] or doc_comment:
                    print(f"    tail: {len(tail['properties'])} prop(s), "
                          f"{len(tail['constants'])} const(s)"
                          + (", doc-comment" if doc_comment else ""))
            except Exception as exc:
                # Tail layout not fully recognized — keep the class we decoded
                # but stop the loop, since we can no longer locate the next one.
                safe = str(exc).encode("ascii", "replace").decode()
                print(f"    note: class tail not fully parsed ({safe}); "
                      f"stopping after this class")
                class_id = f"class:{class_name.encode('utf-8').hex()}"
                if class_id in class_index:
                    class_id = f"{class_id}_{cls_idx}"
                class_index[class_id] = {
                    "id": class_id, "name": class_name, "parent": parent_name,
                    "interfaces": interfaces, "methods": class_methods,
                    "ce_flags_decoded": ce_flags_decoded,
                }
                break

            # Register the class and its decoded methods in the normalized IR.
            class_id = f"class:{class_name.encode('utf-8').hex()}"
            if class_id in class_index:
                class_id = f"{class_id}_{cls_idx}"
            class_index[class_id] = {
                "id": class_id,
                "name": class_name,
                "parent": parent_name,
                "interfaces": interfaces,
                "methods": class_methods,
                "ce_flags_decoded": ce_flags_decoded,
                "doc_comment": doc_comment,
                "properties_info": properties_info,
            }

        if class_method_count:
            print(f"class_methods_total: {class_method_count}")

    # ── icdump-ir-v1 output ────────────────────────────────────────────────────
    ok    = sum(1 for m in report_methods if "opcodes" in m)
    stubs = sum(1 for m in report_methods if m.get("state", "").startswith("stub:"))
    fails = sum(1 for m in report_methods if m.get("state") == "failed")

    resolve_function_calls(op_arrays)

    icdump = {
        "format": "icdump-ir-v1",
        "source_file": str(source),
        "summary": {
            "op_array_count": len(op_arrays),
            "function_count": len(function_index),
            "closure_count": closure_counter[0],
            "class_count": len(class_index),
        },
        "entry": "main",
        "op_arrays": op_arrays,
        "function_index": function_index,
        "closure_index": {},
        "class_index": class_index,
        "ioncube_api_calls": safe_value([]),
    }

    sep = "\n" + "=" * 72 + "\n"
    combined_txt = sep.join(all_methods_text)

    if save_files and out_dir:
        out_dir.mkdir(parents=True, exist_ok=True)
        (out_dir / f"{source.stem}.icdump.json").write_text(
            json.dumps(icdump, indent=2, ensure_ascii=False), encoding="utf-8"
        )
        (out_dir / f"{source.stem}.icdump.txt").write_text(combined_txt, encoding="utf-8")
        print(f"\ndone: {ok} decoded, {stubs} stubs, {fails} failed, {closure_counter[0]} closures")
        print(f"output: {out_dir}")

    return icdump, combined_txt, header_report


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("input", type=Path)
    ap.add_argument("--out-dir", type=Path)
    ap.add_argument("--serialization-version", type=int)
    ap.add_argument("--loader-dll", type=Path, metavar="DLL",
                    help="path to ioncube_loader_win_8.N.dll for interned-string resolution")
    ap.add_argument("--php-version", type=int, choices=(81, 82, 83, 84),
                    help="target PHP ABI (normally inferred from the header trailer)")
    args = ap.parse_args()

    out_dir = args.out_dir or args.input.with_name(args.input.stem + "_dump")
    dump_file_to_ir(
        args.input,
        out_dir=out_dir,
        serialization_version=args.serialization_version,
        loader_dll=args.loader_dll,
        php_version=args.php_version,
        save_files=True,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
