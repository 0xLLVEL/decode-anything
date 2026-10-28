"""Recursive project scanner for encoded PHP files."""

from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Generator

from .signatures import EncoderMatch, detect_file_encoder


@dataclass
class EncodedFileInfo:
    path: Path
    relative_path: str
    size_bytes: int
    match: EncoderMatch


@dataclass
class ScanReport:
    root_path: Path
    total_files_scanned: int = 0
    total_php_files: int = 0
    encoded_files: list[EncodedFileInfo] = field(default_factory=list)
    duration_seconds: float = 0.0

    @property
    def encoded_count(self) -> int:
        return len(self.encoded_files)

    @property
    def encoder_summary(self) -> dict[str, int]:
        summary: dict[str, int] = {}
        for item in self.encoded_files:
            enc = item.match.name
            summary[enc] = summary.get(enc, 0) + 1
        return summary

    def to_dict(self) -> dict:
        return {
            "root_path": str(self.root_path),
            "total_files_scanned": self.total_files_scanned,
            "total_php_files": self.total_php_files,
            "encoded_count": self.encoded_count,
            "duration_seconds": round(self.duration_seconds, 3),
            "encoders": self.encoder_summary,
            "files": [
                {
                    "path": str(f.path),
                    "relative_path": f.relative_path,
                    "size_bytes": f.size_bytes,
                    "encoder": f.match.name,
                    "version_hint": f.match.version_hint,
                    "details": f.match.details,
                    "confidence": f.match.confidence,
                }
                for f in self.encoded_files
            ],
        }


# Directories typically ignored in scan
DEFAULT_IGNORED_DIRS = {
    ".git",
    ".svn",
    ".hg",
    "node_modules",
    ".pytest_cache",
    "__pycache__",
    ".idea",
    ".vscode",
}


def scan_project(
    root: Path | str,
    *,
    ignored_dirs: set[str] | None = None,
    php_extensions: tuple[str, ...] = (".php", ".inc", ".phtml", ".php5", ".php7", ".php8"),
) -> ScanReport:
    """Scan a project directory recursively for encoded PHP files."""
    root_path = Path(root).resolve()
    ignored = ignored_dirs if ignored_dirs is not None else DEFAULT_IGNORED_DIRS
    report = ScanReport(root_path=root_path)

    start_time = time.perf_counter()

    if root_path.is_file():
        report.total_files_scanned = 1
        if root_path.suffix.lower() in php_extensions:
            report.total_php_files = 1
            match = detect_file_encoder(root_path)
            if match is not None:
                report.encoded_files.append(
                    EncodedFileInfo(
                        path=root_path,
                        relative_path=root_path.name,
                        size_bytes=root_path.stat().st_size,
                        match=match,
                    )
                )
        report.duration_seconds = time.perf_counter() - start_time
        return report

    for dirpath, dirnames, filenames in os.walk(root_path):
        # Filter ignored directories in-place
        dirnames[:] = [d for d in dirnames if d not in ignored]

        for fname in filenames:
            fpath = Path(dirpath) / fname
            report.total_files_scanned += 1

            if fpath.suffix.lower() not in php_extensions:
                continue

            report.total_php_files += 1
            match = detect_file_encoder(fpath)
            if match is not None:
                try:
                    rel_p = str(fpath.relative_to(root_path))
                except ValueError:
                    rel_p = str(fpath)

                report.encoded_files.append(
                    EncodedFileInfo(
                        path=fpath,
                        relative_path=rel_p,
                        size_bytes=fpath.stat().st_size,
                        match=match,
                    )
                )

    report.duration_seconds = time.perf_counter() - start_time
    return report


def print_scan_report(report: ScanReport, *, as_json: bool = False) -> None:
    """Print the scan report nicely to console."""
    if as_json:
        print(json.dumps(report.to_dict(), indent=2))
        return

    print("=" * 72)
    print(" PROJECT ENCODER SCANNER REPORT")
    print("=" * 72)
    print(f" Target Path       : {report.root_path}")
    print(f" Total Files       : {report.total_files_scanned}")
    print(f" PHP Files Found   : {report.total_php_files}")
    print(f" Encoded Files     : {report.encoded_count}")
    print(f" Scan Duration     : {report.duration_seconds:.2f}s")
    print("-" * 72)

    if not report.encoded_files:
        print(" [OK] No encoded or obfuscated files detected in project.")
        print("=" * 72)
        return

    print(" Breakdown by Encoder:")
    for enc, count in sorted(report.encoder_summary.items(), key=lambda x: -x[1]):
        print(f"   * {enc:<25}: {count} file(s)")

    print("-" * 72)
    print(" Detected Encoded Files:")
    for i, item in enumerate(report.encoded_files, start=1):
        v_hint = f" ({item.match.version_hint})" if item.match.version_hint else ""
        print(f"  [{i:>3}] [{item.match.name}{v_hint}] {item.relative_path}")
        if item.match.details:
            print(f"        -> {item.match.details} ({item.size_bytes:,} bytes)")
    print("=" * 72)
