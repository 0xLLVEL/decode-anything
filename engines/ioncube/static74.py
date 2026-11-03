"""icdump-ir-v1 for a PHP 7.4 artifact, built from the body alone.

The static reader knows the record list, the field block, the opcode stream, the
source line of every instruction and the cache slots. It does not know operand
values: an instruction is an 8-byte word block whose high half is the line and
whose second dword is the per-instruction mask word, so nothing in that stream
names a literal, a CV or a temp. Feeding this document to the AST decompiler
therefore rebuilds the file's skeleton - class, method names, argument counts,
line ranges, opcode order - with unresolved operands, which is why
``decompile.py`` still routes 7.4 through the runtime until the operand table is
reversed.

What it is good for today:

* one JSON artifact per file holding the whole structural layer, diffable
  against a runtime dump with ``--truth``;
* the id/class/function indexing ``icdump-ir-v1`` expects, so the AST side can
  be pointed at it the moment operands land;
* a hard count (records, opcodes, escapes, unseeded records) that the tests pin.

    python tools/ic74_static_ir.py file.php -o file.icdump.json
"""

from __future__ import annotations

import struct
from pathlib import Path
from typing import Any

ARG_RECORD = 20
ARG_MARK = 0x00010000
FIELD_BASE = 0x90


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


def _operand() -> dict[str, Any]:
    return {"type": 0, "type_name": "IS_UNUSED", "constant": 0, "var": 0, "num": 0}


def _raw_opcodes(entry: dict[str, Any], body: bytes) -> list[dict[str, Any]]:
    from tools.ic74_static_dump import op_block_start, walk_ops

    start = op_block_start(body, entry["end"])
    ops, _ = walk_ops(body, start, entry["opcodes"], bytes(entry["opcodes"]))
    decoded = entry.get("opcode_bytes")
    out: list[dict[str, Any]] = []
    for index, op in enumerate(ops):
        opcode = decoded[index] if decoded else op["opcode"]
        out.append(
            {
                "index": index,
                "line": op["line"],
                "opcode": opcode,
                "extended_value": op["slot"] or 0,
                "op1": _operand(),
                "op2": _operand(),
                "result": _operand(),
            }
        )
    return out


def _entry(entry: dict[str, Any], body: bytes, op_id: str) -> dict[str, Any]:
    return {
        "id": op_id,
        "kind": "method" if entry.get("class") else "function",
        "function_name": entry["name"],
        "vars": [],
        "num_args": argument_count(body, entry["end"]),
        "required_num_args": 0,
        "fn_flags": 0,
        "line_start": entry["line_start"],
        "line_end": entry["line_end"],
        "last_var": entry["variables"],
        "T": entry["temps"],
        "literals": [],
        "opcodes": _raw_opcodes(entry, body),
        "try_catch": [],
        "meta": {"operands": "unresolved", "fn_flags": "unresolved"},
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
        op_arrays[op_id] = _entry(entry, body, op_id)

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
            "operands": "unresolved",
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
        "status": "static_skeleton",
        "encoder": "ionCube",
        "source": "static_body_74",
        "operands": "unresolved",
        "note": (
            "opcode stream, line numbers and cache slots come from the body; "
            "operand values are not in it, so the AST layer emits placeholders"
        ),
    }
    return icdump
