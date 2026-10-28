"""Detector package for discovering encoded and obfuscated files."""

from .signatures import EncoderMatch, detect_file_encoder
from .scanner import ScanReport, EncodedFileInfo, scan_project, print_scan_report

__all__ = [
    "EncoderMatch",
    "detect_file_encoder",
    "ScanReport",
    "EncodedFileInfo",
    "scan_project",
    "print_scan_report",
]
