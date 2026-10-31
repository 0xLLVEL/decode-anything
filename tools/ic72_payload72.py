"""Inspect the per-record data segment of an sv5 (PHP 7.2) body.

Each op_array record carries a data segment (``payload``). Four of the five
segments in the PHP 7.2 sample are plaintext images of the compiled function:
a fixed header of dwords, then the literal pool, then the encoded instruction
area.

The header words that matter, verified against the record fields the walker
already parses:

======  ===============================================================
``+00`` ``0x5bdfac02``, constant across every function segment
``+04`` ``fn_flags`` for the function
``+14`` argument count
``+18`` argument count again, zero for a function with no arguments
``+2c`` literal count, equals the record's literal table length
``+30`` opcode count, equals the descriptor's second dword
``+50`` offset of a packed instruction sub-area (exact for ``call_bp_proxy``)
``+54`` second sub-area offset, same caveat
======  ===============================================================

Every other dword in the header is either zero or a ``0x5b......`` value: the
encoder's own address space, kept so the loader can relocate it. They are not
offsets into the segment.
"""

from __future__ import annotations

import argparse
import re
import struct
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tools.ic72_record_walk import resync, walk  # noqa: E402

MAGIC = 0x5BDFAC02

FIELD_NAMES = {
    0x00: "magic",
    0x04: "fn_flags",
    0x08: "address",
    0x0C: "zero",
    0x10: "zero",
    0x14: "arg_count",
    0x18: "arg_count_2",
    0x1C: "address",
    0x20: "address",
    0x24: "field_24",
    0x28: "address",
    0x2C: "literal_count",
    0x30: "opcode_count",
    0x34: "address",
    0x38: "field_38",
    0x3C: "zero",
    0x40: "address",
    0x44: "zero",
    0x48: "zero",
    0x4C: "shared_address",
    0x50: "field_50",
    0x54: "field_54",
    0x58: "zero",
    0x5C: "sentinel",
    0x60: "field_60",
    0x64: "address",
    0x68: "field_68",
}

PRINTABLE_RUN = re.compile(rb"[ -~]{5,}")


def header_words(payload: bytes, limit: int = 0x6C) -> list[tuple[int, str, int]]:
    words = []
    for offset in range(0, min(limit, len(payload)) - 3, 4):
        value = struct.unpack_from("<I", payload, offset)[0]
        words.append((offset, FIELD_NAMES.get(offset, ""), value))
    return words


def describe(record, payload: bytes) -> list[str]:
    lines = []
    fields = {offset: (name, value) for offset, name, value in header_words(payload)}
    magic = fields[0x00][1]
    status = "ok" if magic == MAGIC else "unexpected"
    lines.append(f"   header magic {magic:#010x} ({status})")
    checks = [
        ("fn_flags", record.fn_flags, fields[0x04][1]),
        ("arg_count", len(record.arguments), fields[0x14][1]),
        ("literal_count", record.literal_count, fields[0x2C][1]),
        ("opcode_count", struct.unpack_from("<I", record.descriptor, 4)[0], fields[0x30][1]),
        ("field_24", None, fields[0x24][1]),
        ("field_50", None, fields[0x50][1]),
        ("field_60", None, fields[0x60][1]),
    ]
    for label, expected, actual in checks:
        if expected is None:
            lines.append(f"   {label:<15} {actual}")
        else:
            mark = "match" if expected == actual else f"MISMATCH {expected}"
            lines.append(f"   {label:<15} {actual} ({mark})")
    return lines


def instruction_area(payload: bytes, offset: int, size: int | None = None) -> bytes:
    end = len(payload) if size is None else min(len(payload), offset + size)
    return payload[offset:end]


def hexdump(data: bytes, base: int = 0, width: int = 16) -> str:
    out = []
    for line in range(0, len(data), width):
        chunk = data[line:line + width]
        text = "".join(chr(b) if 32 <= b < 127 else "." for b in chunk)
        out.append(f"{base + line:04x}  {' '.join(f'{b:02x}' for b in chunk):<47}  {text}")
    return "\n".join(out)


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("body", type=Path)
    ap.add_argument("--skip", type=lambda s: int(s, 0), default=4)
    ap.add_argument("--index", type=int, default=None, help="record index")
    ap.add_argument("--name", default=None, help="record name")
    ap.add_argument("--strings", type=int, default=12)
    ap.add_argument("--dump-instr", type=int, default=0, help="bytes of instruction area")
    ap.add_argument("--resync", action="store_true")
    args = ap.parse_args(argv)

    body = args.body.read_bytes()
    records = resync(body, args.skip) if args.resync else walk(body, args.skip)[0]
    if not records:
        print("no records", file=sys.stderr)
        return 1

    targets = records
    if args.index is not None:
        targets = [records[args.index]]
    elif args.name is not None:
        targets = [record for record in records if record.name == args.name]

    for record in targets:
        payload = body[record.payload_offset:record.payload_offset + record.payload_size]
        print(f"\n{record.name or '<file level>'}  segment {record.payload_size} B "
              f"at {record.payload_offset:#06x}")
        for line in describe(record, payload):
            print(line)
        words = struct.unpack("<5I", record.descriptor)
        print(f"   descriptor      literals={words[0]} opcodes={words[1]} "
              f"pad={words[2]}/{words[3]} table={words[4]}")
        runs = [match.group().decode("latin-1") for match in PRINTABLE_RUN.finditer(payload)]
        for run in runs[:args.strings]:
            print(f"   str {run[:96]!r}")
        if len(runs) > args.strings:
            print(f"   ... {len(runs) - args.strings} more runs")
        if args.dump_instr:
            fields = {offset: value for offset, _, value in header_words(payload)}
            start = fields[0x50]
            print(f"   bytes from field_50 ({start:#x}):")
            print(hexdump(instruction_area(payload, start, args.dump_instr), start))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
