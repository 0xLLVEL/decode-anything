"""Split a 7.2 function record into its sections and print every span.

The record is a byte stream read front to back.  Every section boundary below is
an offset that can be checked, not an inference:

    0x00   112   header
    0x70   4     copied to op_array+24
    0x74   16    name entry, [u32 u32 u32 u32] with a zend string header
    0x84   4     name-table count for sub_18009DDB0 (zero in every record here)
    0x88   20*n  argument table, n from sub_18000C8D0; entry is two
                 (offset, length) string refs plus four flag bytes
    ?      8     opcode-section header: [payload[0x24], cell count]
    ?      4*cells  the word array, one cell per operand slot, closed by a
                 0xFFFFFFFF cell that the header's count includes

The cell count is the load-bearing number: the dword immediately before the
array equals (cells), and the array begins at 0x88 + 20*args + 8 and ends one
cell past the 0xFFFFFFFF terminator.  All four records close exactly.

    python tools/ic72_record_layout.py <body> [--record N]
"""

from __future__ import annotations

import argparse
import struct
from pathlib import Path

from ic72_record_walk import resync

PREFIX_END = 0x88
ENTRY = 20
TERMINATOR = 0xFFFFFFFF


def arg_count_from_header(header: tuple[int, ...]) -> int:
    """sub_18000C8D0. Argument count, plus the receiver slots fn_flags asks for."""
    return header[0x14 // 4]


def layout(payload: bytes, name: str, flags: int) -> None:
    header = struct.unpack_from("<28I", payload, 0)
    args = arg_count_from_header(header)
    literals = header[0x2C // 4]
    constants = header[0x38 // 4]

    arg_at = PREFIX_END
    head_at = arg_at + ENTRY * args
    array_at = head_at + 8

    if array_at + 8 > len(payload):
        print("== %s  OVERRUN: array would start at %#x" % (name, array_at))
        return

    image = struct.unpack_from("<2I", payload, head_at)
    cells = image[1]
    word_cells = cells - 1

    end_at = array_at + 4 * cells
    term_at = end_at - 4
    terminator = struct.unpack_from("<I", payload, term_at)[0] if term_at + 4 <= len(payload) else None
    closes = terminator == TERMINATOR

    print("== %s  desc=0x%08x" % (name, flags))
    words = [struct.unpack_from("<I", payload, array_at + 4 * k)[0] for k in range(max(0, word_cells))]
    escapes = sum(1 for w in words if ((w >> 8) & 0xFF) == 0x1F or ((w >> 16) & 0xFFFF) == 0xFFFF)
    slots = cells - escapes

    print("   header          0x0000  112")
    print("   op_array+24     0x0070  4")
    print("   name entry      0x0074  16")
    print("   name count      0x0084  %d" % struct.unpack_from("<I", payload, 0x84)[0])
    print("   arg table       0x%04x  %d x %d = %d" % (arg_at, args, ENTRY, ENTRY * args))
    print("   op header       0x%04x  slots=%d cells=%d  %s"
          % (head_at, image[0], image[1],
             "consistent" if image[0] == slots else "h24 %d != cells-escapes %d" % (image[0], slots)))
    print("   word array      0x%04x  %d cells (%d words + terminator), %d escapes"
          % (array_at, cells, word_cells, escapes))
    print("   terminator      0x%04x  %s" % (term_at, "0xFFFFFFFF" if closes else "%#010x BAD" % terminator))
    print("   literals=%d constpool=%d" % (literals, constants))

    if not closes:
        return

    table_at = end_at + 4
    if table_at + 4 <= len(payload):
        size = struct.unpack_from("<I", payload, end_at)[0]
        print("   slot table      0x%04x  u32 size=%d == 3*%d: %s, then %d trailing bytes"
              % (end_at, size, image[0], size == 3 * image[0], len(payload) - table_at - size))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("body")
    ap.add_argument("--record", type=int)
    args = ap.parse_args()

    body = Path(args.body).read_bytes()
    for index, rec in enumerate(resync(body, 4)):
        if index == 0:
            continue
        if args.record is not None and index != args.record:
            continue
        payload = body[rec.payload_offset:rec.payload_offset + rec.payload_size]
        layout(payload, rec.name, struct.unpack_from("<I", rec.descriptor, 4)[0])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
