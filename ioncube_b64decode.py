#!/usr/bin/env python3
"""IonCube custom Base64 decoder CLI and library.

IonCube PHP 8.x loaders use a modified Base64 alphabet where digits 0-9
are placed at the beginning:
    ioncube:  0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz+/
    standard: ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/

Reference: https://www.amariei.org/ioncube-php8-static-decode.html
"""

import argparse
import re
import struct
import sys
from pathlib import Path

ALPHA = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz+/"
LUT = {c: i for i, c in enumerate(ALPHA)}
VERSION_XOR = 0x2853CEF2
HRC_VERSIONS = {
    0x4FF571B7,
    0x17EFE671,
    0x2A4496DD,
    0x3CCC22E1,
}


def ioncube_b64decode(s: str) -> bytes:
    """Decode a string encoded in IonCube's custom Base64 alphabet."""
    # Strip whitespace / newlines
    compact = "".join(s.split())
    if not compact:
        return b""

    # Determine padding count
    pad_count = compact.count("=")
    clean = compact.rstrip("=")
    rem = len(clean) % 4
    if rem:
        clean += "0" * (4 - rem)

    out = bytearray()
    for i in range(0, len(clean), 4):
        a = LUT.get(clean[i], 0)
        b = LUT.get(clean[i + 1], 0)
        c = LUT.get(clean[i + 2], 0)
        d = LUT.get(clean[i + 3], 0)
        n = (a << 18) | (b << 12) | (c << 6) | d
        out += bytes([(n >> 16) & 0xFF, (n >> 8) & 0xFF, n & 0xFF])

    if pad_count in (1, 2):
        return bytes(out[:-pad_count])
    elif pad_count >= 3:
        # IonCube bundle boundary sometimes uses ===
        # Modulo check determines real byte count
        actual_len = (len(compact.rstrip("=")) * 6) // 8
        return bytes(out[:actual_len])
    elif rem:
        actual_len = (len(compact.rstrip("=")) * 6) // 8
        return bytes(out[:actual_len])

    return bytes(out)


def decode_file_payloads(path: Path) -> list[dict]:
    """Inspect an ionCube PHP file, detect bundles, and decode HR+c payloads."""
    content = path.read_bytes()

    # Check for multi-target bundle header
    bundle_info = None
    first_line = content[:120].split(b"\n", 1)[0]
    if b"//ICB0" in first_line:
        m = re.search(rb"//ICB0\s+([^?]+)", first_line)
        if m:
            bundle_info = m.group(1).decode("latin1", errors="replace").strip()

    # Locate all HR+c markers
    markers = [m.start() for m in re.finditer(b"HR\\+c", content)]
    if not markers:
        raise ValueError("No 'HR+c' marker found in file.")

    results = []
    for idx, start in enumerate(markers):
        end = markers[idx + 1] if idx + 1 < len(markers) else len(content)
        raw_b64 = content[start:end].decode("latin1", errors="ignore")
        decoded = ioncube_b64decode(raw_b64)

        info = {
            "index": idx,
            "marker_offset": start,
            "raw_length": end - start,
            "decoded_bytes": decoded,
            "decoded_length": len(decoded),
        }

        # Check version word if available
        if len(decoded) >= 4:
            raw_v = struct.unpack_from("<I", decoded, 0)[0]
            dec_v = raw_v ^ VERSION_XOR
            info["raw_version"] = f"0x{raw_v:08X}"
            info["decoded_version"] = f"0x{dec_v:08X}"
            info["is_valid_hrc_version"] = dec_v in HRC_VERSIONS

        results.append(info)

    return results, bundle_info


def format_hex_dump(data: bytes, max_bytes: int = 128) -> str:
    """Format bytes as a hex dump."""
    lines = []
    chunk = data[:max_bytes]
    for i in range(0, len(chunk), 16):
        row = chunk[i : i + 16]
        hex_part = " ".join(f"{b:02x}" for b in row)
        ascii_part = "".join(chr(b) if 32 <= b < 127 else "." for b in row)
        lines.append(f"{i:04x}  {hex_part:<48}  |{ascii_part}|")
    if len(data) > max_bytes:
        lines.append(f"... ({len(data) - max_bytes} more bytes)")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Decode IonCube custom Base64 string or file payload."
    )
    parser.add_argument(
        "input",
        nargs="?",
        help="Base64 string or path to an encoded PHP file",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        help="Write decoded binary output to file",
    )
    parser.add_argument(
        "-p",
        "--payload-index",
        type=int,
        default=0,
        help="Payload index to extract if file contains multiple bundles (default: 0)",
    )

    args = parser.parse_args()

    if not args.input:
        parser.print_help()
        print("\nExamples:")
        print("  py .\\ioncube_b64decode.py ewfw")
        print("  py .\\ioncube_b64decode.py SpondonItSchoolServiceProvider.php")
        print("  py .\\ioncube_b64decode.py SpondonItSchoolServiceProvider.php -o payload.bin")
        return 0

    target = Path(args.input)
    if target.is_file():
        print(f"Reading file: {target}")
        try:
            payloads, bundle_info = decode_file_payloads(target)
        except Exception as e:
            print(f"Error parsing file: {e}", file=sys.stderr)
            return 1

        if bundle_info:
            print(f"Detected multi-target bundle (//ICB0): {bundle_info}")
        print(f"Found {len(payloads)} HR+c payload(s) in file:")

        for p in payloads:
            idx = p["index"]
            valid = "OK" if p.get("is_valid_hrc_version") else "INVALID"
            print(
                f"  [{idx}] Offset: {p['marker_offset']} | "
                f"Base64: {p['raw_length']} bytes -> Decoded: {p['decoded_length']} bytes | "
                f"HRC Version: {p.get('decoded_version', 'N/A')} ({valid})"
            )

        selected = (
            payloads[args.payload_index]
            if args.payload_index < len(payloads)
            else payloads[0]
        )
        print(f"\nHex preview for payload [{selected['index']}]:")
        print(format_hex_dump(selected["decoded_bytes"]))

        if args.output:
            args.output.write_bytes(selected["decoded_bytes"])
            print(f"\nWrote {len(selected['decoded_bytes'])} bytes to {args.output}")
        return 0
    else:
        # Treat input as a raw base64 string
        decoded = ioncube_b64decode(args.input)
        print(f"Decoded {len(decoded)} byte(s) from custom Base64 string:")
        print(format_hex_dump(decoded))
        if args.output:
            args.output.write_bytes(decoded)
            print(f"Wrote to {args.output}")
        return 0


if __name__ == "__main__":
    sys.exit(main())