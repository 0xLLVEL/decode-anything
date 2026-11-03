#!/usr/bin/env python3
"""Write the static 7.4 structure of a file as ``icdump-ir-v1`` JSON.

No PHP, no loader DLL, no dumper extension: the container, the body, the record
scan, the seed stubs, the mask stream and the opcode walk all run in Python.

Operand values are not part of the body, so every emitted instruction carries
``IS_UNUSED`` operands - the document is the file's skeleton (class, methods,
argument counts, line ranges, opcode order), not decompiled source.

    python tools/ic74_static_ir.py file.php -o file.icdump.json
    python tools/ic74_static_ir.py contacts.php --truth contacts.opcodes.json
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from engines.ioncube.static74 import static74_icdump  # noqa: E402


def compare(icdump: dict, truth_path: Path) -> dict:
    """Opcode bytes and line ranges against a runtime dump, record by record."""

    truth = json.loads(truth_path.read_text(encoding="utf-8"))
    expected: dict[str, dict] = {}
    for item in (truth.get("op_arrays") or {}).values():
        name = item.get("function_name")
        name = name.get("value") if isinstance(name, dict) else name
        if name:
            expected[name] = item

    got: dict[str, dict] = {}
    for entry in icdump["op_arrays"].values():
        name = entry.get("function_name")
        name = name.get("value") if isinstance(name, dict) else name
        if name:
            got[name] = entry

    streams = ranges = 0
    mismatched: list[str] = []
    for name, want in expected.items():
        entry = got.get(name)
        if entry is None:
            mismatched.append(f"missing:{name}")
            continue
        got_ops = [op["opcode"] for op in entry.get("opcodes") or []]
        want_ops = [op["opcode"] for op in want.get("opcodes") or []]
        if got_ops == want_ops:
            streams += 1
        else:
            mismatched.append(f"opcodes:{name}")
        if (entry.get("line_start"), entry.get("line_end")) == (
            want.get("line_start"),
            want.get("line_end"),
        ):
            ranges += 1
        else:
            mismatched.append(f"lines:{name}")
    return {
        "truth_op_arrays": len(expected),
        "opcode_streams": streams,
        "line_ranges": ranges,
        "mismatched": mismatched,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path", type=Path, help="encoded PHP file")
    parser.add_argument("-o", "--output", type=Path, help="output icdump-ir-v1 JSON")
    parser.add_argument("--truth", type=Path, help="compare against a runtime dump")
    args = parser.parse_args(argv)

    icdump = static74_icdump(args.path)
    summary = icdump["summary"]
    static = summary["static_74"]
    print(f"source                {args.path}")
    print(f"encoder              {icdump.get('encoder')}")
    print(f"op_arrays            {summary['op_array_count']}")
    print(f"classes              {len(icdump['class_index'])}")
    print(f"opcode_total         {static['opcode_total']}")
    print(f"opcode_escapes       {static['opcode_escapes']}")
    print(f"unseeded             {len(static['unseeded'])}")
    print("operands             unresolved (not in the body)")

    status = 0
    if args.truth:
        result = compare(icdump, args.truth)
        print(f"truth op_arrays      {result['truth_op_arrays']}")
        print(f"opcode streams       {result['opcode_streams']}/{result['truth_op_arrays']}")
        print(f"line ranges          {result['line_ranges']}/{result['truth_op_arrays']}")
        if result["mismatched"]:
            status = 1
            for item in result["mismatched"][:10]:
                print(f"  mismatch           {item}")

    if args.output:
        args.output.write_text(json.dumps(icdump, indent=1), encoding="utf-8")
        print(f"written              {args.output}")
    return status


if __name__ == "__main__":
    raise SystemExit(main())
