"""Recursive project scanner for encoded PHP files."""

from __future__ import annotations

import json
import os
import shutil
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path

from .signatures import EncoderMatch, detect_file_encoder

REPORT_WIDTH = 78
LIST_LIMIT = 40
PROJECT_NAME = "decode-anything"
PROJECT_URL = "https://github.com/0xLLVEL/decode-anything"


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
    truncated_listing: bool = False

    @property
    def encoded_count(self) -> int:
        return len(self.encoded_files)

    @property
    def clean_php_count(self) -> int:
        return max(self.total_php_files - self.encoded_count, 0)

    @property
    def encoder_summary(self) -> dict[str, int]:
        summary: dict[str, int] = {}
        for item in self.encoded_files:
            enc = item.match.name
            summary[enc] = summary.get(enc, 0) + 1
        return summary

    def encoder_groups(self) -> dict[str, dict[str, int]]:
        """Encoder -> variant (PHP ABI, encoder/container build) -> file count."""

        groups: dict[str, dict[str, int]] = {}
        for item in self.encoded_files:
            variants = groups.setdefault(item.match.name, {})
            variants[item.match.variant] = variants.get(item.match.variant, 0) + 1
        return groups

    @property
    def php_scan_rate(self) -> float:
        if self.duration_seconds <= 0:
            return 0.0
        return self.total_php_files / self.duration_seconds

    def to_dict(self) -> dict:
        return {
            "root_path": str(self.root_path),
            "total_files_scanned": self.total_files_scanned,
            "total_php_files": self.total_php_files,
            "clean_php_count": self.clean_php_count,
            "encoded_count": self.encoded_count,
            "encoded_ratio": (
                round(self.encoded_count / self.total_php_files, 4)
                if self.total_php_files
                else 0.0
            ),
            "duration_seconds": round(self.duration_seconds, 3),
            "encoders": self.encoder_summary,
            "encoder_groups": self.encoder_groups(),
            "files": [
                {
                    "path": str(f.path),
                    "relative_path": f.relative_path,
                    "size_bytes": f.size_bytes,
                    "encoder": f.match.name,
                    "version_hint": f.match.version_hint,
                    "php_version": f.match.php_version,
                    "tool_version": f.match.toolchain,
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


class _ProgressBar:
    """Single-line progress bar that only draws on a real terminal."""

    def __init__(self, total: int, *, stream=None, enabled: bool = True) -> None:
        self.total = max(total, 1)
        self.stream = stream if stream is not None else sys.stdout
        encoding = getattr(self.stream, "encoding", None) or "utf-8"
        try:
            "█".encode(encoding)
            self.full, self.empty, self.cut = "█", "░", "…"
        except (UnicodeEncodeError, LookupError):
            self.full, self.empty, self.cut = "#", "-", "..."
        self.enabled = bool(enabled) and total > 1 and self.stream.isatty()
        self.columns = shutil.get_terminal_size((100, 24)).columns
        self.width = 24
        self.started = time.perf_counter()
        self.drawn = False

    def update(self, done: int, label: str = "") -> None:
        if not self.enabled:
            return
        ratio = done / self.total
        filled = int(self.width * ratio)
        bar = self.full * filled + self.empty * (self.width - filled)
        rate = done / max(time.perf_counter() - self.started, 1e-9)
        line = f"  [{bar}] {ratio * 100:3.0f}%  {done:,}/{self.total:,}  {rate:,.0f}/s"
        room = self.columns - len(line) - 3
        if label and room > 8:
            if len(label) > room:
                keep = max(room - len(self.cut), 1)
                label = self.cut + label[-keep:]
            line += f"  {label}"
        self.stream.write("\r" + line + " " * max(self.columns - 1 - len(line), 0))
        self.stream.flush()
        self.drawn = True

    def close(self) -> None:
        if self.enabled and self.drawn:
            self.stream.write("\r" + " " * (self.columns - 1) + "\r")
            self.stream.flush()


def _walk_files(root: Path, ignored: set[str]):
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = sorted(d for d in dirnames if d not in ignored)
        for fname in sorted(filenames):
            yield Path(dirpath) / fname


def scan_project(
    root: Path | str,
    *,
    ignored_dirs: set[str] | None = None,
    php_extensions: tuple[str, ...] = (
        ".php",
        ".inc",
        ".phtml",
        ".php5",
        ".php7",
        ".php8",
    ),
    progress: bool = True,
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

    files = list(_walk_files(root_path, ignored))
    php_files = [path for path in files if path.suffix.lower() in php_extensions]
    report.total_files_scanned = len(files)
    report.total_php_files = len(php_files)

    bar = _ProgressBar(len(php_files), enabled=progress)
    for done, fpath in enumerate(php_files, start=1):
        bar.update(done - 1, fpath.name)
        match = detect_file_encoder(fpath)
        if match is not None:
            try:
                rel_path = str(fpath.relative_to(root_path))
            except ValueError:
                rel_path = str(fpath)
            try:
                size = fpath.stat().st_size
            except OSError:
                size = 0
            report.encoded_files.append(
                EncodedFileInfo(
                    path=fpath,
                    relative_path=rel_path,
                    size_bytes=size,
                    match=match,
                )
            )
    bar.update(len(php_files))
    bar.close()

    report.duration_seconds = time.perf_counter() - start_time
    return report


def _pct(part: int, whole: int) -> str:
    if whole <= 0:
        return "  -  "
    return f"{part / whole * 100:5.1f}%"


def _plural(count: int, word: str) -> str:
    return word if count == 1 else f"{word}s"


def print_scan_report(report: ScanReport, *, as_json: bool = False) -> None:
    """Print the scan report nicely to console."""

    if as_json:
        print(json.dumps(report.to_dict(), indent=2))
        return

    thin = "-" * REPORT_WIDTH
    print(PROJECT_NAME.center(REPORT_WIDTH))
    print(f"source: {PROJECT_URL}".center(REPORT_WIDTH))
    print()
    print(f" {'Target':<15} {report.root_path}")
    print(f" {'Files walked':<15} {report.total_files_scanned:,}")
    php_share = (
        f"  ({_pct(report.total_php_files, report.total_files_scanned).strip()} of files)"
        if report.total_files_scanned
        else ""
    )
    encoded_share = (
        f"  ({_pct(report.encoded_count, report.total_php_files).strip()} of PHP)"
        if report.total_php_files
        else ""
    )
    print(f" {'PHP files':<15} {report.total_php_files:,}{php_share}")
    print(f" {'  encoded':<15} {report.encoded_count:,}{encoded_share}")
    print(f" {'  clean':<15} {report.clean_php_count:,}")
    print(
        f" {'Duration':<15} {report.duration_seconds:.2f}s"
        f"  ({report.php_scan_rate:,.0f} PHP files/s)"
    )
    print(thin)

    if not report.encoded_files:
        print(" [OK] No encoded or obfuscated files detected.")
        print()
        return

    groups = report.encoder_groups()
    total = report.encoded_count
    print(
        f" {total:,} encoded {_plural(total, 'file')} across "
        f"{len(groups)} {_plural(len(groups), 'encoder')}"
    )

    longest = max(len(name) for name in groups)
    bar_width = 22
    variant_width = 46
    for enc, variants in sorted(groups.items(), key=lambda kv: -sum(kv[1].values())):
        count = sum(variants.values())
        filled = round(bar_width * count / total)
        bar = "#" * filled + "-" * (bar_width - filled)
        print(f"   {enc:<{longest}}  {count:>5,}  {_pct(count, total)}  {bar}")
        for variant, variant_count in sorted(variants.items(), key=lambda kv: -kv[1]):
            label = variant if len(variant) <= variant_width else variant[: variant_width - 3] + "..."
            print(f"       {label:<{variant_width}}  {variant_count:>5,}")

    print(thin)
    print(" Detected files")
    listed = report.encoded_files[:LIST_LIMIT]
    for index, item in enumerate(listed, start=1):
        label = item.match.variant
        if item.match.php_version or item.match.toolchain:
            label = f"{item.match.name}: {label}"
        else:
            label = item.match.name
        print(f"  [{index:>3}] {label}")
        print(f"        {item.relative_path}  ({item.size_bytes:,} bytes)")
    hidden = report.encoded_count - len(listed)
    if hidden > 0:
        print(f"  ... and {hidden:,} more (use --json for the full list)")
    print()
