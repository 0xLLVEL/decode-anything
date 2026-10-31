"""Decrypt an arbitrary span of an ionCube 7.x program blob.

Key material comes from either
  * ``--material`` (raw bytes, hex) fed through ``derive_key`` (0x0D + SHA1), or
  * ``--raw-key`` (bytes used directly with no SHA-1), or
  * ``--sample``, which regenerates the header plaintext and tries every ASCII
    run inside it plus the whole header as key material.

The cipher is ``sub_180001E10``; see ``engines/ioncube/body72.py`` for the map.
"""

from __future__ import annotations

import argparse
import re
import struct
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from engines.ioncube.body72 import (  # noqa: E402
    decrypt_buffer,
    derive_key,
    keystream,
    seed0,
    seed1,
    Type6Rng,
)
from engines.ioncube.header import (  # noqa: E402
    MT4IC,
    VERSION_XOR,
    decode_custom_base64,
    decode_meta_header,
    get_hrc_payload_slice,
    read_u32,
    rol8,
    unchunk_header,
)


def header_plaintext(sample: Path) -> bytes:
    _marker, raw = get_hrc_payload_slice(sample.read_bytes())
    payload = decode_custom_base64(raw)
    if read_u32(payload, 0) ^ VERSION_XOR not in (0x4FF571B7,):
        raise SystemExit("not a recognised 7.x payload")
    meta = decode_meta_header(payload[4:28])
    header, _consumed, _chunks = unchunk_header(payload[28:], meta.header_size)
    checksum = bytes(rol8(v) for v in header[-16:])
    prng = MT4IC(meta.seed)
    return bytes(
        header[i] ^ checksum[i & 0x0F] ^ (prng.get() & 0xFF)
        for i in range(meta.header_size - 16)
    )


def runs(buf: bytes, minimum: int) -> list[tuple[int, str]]:
    return [
        (m.start(), m.group().decode())
        for m in re.finditer(rb"[ -~]{%d,}" % minimum, buf)
    ]


def metrics(buf: bytes) -> str:
    if not buf:
        return "empty"
    printable = sum(1 for b in buf if 32 <= b < 127)
    words = struct.unpack_from("<%dI" % (len(buf) // 4), buf, 0)
    small = sum(1 for w in words if w < 0x1000)
    return (
        f"zero={buf.count(0):4d} print={printable:4d} "
        f"({printable * 100.0 / len(buf):5.1f}%) small_dw={small}/{len(words)}"
    )


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("body", type=Path, help="decoded program blob")
    ap.add_argument("--offset", type=lambda s: int(s, 0), default=0x4C)
    ap.add_argument("--count", type=lambda s: int(s, 0), default=616)
    ap.add_argument("--shift", type=int, default=8, help="BYTE1 of the dword by default")
    ap.add_argument("--material", help="key material as hex, hashed with SHA-1")
    ap.add_argument("--raw-key", help="cipher key as hex, used verbatim")
    ap.add_argument("--sample", type=Path, help="encoded file, for header-derived candidates")
    ap.add_argument("--dump", type=Path, help="write the decrypted span here")
    args = ap.parse_args(argv)

    data = args.body.read_bytes()
    ciphertext = data[args.offset:args.offset + args.count]
    print(f"ciphertext {len(ciphertext)} B @ {args.offset:#x}: {ciphertext[:24].hex()}")

    candidates: list[tuple[str, bytes]] = []
    if args.raw_key:
        candidates.append(("raw-key", bytes.fromhex(args.raw_key)))
    if args.material:
        candidates.append(("material", derive_key(bytes.fromhex(args.material))))
    if args.sample:
        header = header_plaintext(args.sample)
        print(f"header plaintext {len(header)} B: {header.hex()}")
        for off, text in runs(header, 3):
            candidates.append((f"hdr+{off:#x}", derive_key(text.encode())))
        candidates.append(("hdr-all", derive_key(header)))
        candidates.append(("hdr-head", header))
    if not candidates:
        raise SystemExit("no key material: pass --material, --raw-key or --sample")

    best: list[tuple[float, str, bytes]] = []
    for name, key in candidates:
        print(f"\n{name:16s} key={key.hex()} seed0={seed0(key):#010x} seed1={seed1(key):#010x}")
        for shift in (args.shift,):
            plaintext = decrypt_buffer(ciphertext, key, shift)
            printable = sum(1 for b in plaintext if 32 <= b < 127) / len(plaintext)
            best.append((printable, name, plaintext))
            print(f"  shift {shift:2d} {metrics(plaintext)}  {plaintext[:32].hex()}")
            for off, text in runs(plaintext, 8)[:6]:
                print(f"    +{off:#05x} {text[:60]!r}")

    best.sort(key=lambda item: item[0], reverse=True)
    if args.dump:
        args.dump.write_bytes(best[0][2])
        print(f"\nwrote {args.dump} from candidate {best[0][1]}")
    print(f"\nstream self-check: {keystream(b'x', 4).hex()} rng(1,1)={Type6Rng(1, 1).next():#010x}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
