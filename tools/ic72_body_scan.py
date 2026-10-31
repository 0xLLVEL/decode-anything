#!/usr/bin/env python3
"""Inventory the plaintext parts of an ionCube 7.x program blob.

The sv5 record layer is not decoded yet, but the body is not opaque: identifier
names are stored as length-prefixed strings and literal pools use ionCube's
compact zval encoding (``[`` arrays, ``s`` strings, ``i`` ints, ...), the same
grammar the 8.x literal reader already implements.

This tool walks the blob without assuming record boundaries and reports what is
readable, so the record walker can be built against real offsets instead of
guesses:

    python tools/ic72_body_scan.py body72.bin
    python tools/ic72_body_scan.py body72.bin --json

Nothing here claims a record layout. It reports offsets, decoded literal
values and printable identifier runs.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from engines.ioncube.body import ParseError, _EncodedZvalReader  # noqa: E402

ZVALUE_STARTS = b"[sidtfn"
IDENTIFIER_MIN = 4


def parse_at(data: bytes, offset: int, limit: int = 1 << 16) -> tuple[int, Any] | None:
    """Decode one encoded zval starting at ``offset``; return (end, value)."""

    if data[offset] not in ZVALUE_STARTS:
        return None
    window = data[offset : offset + limit].decode("latin1")
    reader = _EncodedZvalReader(window)
    try:
        value = reader.parse()
    except (ParseError, ValueError):
        return None
    if reader.offset < 10:
        return None
    return offset + reader.offset, value


def scan_literals(data: bytes) -> list[dict[str, Any]]:
    found: list[dict[str, Any]] = []
    offset = 0
    while offset < len(data):
        parsed = parse_at(data, offset)
        if parsed is None:
            offset += 1
            continue
        end, value = parsed
        entry: dict[str, Any] = {
            "offset": offset,
            "size": end - offset,
            "kind": type(value).__name__,
        }
        if isinstance(value, (dict, list)):
            entry["entries"] = len(value)
            entry["preview"] = _preview(value, 3)
        else:
            entry["preview"] = value if isinstance(value, (int, float, bool)) else str(value)[:120]
        found.append(entry)
        offset = end
    return found


def _preview(value: Any, depth: int) -> Any:
    if depth <= 0:
        return "…"
    if isinstance(value, dict):
        return {
            str(key): _preview(item, depth - 1)
            for key, item in list(value.items())[:6]
        }
    if isinstance(value, list):
        return [_preview(item, depth - 1) for item in value[:6]]
    if isinstance(value, str):
        return value[:120]
    return value


def scan_length_prefixed(data: bytes, max_length: int = 200) -> list[dict[str, Any]]:
    """Find u32-length-prefixed, NUL-terminated name records (sub_18000B8A0)."""

    found: list[dict[str, Any]] = []
    offset = 0
    while offset + 4 <= len(data):
        length = int.from_bytes(data[offset : offset + 4], "little")
        start = offset + 4
        if 3 <= length <= max_length and start + length < len(data):
            raw = data[start : start + length]
            if raw[0:1].isalpha() and all(
                0x20 <= byte < 0x7F for byte in raw
            ):
                found.append(
                    {
                        "offset": offset,
                        "text": raw.decode("latin1"),
                        "terminator": data[start + length],
                    }
                )
                offset = start + length + 1
                continue
        offset += 1
    return found


def scan_identifiers(data: bytes) -> list[dict[str, Any]]:
    found: list[dict[str, Any]] = []
    run_start = None
    for index, byte in enumerate(data + b"\0"):
        printable = (
            0x30 <= byte <= 0x39
            or 0x41 <= byte <= 0x5A
            or 0x61 <= byte <= 0x7A
            or byte in b"_.$:\\/"
        )
        if printable:
            if run_start is None:
                run_start = index
            continue
        if run_start is not None and index - run_start >= IDENTIFIER_MIN:
            text = data[run_start:index].decode("latin1")
            if not text.isdigit():
                found.append({"offset": run_start, "text": text})
        run_start = None
    return found


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path", type=Path, help="decoded program blob")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    data = args.path.read_bytes()
    literals = scan_literals(data)
    names = scan_length_prefixed(data)
    identifiers = scan_identifiers(data)

    if args.json:
        print(
            json.dumps(
                {
                    "size": len(data),
                    "literals": literals,
                    "names": names,
                    "identifiers": identifiers,
                },
                indent=2,
            )
        )
        return 0

    covered = sum(item["size"] for item in literals)
    print(f"body            {len(data)} bytes")
    print(f"literal pools   {len(literals)} pools, {covered} bytes ({covered * 100 // len(data)}%)")
    print(f"name records    {len(names)}")
    print(f"identifiers     {len(identifiers)} runs")
    print()

    print("literal pools")
    for item in literals:
        print(
            f"  0x{item['offset']:04X}  {item['size']:6d}  {item['kind']:<5}  "
            f"{json.dumps(item['preview'], ensure_ascii=False)[:110]}"
        )

    print()
    print("name records")
    for item in names:
        print(f"  0x{item['offset']:04X}  {item['text']}")

    print()
    print("identifiers")
    for item in identifiers[:200]:
        print(f"  0x{item['offset']:04X}  {item['text']}")
    if len(identifiers) > 200:
        print(f"  ... {len(identifiers) - 200} more")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
