"""Recover the ionCube 7.4 opcode mask from a 32-bit key pair.

`sub_180097AA0` reads the mask **twice** per instruction when the encoder major
is 6 or more:

    opcode = stored ^ A[i] ^ A[i + ops + 2]

where `A` is one continuous byte stream (`tools/ic72_opcode_mask.mask_stream`,
the 7.2 two-word multiply-add: `0x7689` / `0x4650`, `ROL16`, XOR with the
header's `bytecode_xor_key`).  The second read escapes 7.2's `0x95` sentinel, so
the two bytes are always taken from the same stream at a distance of
`ops + 2` bytes.

So the byte a record hides is `A[i] ^ A[i + ops + 2]`, and the record is
decodable as soon as its 32-bit pair `(s0, s1)` is known.  For 92 of the 112
sample op_arrays that pair is stored in the body before the op block and this
tool reproduces every masked byte; the remaining 20 take their seed from
outside the record stream (`docs/ioncube-74-static.md`, "the mask, found").

    python tools/ic74_mask.py contacts.php --truth contacts.opcodes.json
    python tools/ic74_mask.py contacts.php --truth contacts.opcodes.json --scan
    python tools/ic74_mask.py contacts.php --name getTotalSendGroups --seed 1bb0:59ea
"""

from __future__ import annotations

import argparse
import json
import struct
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from tools.ic72_opcode_mask import mask_stream  # noqa: E402
from tools.ic74_static_dump import (  # noqa: E402
    decode_body,
    op_block_start,
    scan_body,
    walk_ops,
)

SECOND_BYTE_DELTA = 2


def stored_bytes(body: bytes, start: int, count: int) -> bytes:
    ops, _ = walk_ops(body, start, count, bytes(count))
    return bytes(op["opcode"] & 0xFF for op in ops)


def predict(s0: int, s1: int, xor_key: int, count: int) -> bytes:
    """The `count` mask bytes a record with this key pair is encoded with."""

    data = mask_stream(s0, s1, xor_key, 4 * count + 128)
    return bytes(data[i] ^ data[i + count + SECOND_BYTE_DELTA] for i in range(count))


def decode_record(
    body: bytes, start: int, count: int, s0: int, s1: int, xor_key: int
) -> list[int]:
    mask = predict(s0, s1, xor_key, count)
    return [stored ^ mask[index] for index, stored in enumerate(stored_bytes(body, start, count))]


def find_seed(
    body: bytes, limit: int, count: int, xor_key: int, target: bytes, window: int
) -> tuple[int, int, int] | None:
    """First ``(offset, s0, s1)`` before *limit* whose stream predicts *target*."""

    for offset in range(max(0, limit - window), limit):
        s0, s1 = struct.unpack_from("<II", body, offset)
        if predict(s0, s1, xor_key, count) == target:
            return offset, s0, s1
    return None


def truth_opcodes(path: Path) -> dict[str, list[int]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    out: dict[str, list[int]] = {}
    for entry in (data.get("op_arrays") or {}).values():
        name = entry.get("function_name")
        name = name.get("value") if isinstance(name, dict) else name
        if name:
            out[name] = [int(item["opcode"]) for item in (entry.get("opcodes") or [])]
    return out


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path", type=Path, help="encoded PHP file")
    parser.add_argument("--truth", type=Path, help="runtime opcode dump to check against")
    parser.add_argument("--name", help="op_array to decode with --seed")
    parser.add_argument("--seed", help="key pair as s0:s1, hex")
    parser.add_argument("--scan", action="store_true", help="list every record")
    parser.add_argument("--window", type=int, default=1400, help="seed search window")
    parser.add_argument("--payload-index", type=int, default=0)
    args = parser.parse_args(argv)

    header, body = decode_body(args.path, args.payload_index)
    xor_key = int(str(header["initial_header"]["bytecode_xor_key"]), 0)
    entries = scan_body(body)["entries"]
    print(f"bytecode_xor_key {xor_key:#010x} records {len(entries)}")

    if args.name and args.seed:
        entry = next(item for item in entries if item["name"] == args.name)
        s0, s1 = (int(part, 16) for part in args.seed.split(":"))
        start = op_block_start(body, entry["end"])
        opcodes = decode_record(body, start, entry["opcodes"], s0, s1, xor_key)
        print(f"{entry['name']} ops={entry['opcodes']} block={start:#07x}")
        print(" ".join(f"{value:02x}" for value in opcodes))
        return 0

    if not args.truth:
        print("pass --truth to verify, or --name/--seed to decode one record")
        return 2

    truth = truth_opcodes(args.truth)
    recovered = checked = 0
    for entry in entries:
        want = truth.get(entry["name"])
        if want is None or len(want) != entry["opcodes"]:
            continue
        checked += 1
        start = op_block_start(body, entry["end"])
        stored = stored_bytes(body, start, entry["opcodes"])
        target = bytes(stored[i] ^ want[i] for i in range(len(want)))
        hit = find_seed(body, entry["offset"], entry["opcodes"], xor_key, target, args.window)
        if hit is None:
            if args.scan:
                print(f"{entry['name']:<34} ops={entry['opcodes']:<5} no seed before record")
            continue
        offset, s0, s1 = hit
        opcodes = decode_record(body, start, entry["opcodes"], s0, s1, xor_key)
        if opcodes == want:
            recovered += 1
        if args.scan:
            print(
                f"{entry['name']:<34} ops={entry['opcodes']:<5} block={start:#07x} "
                f"seed={offset:#07x} ({entry['offset'] - offset:+d}) {s0:#010x} {s1:#010x}"
            )
    print(f"records with a stored key pair {recovered}/{checked}")
    return 0 if recovered else 1


if __name__ == "__main__":
    raise SystemExit(main())
