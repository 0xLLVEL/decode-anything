"""Walk sv5 (PHP 7.2) op_array records out of a decoded program blob.

Read order recovered from the 7.2 loader. Field names track the loader's own
stores into ``zend_op_array``.

``sub_1800A02A0`` -- record framing, keyed branch (``php_flags & 0x8000``)::

    u32 payload_size
    u32 key1
    u32 key2
    sub_1800A0090 ...
    u32 stored_size
    payload[payload_size]

``sub_1800A0090`` -- field order::

    sub_180003730   u8 flag
                    u32 n1, then B830(n1) bytes
                    u32 n2, then n2 * (u32 len + B830(len) bytes)
                    u32 -> +64
                    u32 -> +68
    sub_18009FFC0   u16 name_len, name_len + 1 bytes (0 means no name)
    20 bytes        descriptor (sub_18009D610 == B830(20))
    u32             -> +32 (arg count seed)
    u32             -> +36
    u32             fn_flags, then ``&= ~8``
    sub_18009E500   argument table, count = sub_18000C8D0(op_array):
                    per argument u32 flag, string when set,
                    u32 flag, string when set, then 4 raw bytes
    u32             -> +72 (literal count)
    sub_18009DFE0   per literal: sub_18000B8A0 string + 8-byte key
    u32             -> +24
    u8              construct flag
    u32             filename reference, 0xFFFFFFFF means none, else a string

``sub_18000B8A0`` -- string: ``u32 word``. A negative word means the empty
string, otherwise the payload is ``word & 0x9FFFFFFF`` bytes plus one NUL when
bit 29 is clear.

Group level (``sub_1800A16E0``) wraps the records: one ``u32`` gate word, then
the file-level op_array, then a ``u16`` function count and that many function
records, then a ``u16`` class count.
"""

from __future__ import annotations

import argparse
import json
import re
import struct
import sys
from dataclasses import dataclass, field, asdict
from pathlib import Path

NEGATIVE_WORD = 0x80000000
FILENAME_NONE = 0xFFFFFFFF
MAX_ARGUMENTS = 64
MAX_LITERALS = 8192


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
    text: str
    key: int


@dataclass
class Argument:
    flags_first: int
    name: str
    flags_second: int
    type_name: str
    tail: bytes


@dataclass
class Record:
    start: int
    payload_size: int
    key1: int
    key2: int
    block_flag: int = 0
    block_n1: int = 0
    block_n2: int = 0
    block_64: int = 0
    block_68: int = 0
    name: str = ""
    descriptor: bytes = b""
    arg_seed: int = 0
    field_36: int = 0
    fn_flags: int = 0
    arguments: list[Argument] = field(default_factory=list)
    literal_count: int = 0
    literals: list[Literal] = field(default_factory=list)
    field_24: int = 0
    construct: bool = False
    filename: str | None = None
    stored_size: int = 0
    payload_offset: int = 0
    end: int = 0

    def to_json(self) -> dict:
        out = asdict(self)
        out["descriptor"] = self.descriptor.hex()
        out["arguments"] = [
            {**asdict(item), "tail": item.tail.hex()} for item in self.arguments
        ]
        out["literals"] = [asdict(item) for item in self.literals]
        for key in ("start", "payload_offset", "end"):
            out[key] = hex(out[key])
        for key in ("key1", "key2", "fn_flags"):
            out[key] = hex(out[key])
        return out


def argument_count(fn_flags: int, arg_seed: int) -> int:
    """``sub_18000C8D0`` -- required argument count with flags folded in."""
    count = arg_seed + 1 if fn_flags & 0x40000000 else arg_seed
    if fn_flags & 0x01000000:
        count += 1
    return count


def read_record(stream: Stream) -> Record:
    start = stream.pos
    record = Record(start=start, payload_size=stream.u32(), key1=stream.u32(), key2=stream.u32())
    if record.payload_size > len(stream.data):
        raise Truncated(f"payload {record.payload_size} at {start:#x}")

    record.block_flag = stream.u8()
    record.block_n1 = stream.u32()
    stream.take(record.block_n1)
    record.block_n2 = stream.u32()
    if record.block_n2 > MAX_ARGUMENTS:
        raise Truncated("field block entry count")
    for _ in range(record.block_n2):
        stream.take(stream.u32())
    record.block_64 = stream.u32()
    record.block_68 = stream.u32()

    record.name = stream.name()
    record.descriptor = stream.take(20)
    record.arg_seed = stream.u32()
    record.field_36 = stream.u32()
    record.fn_flags = stream.u32() & ~8

    for _ in range(argument_count(record.fn_flags, record.arg_seed)):
        first = stream.u32()
        name = stream.string() if first else ""
        second = stream.u32()
        type_name = stream.string() if second else ""
        record.arguments.append(Argument(first, name, second, type_name, stream.take(4)))

    record.literal_count = stream.u32()
    if record.literal_count > MAX_LITERALS:
        raise Truncated("literal count")
    for _ in range(record.literal_count):
        text = stream.string()
        record.literals.append(Literal(text, struct.unpack("<Q", stream.take(8))[0]))

    record.field_24 = stream.u32()
    record.construct = bool(stream.u8())
    filename = stream.u32()
    record.filename = None if filename == FILENAME_NONE else stream.string()

    record.stored_size = stream.u32()
    record.payload_offset = stream.pos
    stream.take(record.payload_size)
    record.end = stream.pos
    return record


def walk(body: bytes, skip: int = 4, limit: int = 512) -> tuple[list[Record], int]:
    stream = Stream(body, skip)
    records: list[Record] = []
    while stream.pos < len(body) and len(records) < limit:
        snapshot = stream.pos
        try:
            records.append(read_record(stream))
        except Truncated:
            stream.pos = snapshot
            break
    return records, stream.pos


def resync(body: bytes, skip: int = 4, limit: int = 512) -> list[Record]:
    """Walk, skipping group-level words that are not record starts."""
    stream = Stream(body, skip)
    records: list[Record] = []
    while stream.pos < len(body) - 16 and len(records) < limit:
        snapshot = stream.pos
        try:
            records.append(read_record(stream))
        except Truncated:
            stream.pos = snapshot + 1
    return records


PRINTABLE_RUN = re.compile(rb"[ -~]{5,}")


def payload_strings(body: bytes, record: Record, limit: int = 40) -> list[str]:
    payload = body[record.payload_offset:record.end]
    runs = [match.group().decode("latin-1") for match in PRINTABLE_RUN.finditer(payload)]
    return runs[:limit]


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("body", type=Path)
    ap.add_argument("--skip", type=lambda s: int(s, 0), default=4)
    ap.add_argument("--limit", type=int, default=512)
    ap.add_argument("--resync", action="store_true", help="skip non-record words")
    ap.add_argument("--strings", type=int, default=0, help="print N payload runs per record")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)

    body = args.body.read_bytes()
    records = resync(body, args.skip, args.limit) if args.resync else walk(body, args.skip, args.limit)[0]

    if args.json:
        print(json.dumps([r.to_json() for r in records], indent=2))
        return 0

    print(f"body {len(body)} B, {len(records)} record(s)")
    for index, record in enumerate(records):
        print(
            f"\n#{index} {record.start:#06x}..{record.end:#06x} "
            f"payload={record.payload_size} keys={record.key1:#010x}/{record.key2:#010x}"
        )
        print(f"   name={record.name!r} fn_flags={record.fn_flags:#x} "
              f"descriptor={record.descriptor.hex()}")
        print(f"   block flag={record.block_flag} 64={record.block_64} 68={record.block_68}")
        print(f"   arg_seed={record.arg_seed} field_36={record.field_36} "
              f"args={len(record.arguments)} literals={record.literal_count} "
              f"field_24={record.field_24} construct={record.construct} "
              f"filename={record.filename!r}")
        for argument in record.arguments:
            print(f"     arg {argument.name!r} type={argument.type_name!r}")
        for literal in record.literals[:8]:
            print(f"     lit {literal.text[:44]!r} key={literal.key:#018x}")
        if record.literal_count > 8:
            print(f"     ... {record.literal_count - 8} more literals")
        if record.stored_size != record.payload_size:
            print(f"   stored_size={record.stored_size} differs from payload")
        if args.strings:
            for run in payload_strings(body, record, args.strings):
                print(f"     str {run[:100]!r}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
