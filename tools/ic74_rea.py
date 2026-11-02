#!/usr/bin/env python3
"""Thin wrapper over `rea --format json` so IDA answers land in one file per query.

Every call records the evidence id, the parameters and the normalized result, which
keeps the loader analysis reproducible without pasting YAML transcripts around.

    python tools/ic74_rea.py search "has expired" --kind strings
    python tools/ic74_rea.py decompile 0x1800A02A0
    python tools/ic74_rea.py xrefs 0x1800B4E90
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TARGET = ROOT / "loader" / "ioncube_loader_win_7.4.dll"
CACHE = ROOT / "scratch" / "ida74"
CONFIG = ROOT / "scratch" / "rea-ida.json"


def run(args: list[str]) -> dict:
    env = dict(os.environ)
    env["REA_IDA_MCP_CONFIG"] = str(CONFIG)
    rea = shutil.which("rea") or shutil.which("rea.cmd") or "rea"
    head = args[:1]
    tail = args[1:]
    proc = subprocess.run(
        [rea, *head, str(TARGET), *tail, "--provider", "ida", "--format", "json"],
        shell=False,
        capture_output=True,
        text=True,
        env=env,
        encoding="utf-8",
        errors="replace",
    )
    if proc.returncode != 0:
        raise SystemExit(proc.stderr[-2000:] or proc.stdout[-2000:])
    return json.loads(proc.stdout)


def main(argv: list[str]) -> int:
    if len(argv) < 3:
        print(__doc__)
        return 2
    verb, subject = argv[1], argv[2]
    CACHE.mkdir(parents=True, exist_ok=True)
    if verb == "search":
        payload = run(["search", subject, *argv[3:], "--mode", "literal"])
    else:
        payload = run([verb, subject, *argv[3:]])
    slug = "_".join(part.strip("0x") for part in (verb, subject))
    slug = "".join(c if c.isalnum() or c in "._-" else "_" for c in slug)
    (CACHE / f"{slug}.json").write_text(json.dumps(payload, indent=1), encoding="utf-8")

    result = payload.get("normalized_result") or payload.get("raw_result")
    text = json.dumps(result, indent=1)
    print(text[:8000])
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
