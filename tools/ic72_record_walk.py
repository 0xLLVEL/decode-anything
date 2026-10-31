"""Walk sv5 (PHP 7.2) op_array records out of a decoded program blob.

Read order recovered from the 7.2 loader:

  sub_1800A02A0   record framing (dynamic-key branch)
       u32 A, u32 key1, u32 key2, fields..., u32 blob_len, blob[A] bytes
  sub_1800A0090   field order
       sub_180003730   u8, u32 + bytes, u32 count { u32 len + bytes }, u32, u32
       sub_18009FFC0   u16 len, len+1 bytes
       20 bytes        descriptor (sub_18009D610 == B830(20))
       u32, u32, u32   op_array +0x20, +0x24, fn_flags
       sub_18009E500   args: per arg u32 flag, string when flag != 0
       u32             literal_count, then sub_18009DFE0 per literal:
                       string + 8-byte key
       u32             num_args
       u8              construct flag
       u32             filename reference, 0xFFFFFFFF means none
  sub_18000B8A0   string: u32 word; negative word means empty, otherwise
                  length = word & 0x9FFFFFFF with one extra byte when bit 29
                  is clear.
"""

from __future__ import annotations

import argparse
import json
import struct
import sys
from dataclasses import dataclass, field, asdict
from pathlib import Path

NEGATIVE_WORD = 0x80000000


class Truncated(Exception):
    pass


class Stream:
    def __init__(self, data: bytes, pos: int = 0):
        self.data = data
        self.pos = pos

    def take(self, count: int) -> bytes:
        if count < 0 or self.pos + count > len(self.data):
            raise Truncated(f"need {count} bytes at {self.pos:#x}")
        chunk = self.data[self.pos:self.pos + count]
        self.pos += count
        return chunk

    def u8(self) -> int:
        return self.take(1)[0]

    def u16(self) -> int:
        return struct.unpack("<H", self.take(2))[0]

    def u32(self) -> int:
        return struct.unpack("<I", self.take(4))[0]

    def string(self) -> str:
        word = self.u32()
        if word & NEGATIVE_WORD:
            return ""
        length = word & 0x9FFFFFFF
        raw = self.take(length + (0 if word & 0x20000000 else 1))
        return raw[:length].decode("latin-1")

    def name(self) -> str:
        length = self.u16()
        if not length:
            return ""
        raw = self.take(length + 1)
        return raw[:length].decode("latin-1")


@dataclass
class Literal:
    name: str
    key: int


@dataclass
class Record:
    start: int
    payload_size: int
    key1: int
    key2: int
    header_flag: int = 0
    header_blobs: list[str] = field(default_factory=list)
    header_a: int = 0
    header_b: int = 0
    name: str = ""
    descriptor: bytes = b""
    field_20: int = 0
    field_24: int = 0
    fn_flags: int = 0
    args: list[int] = field(default_factory=list)
    literal_count: int = 0
    literals: list[Literal] = field(default_factory=list)
    num_args: int = 0
    construct: int = 0
    filename: str | None = None
    blob_len: int = 0
    blob_offset: int = 0
    end: int = 0

    def to_json(self) -> dict:
        out = asdict(self)
        out["descriptor"] = self.descriptor.hex()
        out["literals"] = [asdict(item) for item in self.literals]
        for key in ("start", "blob_offset", "end"):
            out[key] = hex(out[key])
        out["key1"] = hex(self.key1)
        out["key2"] = hex(self.key2)
        out["fn_flags"] = hex(self.fn_flags)
        return out


def read_record(stream: Stream, arg_count: int | None = None) -> Record:
    start = stream.pos
    record = Record(start=start, payload_size=0, key1=0, key2=0)
    record.payload_size = stream.u32()
    record.key1 = stream.u32()
    record.key2 = stream.u32()

    record.header_flag = stream.u8()
    inline = stream.u32()
    if inline:
        record.header_blobs.append(stream.take(inline).hex()[:64])
    count = stream.u32()
    for _ in range(count):
        length = stream.u32()
        record.header_blobs.append(stream.take(length).hex()[:64])
    record.header_a = stream.u32()
    record.header_b = stream.u32()

    record.name = stream.name()
    record.descriptor = stream.take(20)
    record.field_20 = stream.u32()
    record.field_24 = stream.u32()
    record.fn_flags = stream.u32()

    for _ in range(arg_count or 0):
        flag = stream.u32()
        record.args.append(flag)
        if flag:
            stream.string()

    record.literal_count = stream.u32()
    for _ in range(record.literal_count):
        literal_name = stream.string()
        key = struct.unpack("<Q", stream.take(8))[0]
        record.literals.append(Literal(literal_name, key))

    record.num_args = stream.u32()
    record.construct = stream.u8()

    filename = stream.u32()
    record.filename = None if filename == 0xFFFFFFFF else stream.string()

    record.blob_len = stream.u32()
    record.blob_offset = stream.pos
    stream.take(record.payload_size)
    record.end = stream.pos
    return record


def walk(body: bytes, skip: int = 4, limit: int = 64) -> tuple[list[Record], int]:
    stream = Stream(body, skip)
    records: list[Record] = []
    while stream.pos < len(body) and len(records) < limit:
        snapshot = stream.pos
        try:
            record = read_record(stream)
        except Truncated:
            stream.pos = snapshot
            break
        records.append(record)
    return records, stream.pos


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("body", type=Path)
    ap.add_argument("--skip", type=lambda s: int(s, 0), default=4)
    ap.add_argument("--limit", type=int, default=64)
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)

    body = args.body.read_bytes()
    records, stopped = walk(body, args.skip, args.limit)

    if args.json:
        print(json.dumps(
            {"records": [r.to_json() for r in records], "stopped_at": hex(stopped)},
            indent=2,
        ))
        return 0

    print(f"body {len(body)} B, walked from {args.skip:#x}, stopped at {stopped:#x}")
    for index, record in enumerate(records):
        print(
            f"\n#{index} {record.start:#06x}..{record.end:#06x} "
            f"A={record.payload_size} keys={record.key1:#010x}/{record.key2:#010x}"
        )
        print(f"   name={record.name!r} flag={record.header_flag} "
              f"a={record.header_a} b={record.header_b} blobs={len(record.header_blobs)}")
        print(f"   +20={record.field_20} +24={record.field_24} fn_flags={record.fn_flags:#x} "
              f"args={len(record.args)}")
        print(f"   literals={record.literal_count} num_args={record.num_args} "
              f"construct={record.construct} filename={record.filename!r}")
        print(f"   blob_len={record.blob_len} blob@{record.blob_offset:#06x}")
        for literal in record.literals[:4]:
            print(f"     lit {literal.name[:40]!r} key={literal.key:#018x}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
