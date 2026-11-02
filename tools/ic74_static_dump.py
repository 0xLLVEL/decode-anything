#!/usr/bin/env python3
"""Static decode of a PHP 7.4 ionCube artifact - no PHP runtime, no dumper DLL.

Two layers come apart without the loader:

  container   header (MD4 + transition adler + frame adlers) and the raw-DEFLATE
              body, exactly the gates the loader runs first
  body        encoder 15.x lays every op_array out as a length-prefixed name
              followed by a fixed field block; the six counters below are read
              straight from it

Field block, offsets measured from the first byte after the name's NUL:

    +0x28  opcode count      +0x54  first source line
    +0x30  local variables   +0x58  last source line
    +0x34  temp variables    +0x60  literal count

Against `loader/refs/ic74dump-opcodes/contacts.opcodes.json` (113 op_arrays from
the 7.4 runtime dumper) all six agree for every named op_array, which is what
makes them a fingerprint rather than a guess: `--truth` checks exactly that.

The opcode stream that starts at +0x90 is masked with a per-record key stream
that is generated, not stored, so the scan reports structure only.
:func:`walk_ops` is the confirmed grammar with the mask supplied by the caller;
for ``getTotalSendGroups`` it reproduces all twelve runtime opcodes.
See docs/ioncube-74-static.md.

    python tools/ic74_static_dump.py sample.php
    python tools/ic74_static_dump.py sample.php --json --truth dump.json
"""

from __future__ import annotations

import argparse
import json
import struct
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from engines.ioncube.header import (  # noqa: E402
    decode_custom_base64,
    decode_file,
    decode_payload_body,
    get_hrc_payload_slice,
)

CLASS_HEADER = b"\x02\x00\x02\x00\x02"
IDENTIFIER = frozenset(b"_\\abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789")

FIELDS = {
    "opcodes": 0x28,
    "variables": 0x30,
    "temps": 0x34,
    "line_start": 0x54,
    "line_end": 0x58,
    "literals": 0x60,
}


def decode_body(path: Path, payload_index: int = 0) -> tuple[dict, bytes]:
    source = path.read_bytes()
    _, raw_payload = get_hrc_payload_slice(source, index=payload_index)
    payload = decode_custom_base64(raw_payload)
    header, _ = decode_file(path, payload_index=payload_index)
    body = decode_payload_body(
        payload,
        int(header["body_offset"]),
        int(header["initial_header"]["version"]),
    )
    return header, body.decompressed


def _u32(buf: bytes, offset: int) -> int:
    if offset < 0 or offset + 4 > len(buf):
        return -1
    return struct.unpack_from("<I", buf, offset)[0]


def _s32(buf: bytes, offset: int) -> int:
    if offset < 0 or offset + 4 > len(buf):
        return -1
    return struct.unpack_from("<i", buf, offset)[0]


def _name_at(buf: bytes, offset: int) -> tuple[str, int] | None:
    """Read the op_array name at *offset*, returning (name, first field offset).

    Every op_array record is its own name as a NUL-terminated identifier, then
    the pair ``2, 0x42020001`` that no other 8-byte window in the body carries at
    this distance from a terminator.
    """

    end = buf.find(b"\x00", offset, offset + 96)
    if end <= offset:
        return None
    raw = buf[offset:end]
    if not raw or any(byte not in IDENTIFIER for byte in raw):
        return None
    fields = end + 1
    if _u32(buf, fields + 4) != 2 or not _is_record_mark(_u32(buf, fields + 8)):
        return None
    return raw.decode("ascii"), fields


def _is_record_mark(word: int) -> bool:
    """``0x42020001`` and friends: kind byte 0x02, low byte 1 (or 4 for ref)."""

    return (word >> 16) & 0xFF == 0x02 and (word & 0xFF) in (1, 4)


def _class_name_at(buf: bytes, offset: int) -> tuple[str, int] | None:
    if not buf.startswith(CLASS_HEADER, offset):
        return None
    length = _u32(buf, offset + len(CLASS_HEADER))
    start = offset + len(CLASS_HEADER) + 4
    end = start + length
    if length < 1 or end >= len(buf) or buf[end] != 0:
        return None
    try:
        name = buf[start:end].decode("ascii")
    except UnicodeDecodeError:
        return None
    if not all(char.isalnum() or char in "_\\" for char in name):
        return None
    return name, end + 1


def scan_body(body: bytes) -> dict:
    """Collect class and op_array records the encoder laid down in order."""

    entries: list[dict] = []
    classes: list[dict] = []
    cursor = 0
    while cursor < len(body) - 96:
        found = _class_name_at(body, cursor)
        if found is not None:
            name, end = found
            classes.append({"offset": cursor, "name": name})
            cursor = end
            continue
        found = _name_at(body, cursor)
        if found is not None:
            name, end = found
            fields = {key: _u32(body, end + off) for key, off in FIELDS.items()}
            plausible = (
                0 < fields["opcodes"] <= 0x10000
                and 0 <= fields["variables"] < 0x1000
                and 0 <= fields["temps"] < 0x10000
                and 0 <= fields["literals"] < 0x10000
                and 0 < fields["line_end"] < 0x1000000
                and fields["line_start"] <= fields["line_end"]
            )
            if plausible:
                entries.append(
                    {"offset": cursor, "name": name, "end": end, **fields}
                )
                cursor = end
                continue
        cursor += 1

    owner = None
    cursor = 0
    for entry in entries:
        while cursor < len(classes) and classes[cursor]["offset"] < entry["offset"]:
            owner = classes[cursor]
            cursor += 1
        if owner is not None and entry["name"] != owner["name"]:
            entry["class"] = owner["name"]
        elif owner is not None:
            entry["kind"] = "class"
    return {"entries": entries, "classes": classes}


def walk_ops(body: bytes, start: int, count: int, mask: bytes) -> tuple[list[dict], int]:
    """Walk the 7.4 word block the way ``sub_180097AA0`` does.

    Each instruction is one opcode word plus the 7.4-only extended word. Both
    cache bits set (`0x1800`) adds an explicit slot word; the line is the high
    half unless it is ``0xFFFF``, which also adds a word. ``mask`` is the
    per-op mask stream, one byte per instruction.
    """

    ops: list[dict] = []
    cursor = start
    for index in range(count):
        word = _u32(body, cursor)
        cursor += 8
        slot = None
        cache = word & 0x1800
        if cache == 0x0800:
            slot = 1
        elif cache == 0x1000:
            slot = 60
        elif cache == 0x1800:
            slot = _s32(body, cursor)
            cursor += 4
        line = word >> 16
        if line == 0xFFFF:
            line = _u32(body, cursor)
            cursor += 4
        ops.append(
            {
                "opcode": (word & 0xFF) ^ mask[index],
                "line": line,
                "slot": slot,
                "arg1": bool(word & 0x100),
                "arg2": bool(word & 0x200),
                "arg3": bool(word & 0x400),
            }
        )
    return ops, cursor


def compare_with_truth(report: dict, truth_path: Path) -> dict:
    truth = json.loads(truth_path.read_text(encoding="utf-8"))
    expected: dict[str, dict] = {}
    for entry in (truth.get("op_arrays") or {}).values():
        name = entry.get("function_name")
        name = name.get("value") if isinstance(name, dict) else name
        if not name:
            continue
        expected[name] = {
            "opcodes": len(entry.get("opcodes") or []),
            "variables": entry.get("last_var") or 0,
            "temps": entry.get("T") or 0,
            "literals": len(entry.get("literals") or []),
            "line_start": entry.get("line_start") or 0,
            "line_end": entry.get("line_end") or 0,
        }

    seen = {entry["name"]: entry for entry in report["entries"]}
    matched, mismatched, missing = [], [], []
    for name, want in expected.items():
        got = seen.get(name)
        if got is None:
            missing.append(name)
            continue
        diff = {key: (got[key], want[key]) for key in want if got[key] != want[key]}
        if diff:
            mismatched.append({"name": name, "diff": diff})
        else:
            matched.append(name)
    return {
        "truth_op_arrays": len(expected),
        "matched": len(matched),
        "mismatched": mismatched,
        "missing": missing,
        "extra": sorted(set(seen) - set(expected)),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path", type=Path, help="encoded PHP file")
    parser.add_argument("--json", action="store_true", help="print the full report")
    parser.add_argument("--body-out", type=Path, help="write the decoded body")
    parser.add_argument("--truth", type=Path, help="compare against a runtime dump")
    parser.add_argument("--payload-index", type=int, default=0)
    args = parser.parse_args(argv)

    header, body = decode_body(args.path, args.payload_index)
    if args.body_out:
        args.body_out.write_bytes(body)

    scanned = scan_body(body)
    report = {
        "format": "ic74-static-v1",
        "source": str(args.path),
        "decoded_version": header["decoded_version"],
        "encoder": (
            f"{header['header_trailer']['encoder_major']}."
            f"{header['header_trailer']['encoder_minor']}."
            f"{header['header_trailer']['encoder_revision']}"
        ),
        "php_version_code": header["header_trailer"]["php_version_code"],
        "container": {
            "md4_matches": header["md4_matches"],
            "transition_checksum_matches": header["transition_checksum_matches"],
            "body_offset": header["body_offset"],
            "body_size": len(body),
        },
        "entries": scanned["entries"],
        "classes": [{"name": item["name"]} for item in scanned["classes"]],
        "summary": {
            "entry_count": len(scanned["entries"]),
            "named_op_arrays": len({entry["name"] for entry in scanned["entries"]}),
            "class_count": len({entry.get("class") for entry in scanned["entries"] if entry.get("class")}),
            "opcode_total": sum(entry["opcodes"] for entry in scanned["entries"]),
            "literal_total": sum(entry["literals"] for entry in scanned["entries"]),
        },
    }
    if args.truth:
        report["truth"] = compare_with_truth(report, args.truth)

    if args.json:
        print(json.dumps(report, indent=2))
        return 0

    print(f"source                {report['source']}")
    print(f"encoder               {report['encoder']}")
    print(f"php_version_code      {report['php_version_code']}")
    print(f"body_size             {report['container']['body_size']}")
    for key, value in report["summary"].items():
        print(f"{key:<22}{value}")
    print()
    current = None
    for entry in report["entries"]:
        owner = entry.get("class")
        if owner and owner != current:
            current = owner
            print(f"class {owner}")
        label = entry["name"]
        if owner:
            label = f"  {label}"
        print(
            f"  {label:<34} ops={entry['opcodes']:<5} vars={entry['variables']:<3}"
            f" tmp={entry['temps']:<4} lits={entry['literals']:<4}"
            f" lines={entry['line_start']}..{entry['line_end']}"
        )
    if args.truth:
        truth = report["truth"]
        print()
        print(f"truth op_arrays       {truth['truth_op_arrays']}")
        print(f"matched               {truth['matched']}")
        print(f"mismatched            {len(truth['mismatched'])}")
        print(f"missing               {len(truth['missing'])}")
        print(f"extra                 {len(truth['extra'])}")
        for item in truth["mismatched"][:5]:
            print(f"  {item['name']}: {item['diff']}")
        for name in truth["missing"][:5]:
            print(f"  missing {name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
