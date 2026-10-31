"""Split a decoded 7.2 word stream into ops using the loader's own operand table.

The loader builds one 32-byte op per iteration of sub_18009F1B0 and stops when the
word cursor reaches the count it read from the payload, so a record's word count
and opcode count are both known. This tool asks the only question left: which
opcode byte makes the words divide into exactly that many ops.

    op split <binary> <body> [--record N] [--pad N]

Word layout is [value:u8][class:u8][line:u16], little endian. The op word carries
the opcode in the low byte, the result-type selector in bits 11..12 of `class`,
and the line in the high half. Operand words carry the same shape, which is why
every word, not only the first of an op, has a class and a line.
"""

from __future__ import annotations

import argparse
import struct
from pathlib import Path

from ic72_record_walk import resync
from ic72_vm_table import SPEC_ARRAY, Image

ESCAPE_RESULT = 0x1F
ESCAPE_LINE = 0xFFFF


def popcount(n: int) -> int:
    return bin(n & 7).count("1")


def word_span(payload: bytes, first: int = 0x90):
    """The word stream runs from +0x90 to the first 0xffffffff on a word boundary."""
    for offset in range(first, len(payload) - 3, 4):
        if struct.unpack_from("<I", payload, offset)[0] == 0xFFFFFFFF:
            return first, offset
    return first, len(payload) & ~3


def split(words: list[int], spec: list[int], pad: int, escapes: bool):
    """Return (op count, words consumed) or None when the walk overruns.

    Every word may be followed by an escape word: `class == 0x1f` makes the
    loader read the next word as the op's result-type payload, and a line of
    0xffff makes it read the next word as the line. Both are consumed inline,
    so the escape check belongs to the word, not to the op.
    """
    idx = 0
    ops = 0
    while idx < len(words):
        word = words[idx]
        opcode = ((word & 0xFF) - pad) & 0xFF
        flags = spec[opcode] if opcode < len(spec) else 0
        if not flags:
            return None
        width = 1 + popcount(flags)
        for span in range(idx, idx + width):
            if span + 1 >= len(words):
                break
            tail = words[span + 1]
            if (tail & 0xFF00) >> 8 == ESCAPE_RESULT:
                width += 1
            if (tail >> 16) == ESCAPE_LINE:
                width += 1
        idx += width
        ops += 1
        if idx > len(words):
            return None
    return ops, idx


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("binary")
    ap.add_argument("body")
    ap.add_argument("--record", type=int, help="only this record index")
    ap.add_argument("--pad", type=int, help="only this xor pad, instead of a sweep")
    ap.add_argument("--head", type=int, default=12, help="words to print per op")
    args = ap.parse_args()

    image = Image(args.binary)
    spec = image.u32s(SPEC_ARRAY, 256)
    body = Path(args.body).read_bytes()

    for index, rec in enumerate(resync(body, 4)):
        if args.record is not None and index != args.record:
            continue
        payload = body[rec.payload_offset:rec.payload_offset + rec.payload_size]
        literals, opcodes = struct.unpack_from("<2I", rec.descriptor)
        if index == 0:
            print("%-4s %-18s %-14s %-8s %s" % ("#", "name", "lits/ops", "words", "pads that close exactly"))
            continue
        start, end = word_span(payload)
        raw = payload[start:end]
        words = list(struct.unpack("<%dI" % (len(raw) // 4), raw[:len(raw) // 4 * 4]))
        pads = [args.pad] if args.pad is not None else range(256)
        hits = []
        for pad in pads:
            for escapes in (False, True):
                got = split(words, spec, pad, escapes)
                if got and got[0] == opcodes and got[1] == len(words):
                    hits.append((pad, escapes))
        label = "%d/%d" % (literals, opcodes)
        print("%-4d %-18s %-14s %-8d %s" % (index, rec.name, label, len(words),
                                            hits[:6] if hits else "none"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
