"""Partition a 7.2 function record and resolve every string it names.

Byte stream, front to back:

    0x0000  112       header
    0x0070    4       copied to op_array+24
    0x0074   16       name entry: [refcount, type, offset, length], offset into the pool
    0x0084    4       name-table count for sub_18009DDB0
    0x0088   20*n     argument table, n from sub_18000C8D0
    ?         8       op header: [ops, cells]
    ?      4*cells    word array, closed by a 0xFFFFFFFF cell
    ?         4       aux entry count, always 3 * ops
    ?       5*count   aux array, 15 bytes per opcode
    ?      16*lits    literal table, entries shaped like the name entry
    ?      12*consts  constant pool
    ?         4       unused head of the tail
    ?         4       pool size in bytes
    ?       size      string pool, every offset in this record indexes into it
    ?     16*args2    trailing table keyed by header[0x58]

The pool is the anchor: the name entry and every literal entry carry
(offset, length) pairs that resolve against it, so a wrong offset anywhere above
shows up as garbage text rather than as a plausible number.

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


def layout(payload: bytes, name: str, flags: int) -> None:
    header = struct.unpack_from("<28I", payload, 0)
    args = header[0x14 // 4]
    literals = header[0x2C // 4]
    constants = header[0x38 // 4]

    head_at = PREFIX_END + ENTRY * args
    ops, cells = struct.unpack_from("<2I", payload, head_at)
    array_at = head_at + 8
    end_at = array_at + 4 * cells
    term = struct.unpack_from("<I", payload, end_at - 4)[0]

    aux_count = struct.unpack_from("<I", payload, end_at)[0]
    lit_at = end_at + 4 + 5 * aux_count
    const_at = lit_at + 16 * literals
    tail_at = const_at + 12 * constants
    pool_at = tail_at + 8
    pool_size = struct.unpack_from("<I", payload, tail_at + 4)[0]

    print("== %s  desc=0x%08x" % (name, flags))
    print("   arg table   0x%04x  %d x %d" % (PREFIX_END, args, ENTRY))
    print("   op header   0x%04x  ops=%d cells=%d (escapes=%d)" % (head_at, ops, cells, cells - ops))
    print("   word array  0x%04x  %s" % (array_at, "closes" if term == TERMINATOR else "TERMINATOR %#010x" % term))
    print("   aux array   0x%04x  %d entries = 3 * ops: %s, %d bytes"
          % (end_at + 4, aux_count, aux_count == 3 * ops, 5 * aux_count))
    print("   literals    0x%04x  %d" % (lit_at, literals))
    print("   constants   0x%04x  %d" % (const_at, constants))
    print("   pool        0x%04x  %d bytes, %d trailing" % (pool_at, pool_size, len(payload) - pool_at - pool_size))

    def text(offset: int, length: int) -> bytes:
        return payload[pool_at + offset:pool_at + offset + length]

    entry = struct.unpack_from("<4I", payload, 0x74)
    print("   name        refcount=%d type=%d %r" % (entry[0], entry[1], text(entry[2], entry[3])))

    good = 0
    for index in range(literals):
        refcount, kind, offset, length = struct.unpack_from("<4I", payload, lit_at + 16 * index)
        body = text(offset, length)
        printable = bool(body) and all(32 <= byte < 127 for byte in body)
        good += printable
        if index < 8:
            print("     lit[%2d] %d/%d off=%-5d len=%-4d %r%s"
                  % (index, refcount, kind, offset, length, body, "" if printable else "  NON-TEXT"))
    if literals:
        print("   literals resolve %d/%d" % (good, literals))


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
