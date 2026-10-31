"""Opcode mask for ionCube 7.2 - reproduced without the loader.

The stored opcode byte is `opcode ^ mask[slot]`, and the mask is not in the file.
It is the mask stream built by `sub_18009E8B0`'s caller:

    sub_18009FA20(ctx, op_array, struct)
        struct->mask = alloc(4 * (ops + 1))
        for i in range(ops + 1):
            struct->mask[i] = sub_18009CA60(state)          # u32 per slot
    sub_18009CA60(state)  ->  state->fn(state->data)

`state->fn` is `sub_18009D340`, a two-word multiply-add generator:

    s1 = (s1 & 0xffff) * 0x7689 + (s1 >> 16)
    s0 = (s0 & 0xffff) * 0x4650 + (s0 >> 16)
    out = ROL16(s1) + s0                 (mod 2**32)
    return out ^ bytecode_xor_key

`s0`/`s1` start at the record's key pair (`key1`, `key2`), and
`bytecode_xor_key` is the header field of the same name. The mask byte for a
slot is `out.to_bytes(4, 'little')[slot]` - the loader reads the u32 array with
a byte cursor, so slot `i` lands on byte `i` of the stream.

0x95 is reserved: `sub_18009E8B0` zeroes `mask[slot]` and returns the stored byte
whenever either the stored byte or the xored result is 0x95, so those slots
decode to the stored byte and not to `stored ^ mask`.

Usage:
    python tools/ic72_opcode_mask.py binancepay_asli.php
    python tools/ic72_opcode_mask.py sample.php --json
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from tools.ic72_op_walk import ARG_COUNT, walk_record  # noqa: E402
from tools.ic72_record_walk import resync  # noqa: E402

SENTINEL = 0x95
STEP_K1 = 0x7689
STEP_K0 = 0x4650


def _step(value: int, multiplier: int) -> int:
    return ((value & 0xFFFF) * multiplier + ((value >> 16) & 0xFFFF)) & 0xFFFFFFFF


def mask_stream(key1: int, key2: int, xor_key: int, count: int) -> bytes:
    s0 = key1 & 0xFFFFFFFF
    s1 = key2 & 0xFFFFFFFF
    key = xor_key & 0xFFFFFFFF
    out = bytearray()
    while len(out) < count:
        s1 = _step(s1, STEP_K1)
        s0 = _step(s0, STEP_K0)
        word = (((s1 << 16) | (s1 >> 16)) + s0) & 0xFFFFFFFF
        out += (word ^ key).to_bytes(4, "little")
    return bytes(out[:count])


def decode_slot(stored: int, mask_byte: int, version: int = 5) -> tuple[int, int]:
    """Return `(opcode, mask_byte_after)` for one slot, loader rules included."""
    if version >= 3 and stored == SENTINEL:
        mask_byte = 0
    opcode = stored ^ mask_byte
    if version >= 3 and opcode == SENTINEL:
        return stored, 0
    return opcode, mask_byte


def record_masks(body: bytes, xor_key: int, version: int = 5) -> dict[str, bytes]:
    masks: dict[str, bytes] = {}
    for index, record in enumerate(resync(body, 4)):
        if index == 0:
            continue
        payload = body[record.payload_offset : record.payload_offset + record.payload_size]
        ops = walk_record(payload, ARG_COUNT[index])["ops"]
        masks[record.name] = mask_stream(record.key1, record.key2, xor_key, ops)
    return masks


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path", type=Path, help="body blob or encoded PHP file")
    parser.add_argument("--body", action="store_true", help="path is the body blob")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    if args.body:
        body = args.path.read_bytes()
        xor_key = 0x00364730
    else:
        from tools.ic72_static_container import decode_payload_body, decode_file, load_payload

        payload = load_payload(args.path, 0)
        header, _ = decode_file(args.path, payload_index=0)
        version = int(str(header["initial_header"]["version"]), 0)
        xor_key = int(str(header["initial_header"]["bytecode_xor_key"]), 0)
        body = decode_payload_body(payload, int(header["body_offset"]), version).decompressed

    masks = record_masks(body, xor_key)
    if args.json:
        print(json.dumps({k: v.hex() for k, v in masks.items()}, indent=2))
    else:
        print(f"bytecode_xor_key={xor_key:#010x}")
        for name, mask in masks.items():
            print(f"{name or '<file level>':<20} {len(mask):4d}  {mask.hex()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
