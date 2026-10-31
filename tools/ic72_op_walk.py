"""Walk the opcode word array using the class-byte flag rules from sub_18009E910.

Word layout is [opcode:u8][class:u8][line:u16] little endian. The class byte is a
real flag byte, not a label:

    bit 0 0x01  operand 1 present  -> five aux bytes, type -> +31, node -> +16
    bit 1 0x02  operand 2 present  -> five aux bytes, type -> +29, node -> +8
    bit 2 0x04  result present     -> five aux bytes, type -> +30, node -> +12
    bit 3 0x08  line suppressed    (sub_18009EA30 stores line 0)
    bit 4 0x10  class selector, together with bit 3:
                0x08 -> class 1, 0x10 -> class 60,
                0x18 -> class is the next word (sub_18009E9E0 case 6144)

A set 0x18 pair consumes exactly one more word. The fixed 0xFFFFFFFF word that
closes the array is never an opcode; it is the extension word of the last op.

The opcode byte itself is still masked by the loader. This tool prints it raw and
states the mask rule it does not apply.
"""

import struct
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from tools.ic72_record_walk import resync

OPERAND_TYPES = {
    1: "CONST",
    2: "TMP_VAR",
    4: "VAR",
    8: "UNUSED",
    16: "CV",
}

ARG_COUNT = {1: 0, 2: 1, 3: 2, 4: 4}
NAMES = ["binancepay_config", "binancepay_link", "call_bp_proxy", "bp_call_api"]


def decode_class(class_byte, class_word):
    if (class_byte & 0x18) == 0x18:
        return class_word
    if class_byte & 0x10:
        return 60
    if class_byte & 0x08:
        return 1
    return 0


def literal_text(literals, node):
    """Operand nodes are one based into the literal table."""
    if not literals or node < 1 or node > len(literals):
        return None
    return literals[node - 1].text


def walk_record(payload: bytes, arg_count: int):
    head = 0x88 + 20 * arg_count
    ops, cells = struct.unpack_from("<2I", payload, head)
    word_base = head + 8
    words = [struct.unpack_from("<I", payload, word_base + 4 * k)[0] for k in range(cells)]

    aux_base = word_base + 4 * cells + 4
    aux = payload[aux_base : aux_base + 15 * ops]

    out = []
    cursor = 0
    aux_cursor = 0
    while cursor < cells and len(out) < ops:
        word = words[cursor]
        opcode = word & 0xFF
        class_byte = (word >> 8) & 0xFF
        line = (word >> 16) & 0xFFFF
        cursor += 1

        class_word = None
        if (class_byte & 0x18) == 0x18:
            class_word = words[cursor] if cursor < cells else None
            cursor += 1

        operands = []
        for bit, slot in ((0x01, "op1"), (0x02, "op2"), (0x04, "result")):
            if class_byte & bit:
                kind, node = struct.unpack_from("<BI", aux, aux_cursor)
                aux_cursor += 5
                operands.append((slot, OPERAND_TYPES.get(kind, kind), node))
            else:
                operands.append((slot, "UNUSED", 0))

        if class_byte & 0x08:
            line = 0

        out.append(
            {
                "index": len(out),
                "opcode": opcode,
                "class": decode_class(class_byte, class_word),
                "class_word": class_word,
                "line": line,
                "operands": operands,
            }
        )

    return {
        "name": ops,
        "ops": ops,
        "cells": cells,
        "word_cursor": cursor,
        "aux_consumed": aux_cursor,
        "entries": out,
    }


def format_entry(entry, literals=None):
    parts = []
    for slot, kind, node in entry["operands"]:
        text = literal_text(literals, node) if kind == "CONST" else None
        if text is not None:
            parts.append("%s=CONST(%d)=\"%s\"" % (slot, node, text))
        else:
            parts.append("%s=%s(%d)" % (slot, kind, node))
    extra = "" if entry["class_word"] is None else "  class_word=%#010x" % entry["class_word"]
    return "  op%-3d code=%#04x class=%-10s line=%-4d %s%s" % (
        entry["index"],
        entry["opcode"],
        entry["class"],
        entry["line"],
        " ".join(parts),
        extra,
    )


def main(argv):
    body = Path(argv[1] if len(argv) > 1 else "scratch_body72.bin").read_bytes()
    limit = int(argv[2]) if len(argv) > 2 else 8

    for i, record in enumerate(resync(body, 4)):
        if i == 0:
            continue
        payload = body[record.payload_offset : record.payload_offset + record.payload_size]
        result = walk_record(payload, ARG_COUNT[i])
        states = "OK" if (
            len(result["entries"]) == result["ops"]
            and result["word_cursor"] == result["cells"]
            and result["aux_consumed"] == 15 * result["ops"]
        ) else "MISMATCH"
        print(
            "== %-18s ops=%3d cells=%3d walked=%3d cursor=%3d aux=%3d %s"
            % (
                NAMES[i - 1],
                result["ops"],
                result["cells"],
                len(result["entries"]),
                result["word_cursor"],
                result["aux_consumed"],
                states,
            )
        )
        for entry in result["entries"][:limit]:
            print(format_entry(entry, record.literals))
        if limit and len(result["entries"]) > limit:
            print("  ... %d more" % (len(result["entries"]) - limit))


if __name__ == "__main__":
    main(sys.argv)
