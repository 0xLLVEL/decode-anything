"""Walk a 7.2 function record in the loader's own read order.

The order is fixed by sub_18009FC70, which calls, in sequence:

    sub_18009E240  112-byte header, then u32, then the name entry (16 bytes)
    sub_18009DDB0  class/constant name table: u32 count, then count pairs of strings
    sub_18009DD90  16 * header[0x3c] bytes
    sub_18009E770  20 * argcount bytes
    sub_18009ED60  u32 opcodes, u32 words, 4*words, u32 aux, 5*aux
    sub_18009DF10  16 * header[0x2c] bytes, the literal table
    sub_18009E110  12 * header[0x38] bytes, the constant pool
    reader          u32, u32, then a blob of the second u32's length
    sub_18009F710  16 * header[0x58] bytes

Each span is printed with its offset so a disagreement with the known word array
shows up as a number rather than as a theory.

    python tools/ic72_record_layout.py <body> [--record N]
"""

from __future__ import annotations

import argparse
import struct
from pathlib import Path

from ic72_record_walk import resync


class Cursor:
    def __init__(self, payload: bytes):
        self.data = payload
        self.at = 0

    def u32(self, label: str):
        value = struct.unpack_from("<I", self.data, self.at)[0]
        print("  %-22s %#06x  %d" % (label, self.at - 4, value))
        return value

    def skip(self, count: int, label: str):
        start = self.at
        self.at += count
        if count:
            print("  %-22s %#06x  %d bytes" % (label, start, count))
        return start

    def take_u32(self, label: str):
        start = self.at
        if start + 4 > len(self.data):
            print("  %-22s %#06x  OVERRUN" % (label, start))
            raise SystemExit(0)
        self.at += 4
        value = struct.unpack_from("<I", self.data, start)[0]
        print("  %-22s %#06x  %d" % (label, start, value))
        return value

    def string(self, label: str):
        word = self.take_u32(label + " len")
        if word & 0x80000000:
            return
        length = word & 0xBFFFFFFF
        if not word & 0x20000000:
            length += 1
        self.skip(length, label + " bytes")


def walk(payload: bytes, name: str, use_header_args: bool = False) -> None:
    header = struct.unpack_from("<28I", payload, 0)
    args, literals = header[5], header[0x2C // 4]
    constants, extra = header[0x38 // 4], header[0x3C // 4]
    line_lo, argtab = header[0x50 // 4], header[0x58 // 4]

    print("== %s  args=%d literals=%d constpool=%d extra=%d line_lo=%d argtab=%d"
          % (name, args, literals, constants, extra, line_lo, argtab))

    cur = Cursor(payload)
    cur.skip(112, "header")
    cur.take_u32("op_array+24")
    cur.skip(16, "name entry")

    count = cur.take_u32("name table count")
    for index in range(min(count, 64)):
        cur.string("  name[%d]" % index)
        cur.string("  value[%d]" % index)

    cur.skip(16 * extra, "extra table")
    cur.skip(20 * args if use_header_args else 0, "arg table")

    opcodes = cur.take_u32("opcode count")
    words = cur.take_u32("word count")
    word_at = cur.skip(4 * words, "word array")
    aux = cur.take_u32("aux count")
    cur.skip(5 * aux, "aux array")

    cur.skip(16 * literals, "literal table")
    cur.skip(12 * constants, "const pool")
    cur.take_u32("field A")
    size = cur.take_u32("blob size")
    cur.skip(size, "blob")
    cur.skip(16 * argtab, "trailing table")

    print("  %-22s %#06x  end" % ("", cur.at))
    print("  %-22s %#06x  word array start" % ("", word_at))
    print("  %-22s %d / %d" % ("stream counts", opcodes, words))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("body")
    ap.add_argument("--record", type=int)
    ap.add_argument("--header-args", action="store_true",
                    help="skip 20 bytes per header-level argument count")
    args = ap.parse_args()

    body = Path(args.body).read_bytes()
    for index, rec in enumerate(resync(body, 4)):
        if index == 0:
            continue
        if args.record is not None and index != args.record:
            continue
        payload = body[rec.payload_offset:rec.payload_offset + rec.payload_size]
        walk(payload, rec.name, args.header_args)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
