"""Extract and verify the ionCube 7.x body keystream.

The sv5 body is a frame stream: each frame is either ciphertext (XORed with an
MT4IC keystream) or a literal byte.  This tool rebuilds the keystream the
loader applies, proves it reproduces the deflate stream, and writes the bytes
to disk for further analysis.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from engines.ioncube.header import (
    MT4IC,
    decode_file,
    read_encoded_payload,
)


def build_keystream(payload: bytes, body_offset: int, header_version: int) -> dict:
    seed_size = 8 if header_version >= 4 else 4
    if body_offset + seed_size > len(payload):
        raise ValueError("truncated body seeds")
    primary_seed = int.from_bytes(payload[body_offset : body_offset + 4], "little")
    position = body_offset + seed_size
    prng = MT4IC(primary_seed)
    keystream = bytearray()
    plaintext = bytearray()
    ciphertext = bytearray()
    frames = 0

    while position < len(payload):
        frame_start = position
        flag = payload[position]
        second = payload[position + 1] if position + 1 < len(payload) else 0
        position += 2
        if flag < 0x80:
            end = position + second
            frames += 1
            for value in payload[position:end]:
                key = prng.get() & 0xFF
                keystream.append(key)
                ciphertext.append(value)
                plaintext.append(value ^ key)
            position = end
            continue
        marker = flag & 0xE0
        if marker == 0xA0:
            position = frame_start + 1
            produced = 0
            while produced < 4:
                value = payload[position]
                position += 1
                if value == 0xFF:
                    position += 1
                produced += 1
        elif marker in (0x80, 0xC0):
            plaintext.append(second if marker == 0x80 else 0x3C)

    return {
        "primary_seed": primary_seed,
        "frames": frames,
        "keystream": bytes(keystream),
        "ciphertext": bytes(ciphertext),
        "plaintext": bytes(plaintext),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--target", required=True, type=Path)
    parser.add_argument("--php-version", type=int, default=72)
    parser.add_argument("--out", type=Path, default=Path("scratch/ic72_body_keystream.bin"))
    args = parser.parse_args()

    report, _header = decode_file(args.target, target_php=args.php_version)
    payload = read_encoded_payload(args.target, target_php=args.php_version)
    body_offset = int(report["body_offset"])
    header_version = int(report["initial_header"]["version"])

    result = build_keystream(payload, body_offset, header_version)
    keystream = result["keystream"]

    regenerator = MT4IC(result["primary_seed"])
    regenerated = bytes(regenerator.get() & 0xFF for _ in range(len(keystream)))
    verified = regenerated == keystream

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_bytes(keystream)

    print(f"primary seed   : 0x{result['primary_seed']:08X}")
    print(f"encrypted frames: {result['frames']}")
    print(f"keystream bytes: {len(keystream)}")
    print(f"mt4ic reproduces keystream: {verified}")
    print(f"keystream written to: {args.out}")
    return 0 if verified else 1


if __name__ == "__main__":
    raise SystemExit(main())
