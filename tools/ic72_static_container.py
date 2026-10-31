#!/usr/bin/env python3
"""Static container/header/body dump for ionCube 7.x payloads.

Runs the loader's own gates without the loader:

  adler-17 over payload[4:transition] == transition dword
  MD4(header plaintext) == ROL3(last 16 header ciphertext bytes)
  adler-32(init 0) over every ciphertext frame == embedded 0xA0 frame
  raw DEFLATE reaches BFINAL with no unconsumed input

What comes out is the program blob, the same bytes the loader would hand to
its sv5 record walker. The record layer itself is still open.

Usage:
    python tools/ic72_static_container.py sample.php
    python tools/ic72_static_container.py sample.php --body-out body72.bin
    python tools/ic72_static_container.py sample.php --json
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from engines.ioncube.header import (  # noqa: E402
    decode_custom_base64,
    decode_file,
    decode_payload_body,
    get_hrc_payload_slice,
)


def load_payload(path: Path, payload_index: int) -> bytes:
    source = path.read_bytes()
    _, raw_payload = get_hrc_payload_slice(source, index=payload_index)
    return decode_custom_base64(raw_payload)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path", type=Path, help="encoded PHP file")
    parser.add_argument("--body-out", type=Path, help="write the program blob")
    parser.add_argument("--payload-index", type=int, default=0)
    parser.add_argument("--json", action="store_true", help="print the full report")
    args = parser.parse_args()

    payload = load_payload(args.path, args.payload_index)
    header_report, _ = decode_file(args.path, payload_index=args.payload_index)

    body = decode_payload_body(
        payload,
        int(header_report["body_offset"]),
        int(header_report["initial_header"]["version"]),
    )

    summary = {
        "source": header_report["source"],
        "decoded_version": header_report["decoded_version"],
        "md4_matches": header_report["md4_matches"],
        "transition_checksum_matches": header_report["transition_checksum_matches"],
        "all_frame_checksums_match": body.report["all_checksums_match"],
        "inflate_eof": body.report["inflate_eof"],
        "header_size": header_report["decrypted_header_size"],
        "body_offset": header_report["body_offset"],
        "body_size": body.report["decompressed_size"],
        "bytecode_xor_key": header_report["initial_header"]["bytecode_xor_key"],
        "owner_key": header_report["initial_header"]["owner_key"],
        "php_version_code": header_report["header_trailer"]["php_version_code"],
        "php_flags": header_report["header_trailer"]["php_flags"],
        "encoder": (
            f"{header_report['header_trailer']['encoder_major']}."
            f"{header_report['header_trailer']['encoder_minor']}."
            f"{header_report['header_trailer']['encoder_revision']}"
        ),
        "primary_seed": body.report["primary_seed"],
        "secondary_seed": body.report["secondary_seed"],
        "frames": body.report["event_counts"],
    }

    if args.body_out:
        args.body_out.write_bytes(body.decompressed)
        summary["body_out"] = str(args.body_out)

    if args.json:
        print(
            json.dumps(
                {"summary": summary, "header": header_report, "body": body.report},
                indent=2,
            )
        )
    else:
        for key, value in summary.items():
            print(f"{key:<28}{value}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
