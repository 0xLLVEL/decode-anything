"""icdump-ir-v1 for a PHP 7.4 artifact, built from the body alone.

The static reader recovers the whole record: the field block, the opcode stream,
the source line of every instruction, the cache slots, the literal pool, the CV
names and the operand table. Right after the word block sits a count followed by
one 5-byte group per operand - ``(tag u8, payload u32)`` in ``result, op1, op2``
order - which is where a literal index, a CV index or a temp slot comes from.
Against the runtime dump that is 11,473 of 11,473 live operand slots equal.
Branch destinations are the remaining read, so ``decompile.py`` still routes 7.4
through the runtime dump.

What the document carries:

* every record, its opcode bytes, line range, literal values and variable names;
* the operand of every instruction, resolved to the slot the loader would build;
* the id/class/function indexing ``icdump-ir-v1`` expects, so the shared AST
  layer consumes it exactly like a runtime dump.

    python tools/ic74_static_ir.py file.php -o file.icdump.json
"""

from __future__ import annotations

import struct
from pathlib import Path
from typing import Any

ARG_RECORD = 20
ARG_MARK = 0x00010000
FIELD_BASE = 0x90
LITERAL_HEADER = 16
LITERAL_INLINE = 8

# Literal kind byte, low 8 bits of the table entry's third dword. The `0x100`
# bit rides on strings and arrays; it marks the value as owned by the pool.
LITERAL_NULL = 1
LITERAL_FALSE = 2
LITERAL_TRUE = 3
LITERAL_LONG = 4
LITERAL_STRING = 6
LITERAL_ARRAY = 7
LITERAL_INLINE_KINDS = frozenset({LITERAL_STRING, LITERAL_ARRAY})

OPCODE_HEADERS = (
    "loader/refs/ic74dump-opcodes/build/*/include/Zend/zend_vm_opcodes.h",
    "loader/php74-*/dev/*/include/Zend/zend_vm_opcodes.h",
)


def _u32(buf: bytes, offset: int) -> int:
    if offset < 0 or offset + 4 > len(buf):
        return 0
    return struct.unpack_from("<I", buf, offset)[0]


def argument_count(body: bytes, fields: int) -> int:
    """Declared arguments: the 20-byte records between ``+0x90`` and the block."""

    start = fields + FIELD_BASE
    count = 0
    while count < 0x100 and _u32(body, start + 8) == ARG_MARK:
        start += ARG_RECORD
        count += 1
    return count


def _hex(text: str) -> str:
    return text.encode("utf-8").hex()


def opcode_names() -> dict[int, str]:
    """PHP 7.4 opcode numbers, read from the devel headers in the repo."""

    from .body import load_opcode_names

    root = Path(__file__).resolve().parents[2]
    for pattern in OPCODE_HEADERS:
        for header in sorted(root.glob(pattern)):
            names = load_opcode_names(header)
            if names:
                return names
    return {}


def interned() -> Any:
    """Loader string table for interned literals, when the DLL is present."""

    from .body import LoaderInternedStringResolver

    root = Path(__file__).resolve().parents[2]
    for candidate in sorted(root.glob("loader/ioncube_loader_win_7.4.dll")):
        try:
            return LoaderInternedStringResolver.from_dll(candidate, php_version=74)
        except Exception:
            return None
    return None


def pool(body: bytes, name: str, head: int) -> tuple[int, int, int] | None:
    """The record's string pool: ``(base, length, name_position)``.

    The pool opens with the op_array name, then the declared argument names, then
    the local variable names, then one NUL-terminated entry per literal. A
    ``u32`` length sits six bytes ahead of the name and *relative* offsets in the
    literal table are measured from ``base = name_position - 2``.
    """

    position = body.find(name.encode("utf-8") + b"\x00", head)
    if position < 6:
        return None
    return position - 2, _u32(body, position - 6), position


def variable_names(
    body: bytes, name: str, head: int, arguments: int, last_var: int
) -> tuple[list[str], list[str]]:
    """Argument names then local variable names, in slot order.

    ``+0x30`` counts the CVs and the argument records carry the declared
    parameters, so the pool is walked for exactly ``arguments + last_var`` names.
    Both match the runtime dump one for one.
    """

    found = pool(body, name, head)
    if found is None:
        return [], []
    base, length, position = found
    limit = base + length
    cursor = position + len(name.encode("utf-8")) + 1
    names: list[str] = []
    for _ in range(arguments + last_var):
        end = body.find(b"\x00", cursor, limit)
        if end < 0:
            break
        names.append(body[cursor:end].decode("latin-1"))
        cursor = end + 1
    return names[:arguments], names[arguments:]


def array_keys(text: str) -> list[Any]:
    """Keys of an array literal from its inline serialization.

    The body writes an array as ``[<n>:<ordinal>s<len>'<key><value>;...}`` - the
    keys are literal, the values are references the runtime keeps in its own
    table. ``[}`` is the empty array.
    """

    keys: list[Any] = []
    if not text.startswith("["):
        return keys
    cursor = 1
    if text[cursor : cursor + 1] == "}":
        return keys
    while cursor < len(text):
        colon = text.find(":", cursor)
        if colon < 0:
            break
        cursor = colon + 1
        start = cursor
        while cursor < len(text) and text[cursor].isdigit():
            cursor += 1
        if text[cursor : cursor + 1] == "s":
            quote = text.find("'", cursor + 1)
            if quote < 0:
                break
            size = int(text[cursor + 1 : quote] or 0)
            cursor = quote + 1
            keys.append(text[cursor : cursor + size])
            cursor += size
        else:
            end = text.find(";", start)
            if end < 0:
                break
            keys.append(int(text[start:end] or 0))
            cursor = end + 1
        brace = text.find("}", cursor)
        following = text.find(":", cursor)
        if following < 0 or (0 <= brace < following):
            break
        back = following
        while back > cursor and text[back - 1].isdigit():
            back -= 1
        cursor = back
    return keys


def _text(raw: bytes) -> str:
    """Pool bytes as text: the pool is UTF-8, with latin-1 as the fallback."""

    try:
        return raw.decode("utf-8")
    except UnicodeDecodeError:
        return raw.decode("latin-1")


def _literal(kind: int, payload: int, text: Any) -> dict[str, Any]:
    """One literal in the shape ``icdump-ir-v1`` stores it."""

    if kind == LITERAL_NULL:
        return {"type": "null", "value": None}
    if kind in (LITERAL_FALSE, LITERAL_TRUE):
        return {"type": "bool", "value": kind == LITERAL_TRUE}
    if kind == LITERAL_LONG:
        return {"type": "int", "value": struct.unpack("<i", struct.pack("<I", payload))[0]}
    if kind == LITERAL_ARRAY:
        return {"type": "array", "value": array_keys(text) if isinstance(text, str) else []}
    return {"type": "string", "value": text}


def literals(
    body: bytes, name: str, head: int, count: int, resolver: Any = None
) -> list[dict[str, Any]]:
    """Literal values for one record.

    Right after the pool sits a table of `[flags][hash][kind][aux]` entries, plus
    `[offset][length]` when the kind stores inline data - which is how a string is
    found again once the pool has moved on. A negative offset is an index into the
    loader's own string table. The kind byte decides whether the payload is a
    string, an array key list, an integer, a boolean or null.
    """

    found = pool(body, name, head)
    if found is None:
        return []
    base, pool_len, position = found
    cursor = position + pool_len - 2
    out: list[dict[str, Any]] = []
    for _ in range(count):
        if cursor + LITERAL_HEADER > len(body):
            break
        payload = _u32(body, cursor)
        kind = _u32(body, cursor + 8)
        cursor += LITERAL_HEADER
        text = None
        if kind & 0xFF in LITERAL_INLINE_KINDS:
            if cursor + LITERAL_INLINE > len(body):
                break
            offset = _u32(body, cursor)
            size = _u32(body, cursor + 4)
            cursor += LITERAL_INLINE
            signed = struct.unpack("<i", struct.pack("<I", offset))[0]
            if size == 0:
                text = ""
            elif signed < 0:
                if resolver is not None:
                    try:
                        text = resolver.decode_ref(signed, size)
                    except Exception:
                        text = None
            elif offset + size <= pool_len + 2:
                text = _text(body[base + offset : base + offset + size])
        out.append(_literal(kind & 0xFF, payload, text))
    return out


ARG_GROUP = 5
CV_BASE = 48
CV_SLOT = 16


_OPERAND_TYPE_NAMES = {
    0: "IS_UNUSED",
    1: "IS_CONST",
    2: "IS_TMP_VAR",
    4: "IS_VAR",
    8: "IS_CV",
}


def _operand(kind: int = 0, value: int = 0) -> dict[str, Any]:
    """One operand slot.

    The type name travels with the number: ``to_icdump`` maps PHP 7.4's own
    numbering (IS_CV = 16) onto this project's (IS_CV = 8) by name, so an
    unnamed slot would be read back as ``IS_UNUSED``.
    """

    return {
        "type": kind,
        "type_name": _OPERAND_TYPE_NAMES.get(kind, "IS_UNUSED"),
        "constant": value,
        "var": value,
        "num": value,
    }


def _resolve(kind: int, payload: int, last_var: int) -> int:
    """Slot number to the operand value the loader would build.

    CVs sit at ``16 * index + 48``; temps and vars share the space that starts
    after the CVs at ``16 * (last_var + 3)``. Constants and unused slots keep the
    payload as it is stored.
    """

    if kind == 8:
        return CV_BASE + CV_SLOT * payload
    if kind in (2, 4):
        return CV_SLOT * (last_var + 3) + CV_SLOT * payload
    return payload


def word_end(body: bytes, start: int, count: int) -> int:
    """End of the word block: two dwords per instruction plus the extras."""

    cursor = start
    for _ in range(count):
        word = _u32(body, cursor)
        cursor += 8
        if word & 0x1800 == 0x1800:
            cursor += 4
        if word >> 16 == 0xFFFF:
            cursor += 4
    return cursor


def aux_end(body: bytes, entry: dict[str, Any]) -> int:
    """First byte after the aux block of *entry*."""

    from tools.ic74_static_dump import op_block_start

    end = word_end(body, op_block_start(body, entry["end"]), entry["opcodes"])
    return end + 4 + ARG_GROUP * _u32(body, end)


def aux_operands(
    body: bytes, start: int, count: int, last_var: int
) -> tuple[list[tuple[dict, dict, dict]], int]:
    """The three operands of every instruction, read from the aux block.

    Each instruction spends one 5-byte group per operand - ``(tag u8, payload
    u32)`` - in the order result, op1, op2, written contiguously right after the
    word block whose dword count the record states ahead of it.
    """

    cursor = word_end(body, start, count)
    groups = _u32(body, cursor)
    base = cursor + 4
    rows: list[tuple[dict, dict, dict]] = []
    for index in range(count):
        slots = []
        for slot in range(3):
            offset = base + (index * 3 + slot) * ARG_GROUP
            if offset + ARG_GROUP > len(body):
                slots.append(_operand())
                continue
            kind = body[offset]
            payload = _u32(body, offset + 1)
            slots.append(_operand(kind, _resolve(kind, payload, last_var)))
        # stored as result, op1, op2
        rows.append((slots[1], slots[2], slots[0]))
    return rows, groups


def _raw_opcodes(
    entry: dict[str, Any],
    body: bytes,
    names: dict[int, str],
    var_names: list[str],
) -> list[dict[str, Any]]:
    from tools.ic74_static_dump import op_block_start, walk_ops

    start = op_block_start(body, entry["end"])
    ops, _ = walk_ops(body, start, entry["opcodes"], bytes(entry["opcodes"]))
    decoded = entry.get("opcode_bytes")
    operands, groups = aux_operands(body, start, entry["opcodes"], entry["variables"])
    if groups != 3 * entry["opcodes"]:
        operands = [(_operand(), _operand(), _operand())] * entry["opcodes"]
    out: list[dict[str, Any]] = []
    for index, op in enumerate(ops):
        opcode = decoded[index] if decoded else op["opcode"]
        op1, op2, result = operands[index]
        for slot in (op1, op2, result):
            if slot["type"] != 8:
                continue
            cv_index = (slot["var"] - CV_BASE) // CV_SLOT
            slot["cv_index"] = cv_index
            if 0 <= cv_index < len(var_names):
                slot["cv_name"] = var_names[cv_index]
        out.append(
            {
                "index": index,
                "line": op["line"],
                "opcode": opcode,
                "opcode_name": names.get(opcode),
                "extended_value": op["slot"] or 0,
                "op1": op1,
                "op2": op2,
                "result": result,
            }
        )
    return out


def _argument_info(names: list[str]) -> list[dict[str, Any]]:
    """Argument records in the shape ``icdump-ir-v1`` keeps them.

    The pool names the parameters but carries no type or default, so each one is
    declared untyped and required; ``RECV_INIT`` still supplies the real default
    to the emitter.
    """

    return [
        {
            "index": index,
            "name": name,
            "type_name": None,
            "class_name": None,
            "type_code": 0,
            "pass_by_reference": False,
            "allow_null": True,
            "is_variadic": False,
            "has_default": False,
        }
        for index, name in enumerate(names)
    ]


def _entry(
    entry: dict[str, Any],
    body: bytes,
    op_id: str,
    names: dict[int, str],
    resolver: Any,
) -> dict[str, Any]:
    head = aux_end(body, entry)
    arguments = argument_count(body, entry["end"])
    args, locals_ = variable_names(
        body, entry["name"], head, arguments, entry["variables"]
    )
    return {
        "id": op_id,
        "kind": "method" if entry.get("class") else "function",
        "function_name": entry["name"],
        "vars": list(locals_),
        "num_args": arguments,
        "required_num_args": arguments,
        "fn_flags": 0,
        "arg_info": _argument_info(args),
        "line_start": entry["line_start"],
        "line_end": entry["line_end"],
        "last_var": entry["variables"],
        "T": entry["temps"],
        "literals": literals(body, entry["name"], head, entry["literals"], resolver),
        "opcodes": _raw_opcodes(entry, body, names, locals_),
        "try_catch": [],
        "meta": {"operands": "static", "fn_flags": "unresolved"},
    }


def document(source: str | Path) -> dict[str, Any]:
    """A ``ic74dump-ir``-shaped document built from the static body."""

    from tools.ic74_mask import key_stubs, record_opcodes
    from tools.ic74_static_dump import decode_body, scan_body

    path = Path(source)
    header, body = decode_body(path)
    scanned = scan_body(body)
    xor_key = int(str(header["initial_header"]["bytecode_xor_key"]), 0)

    stubs = key_stubs(body)
    names = opcode_names()
    resolver = interned()
    op_arrays: dict[str, Any] = {}
    class_index: dict[str, Any] = {}
    unseeded: list[str] = []
    escapes = 0
    opcode_total = 0

    for entry in scanned["entries"]:
        opcodes, taken, _ = record_opcodes(body, entry, xor_key, stubs)
        if not opcodes:
            unseeded.append(entry["name"])
        else:
            entry["opcode_bytes"] = opcodes
            escapes += taken
            opcode_total += len(opcodes)
        owner = entry.get("class")
        if owner:
            class_id = f"class:{_hex(owner)}"
            op_id = f"{class_id}:method:{_hex(entry['name'].lower())}"
            methods = class_index.setdefault(class_id, {"name": owner, "methods": {}})
            methods["methods"][entry["name"].lower()] = op_id
        else:
            op_id = f"function:{_hex(entry['name'])}"
        op_arrays[op_id] = _entry(entry, body, op_id, names, resolver)

    return {
        "format": "ic74-static-ir-v1",
        "source_file": str(path),
        "encoder": (
            f"{header['header_trailer']['encoder_major']}."
            f"{header['header_trailer']['encoder_minor']}."
            f"{header['header_trailer']['encoder_revision']}"
        ),
        "summary": {
            "op_array_count": len(op_arrays),
            "class_count": len(class_index),
            "opcode_total": opcode_total,
            "opcode_escapes": escapes,
            "unseeded": unseeded,
            "opcode_names": bool(names),
            "interned_strings": resolver is not None,
        },
        "op_arrays": op_arrays,
        "function_index": {},
        "closure_index": {},
        "class_index": class_index,
    }


def static74_icdump(source: str | Path) -> dict[str, Any]:
    """``icdump-ir-v1`` for *source*, from the body alone."""

    from .runtime_dump import to_icdump

    raw = document(source)
    icdump = to_icdump(raw, str(source))
    icdump["encoder"] = raw["encoder"]
    icdump["summary"]["static_74"] = raw["summary"]
    icdump["summary"]["decompile_status"] = {
        "status": "static_body",
        "encoder": "ionCube",
        "source": "static_body_74",
        "operands": "static",
        "note": (
            "opcode stream, lines, literals, CV names and operand slots all come "
            "from the body; no PHP process or loader DLL is involved"
        ),
    }
    return icdump
