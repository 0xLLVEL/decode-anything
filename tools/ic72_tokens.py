"""Dump the packed instruction stream of a 7.2 function record.

The stream is a word sequence that ends at the first 0xffffffff. Most words are
operand tokens:

    [value:u8] [class:u8] [line:u8] [0]

`line` always falls inside the function's line range, which the payload states
at +0x50/+0x54 and which orders the records in source order. Remaining words are
raw immediates spliced between tokens.

    python tools/ic72_tokens.py scratch_body72.bin
    python tools/ic72_tokens.py scratch_body72.bin --record call_bp_proxy --stream
"""

import argparse
import struct
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tools.ic72_record_walk import resync  # noqa: E402

CLASSES = (0x07, 0x0F, 0x1F)
NAME_RECORD = 0x74
STREAM_START = 0x90
TERMINATOR = 0xFFFFFFFF


def words(payload, start):
    for off in range(start, len(payload) - 3, 4):
        yield off, struct.unpack_from("<I", payload, off)[0]


def parse(payload):
    if struct.unpack_from("<I", payload, 0)[0] != 0x5BDFAC02:
        raise ValueError("not a 7.2 function payload")
    literal_count, opcode_count = struct.unpack_from("<2I", payload, 0x2C)
    line_lo, line_hi = struct.unpack_from("<2I", payload, 0x50)
    refcount, ztype, _pad, name_len, _hash, a, b = struct.unpack_from("<7I", payload, NAME_RECORD)
    if refcount != 1 or ztype != 6:
        raise ValueError("name record not at +0x74")
    return {
        "literal_count": literal_count,
        "opcode_count": opcode_count,
        "line_lo": line_lo,
        "line_hi": line_hi,
        "name_len": name_len,
        "field_a": a,
        "field_b": b,
    }


def stream(payload, line_lo, line_hi):
    tokens = []
    immediates = []
    end = None
    for off, word in words(payload, STREAM_START):
        if word == TERMINATOR:
            end = off
            break
        raw = payload[off:off + 4]
        if raw[3] == 0 and raw[1] in CLASSES and line_lo <= raw[2] <= line_hi:
            tokens.append((off, raw[0], raw[1], raw[2]))
        else:
            immediates.append((off, word))
    return tokens, immediates, end


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("body", help="decoded program body (scratch_body72.bin)")
    ap.add_argument("--record", help="only this record name")
    ap.add_argument("--stream", action="store_true", help="print the word stream in order")
    args = ap.parse_args()

    body = open(args.body, "rb").read()
    for record in resync(body, 4):
        if record.name == "_file" or not record.name:
            continue
        if args.record and record.name != args.record:
            continue
        payload = body[record.payload_offset:record.payload_offset + record.payload_size]
        if struct.unpack_from("<I", payload, 0)[0] != 0x5BDFAC02:
            continue
        meta = parse(payload)
        tokens, immediates, end = stream(payload, meta["line_lo"], meta["line_hi"])
        classes = {}
        for _off, _value, cls, _line in tokens:
            classes[cls] = classes.get(cls, 0) + 1
        print("%-18s ops=%3d lits=%2d lines=%d..%d tokens=%3d imm=%2d "
              "stream=%#06x..%#06x words/op=%.2f"
              % (record.name, meta["opcode_count"], meta["literal_count"],
                 meta["line_lo"], meta["line_hi"], len(tokens), len(immediates),
                 STREAM_START, end or 0,
                 (len(tokens) + len(immediates)) / max(meta["opcode_count"], 1)))
        print("    classes %s" % {hex(k): v for k, v in sorted(classes.items())})
        if args.stream:
            by_offset = {off: ("tok", value, cls, line) for off, value, cls, line in tokens}
            by_offset.update({off: ("imm", value, 0, 0) for off, value in immediates})
            for off in sorted(by_offset):
                kind, value, cls, line = by_offset[off]
                if kind == "tok":
                    print("    %#06x  tok  value=%3d class=%#04x line=%3d" % (off, value, cls, line))
                else:
                    print("    %#06x  imm  %d" % (off, value))
    return 0


if __name__ == "__main__":
    sys.exit(main())
