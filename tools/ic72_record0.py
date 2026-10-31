"""Decode the ionCube 7.x file-level op_array record without the loader.

The four function records in an sv5 body are stored as plain record images: the
opcode bytes are masked but every other field is readable. The file-level record
is the one exception - its 616-byte payload is encrypted with the record cipher
(`sub_180001E10`), keyed by four dwords the loader derives from the program
context (`sub_180003570`).

The cipher is a solved problem: `engines.ioncube.body72.decrypt_record`
reproduces the loader's plaintext byte for byte. What is still open is where
those four dwords come from. Feed them in and this decodes the record; the
loader's own runtime dump can then confirm it.

Usage:
    python tools/ic72_record0.py sample.php --words b8,5,0,29806ff7
    python tools/ic72_record0.py sample.php --words b8,5,0,29806ff7 \
        --truth scratch/rt/binancepay_asli.opcodes.json
    python tools/ic72_record0.py sample.php --words ... --dump scratch/rec0.bin
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from engines.ioncube.body72 import decrypt_record, record_key  # noqa: E402
from tools.ic72_op_walk import OPERAND_TYPES, walk_record  # noqa: E402
from tools.ic72_opcode_mask import decode_slot, mask_stream  # noqa: E402
from tools.ic72_record_walk import resync  # noqa: E402
from tools.ic72_static_container import (  # noqa: E402
    decode_file,
    decode_payload_body,
    load_payload,
)

FILE_LEVEL_HEAD = 0x78


def parse_words(text: str) -> list[int]:
    words = [int(part, 0) for part in text.replace(" ", "").split(",") if part]
    if len(words) != 4:
        raise SystemExit("--words needs four comma separated 32-bit values")
    return words


def truth_opcodes(path: Path) -> list[int] | None:
    document = json.loads(path.read_text(encoding="utf-8"))
    for entry in document["op_arrays"].values():
        name = entry.get("function_name")
        name = name.get("value") if isinstance(name, dict) else name
        if name is None:
            return [op["opcode"] for op in entry["opcodes"]]
    return None


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path", type=Path, help="encoded PHP file")
    parser.add_argument("--words", required=True, help="four dwords, 0xb8,5,0,0x29806ff7")
    parser.add_argument("--dump", type=Path, help="write the decoded record image here")
    parser.add_argument("--truth", type=Path, help="runtime opcode dump to compare against")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    payload = load_payload(args.path, 0)
    header, _ = decode_file(args.path, payload_index=0)
    version = int(str(header["initial_header"]["version"]), 0)
    xor_key = int(str(header["initial_header"]["bytecode_xor_key"]), 0)
    body = decode_payload_body(payload, int(header["body_offset"]), version).decompressed

    records = resync(body, 4)
    record = records[0]
    ciphertext = body[record.payload_offset : record.payload_offset + record.payload_size]

    key = record_key(parse_words(args.words))
    image = decrypt_record(ciphertext, key)
    if args.dump:
        args.dump.write_bytes(image)

    walked = walk_record(image, 0, head=FILE_LEVEL_HEAD, fixed_aux=True)
    masks = mask_stream(record.key1, record.key2, xor_key, walked["ops"])
    opcodes = []
    for entry in walked["entries"]:
        slot = entry["index"]
        opcode, _ = decode_slot(entry["opcode"], masks[slot] if slot < len(masks) else 0)
        opcodes.append(opcode)

    expected = truth_opcodes(args.truth) if args.truth else None
    matched = None if expected is None else sum(1 for a, b in zip(opcodes, expected) if a == b)

    if args.json:
        print(
            json.dumps(
                {
                    "record": record.name or "<file-level>",
                    "key": key.hex(),
                    "ops": walked["ops"],
                    "cells": walked["cells"],
                    "aux_consumed": walked["aux_consumed"],
                    "opcodes": opcodes,
                    "expected": expected,
                    "matched": matched,
                },
                indent=2,
            )
        )
        return 0 if matched in (None, walked["ops"]) else 1

    print(f"key            {key.hex(' ')}")
    print(f"payload        {record.payload_size} bytes at {record.payload_offset:#x}")
    print(f"image head     {image[:8].hex(' ')}")
    print(f"ops/cells      {walked['ops']}/{walked['cells']}  aux {walked['aux_consumed']}/{15 * walked['ops']}")
    for entry, opcode in zip(walked["entries"], opcodes):
        cells = " ".join(
            "%s(%d)" % (kind, node) for _, kind, node in entry["operands"]
        )
        print(
            "  %03d  stored=0x%02X op=%3d class=%-10s line=%-4d %s"
            % (entry["index"], entry["opcode"], opcode, entry["class"], entry["line"], cells)
        )
    if expected is None:
        print("\nno --truth file: opcodes decoded, correctness unchecked")
    else:
        print(f"\nopcodes match runtime dump: {matched}/{len(expected)}")
    return 0 if matched in (None, walked["ops"]) else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
