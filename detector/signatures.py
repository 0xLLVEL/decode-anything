"""Encoder signatures and detection patterns for PHP codebases.

Detection is two-tier. The cheap string/binary signatures decide *whether* a
file is protected; for ionCube and SourceGuardian the file also carries its own
version fields, so the match is filled from a real parse instead of a guess:

    ionCube         HR+c payload -> header trailer -> PHP ABI, encoder build
    SourceGuardian  sg_load() payload -> preheader TLV -> container version
    YAK Pro         banner text, when the obfuscator left one
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

YAKPRO_VERSION = re.compile(rb"Php Obfuscator[^\d]{0,8}(\d+\.\d+(?:\.\d+)?)")
YAKPRO_BANNER = re.compile(rb"YAK Pro[^\r\n\x00]{0,64}")


@dataclass(frozen=True)
class EncoderMatch:
    """One detected encoder. `version_hint` is the short label used in reports."""

    name: str
    version_hint: str | None = None
    confidence: float = 1.0
    details: str = ""
    php_version: str | None = None
    toolchain: str | None = None

    @property
    def variant(self) -> str:
        """Grouping key for summaries: the most specific label the file supports."""

        parts = []
        if self.php_version:
            parts.append(f"PHP {self.php_version}")
        if self.toolchain:
            parts.append(self.toolchain)
        return " | ".join(parts) if parts else "version not in file"


def _ioncube_header(path: Path) -> tuple[str | None, str | None, str]:
    """Parse the real header: (php_version, encoder label, format note)."""

    from engines.ioncube.header import decode_file

    report, _ = decode_file(path)
    trailer = report["header_trailer"]
    initial = report["initial_header"]

    code = int(trailer["php_version_code"])
    php_version = f"{code // 10}.{code % 10}" if 10 <= code <= 99 else None

    major = int(trailer["encoder_major"])
    minor = int(trailer["encoder_minor"])
    revision = int(trailer["encoder_revision"])
    sv = int(initial["version"])
    toolchain = f"encoder {major}.{minor}.{revision} (sv{sv})"

    minimum = int(initial["minimum_loader_version"])
    if minimum:
        toolchain += f", loader >= {minimum}"
    return php_version, toolchain, f"sv{sv}"


def _detect_ioncube(path: Path, header: bytes, sample: bytes) -> EncoderMatch | None:
    has_payload = b"HR+c" in header or b"HR+c" in sample
    banner = b"ionCube Loader" in sample or b"ioncube_file_info" in sample
    if not (has_payload or banner):
        return None

    php_version = toolchain = None
    note = ""
    if has_payload:
        try:
            php_version, toolchain, sv = _ioncube_header(path)
            note = f"ionCube {sv} header decoded"
        except Exception as exc:  # malformed payload is still an ionCube file
            note = f"ionCube payload present, header parse failed ({type(exc).__name__})"
    else:
        note = "ionCube loader bootstrap banner detected"

    hint = " | ".join(part for part in (
        f"PHP {php_version}" if php_version else None, toolchain
    ) if part) or None
    return EncoderMatch(
        name="ionCube",
        version_hint=hint,
        confidence=1.0 if has_payload else 0.95,
        details=note,
        php_version=php_version,
        toolchain=toolchain,
    )


def _detect_sourceguardian(path: Path, header: bytes, sample: bytes) -> EncoderMatch | None:
    if b"sg_load(" not in sample and b"__SG_EXT__" not in sample:
        if not (header.startswith(b"SG") or b"sourceguardian" in sample.lower()):
            return None

    toolchain = None
    note = "SourceGuardian loader call detected"
    try:
        from engines.sourceguardian.container import get_payload, parse_preheader

        version, metadata_size, _flags, _offset = parse_preheader(get_payload(path))
        toolchain = f"container v{version}"
        note = f"container v{version}, {metadata_size}-byte metadata"
    except Exception:
        pass

    return EncoderMatch(
        name="SourceGuardian",
        version_hint=toolchain,
        confidence=1.0,
        details=note,
        toolchain=toolchain,
    )


def _detect_zend_guard(path: Path, header: bytes, sample: bytes) -> EncoderMatch | None:
    if b"Zend Guard" in sample or b"Zend Engine" in sample or header.startswith(b"Zend\x00"):
        return EncoderMatch(
            name="Zend Guard",
            confidence=1.0,
            details="Zend Guard encoded binary detected",
        )
    return None


def _detect_php_bolt(path: Path, header: bytes, sample: bytes) -> EncoderMatch | None:
    if b"bolt_encrypt" in sample or b"boltr_" in sample:
        return EncoderMatch(
            name="PHP Bolt",
            confidence=1.0,
            details="PHP Bolt encryption wrapper detected",
        )
    return None


def _detect_yakpro(path: Path, header: bytes, sample: bytes) -> EncoderMatch | None:
    banner = YAKPRO_BANNER.search(header) or YAKPRO_BANNER.search(sample)
    if banner:
        match = YAKPRO_VERSION.search(banner.group(0))
        version = match.group(1).decode() if match else None
        return EncoderMatch(
            name="YAK Pro",
            version_hint=f"YAK Pro {version}" if version else None,
            confidence=1.0,
            details="YAK Pro PHP Obfuscator (control flow flattening & string escapes)",
            toolchain=f"obfuscator {version}" if version else None,
        )
    if b"yakpro-po" in header or b"yakpro-po" in sample:
        return EncoderMatch(
            name="YAK Pro",
            confidence=1.0,
            details="YAK Pro PHP Obfuscator marker detected",
        )
    if b"goto " in sample and (b"\\x" in sample or b"\\0" in sample or b"\\1" in sample):
        if sample.count(b"goto ") >= 4:
            return EncoderMatch(
                name="YAK Pro",
                confidence=0.9,
                details="statement shuffle & goto flattening detected",
            )
    return None


def _detect_general_obfuscator(path: Path, header: bytes, sample: bytes) -> EncoderMatch | None:
    if b"$$GLOBALS" in sample and sample.count(b"$$") > 5:
        return EncoderMatch(
            name="Yakpro-Po / Obfuscated",
            confidence=0.8,
            details="heavily scrambled variable names detected",
        )
    if b"eval(base64_decode(" in sample or b"eval(gzinflate(" in sample:
        return EncoderMatch(
            name="Eval Packer",
            confidence=0.85,
            details="eval(base64_decode/gzinflate) packing detected",
        )
    return None


Detector = Callable[[Path, bytes, bytes], EncoderMatch | None]

# ionCube is not in this list: its version fields need the file, not a sample.
ENCODER_DETECTORS: list[Detector] = [
    _detect_sourceguardian,
    _detect_zend_guard,
    _detect_php_bolt,
    _detect_yakpro,
    _detect_general_obfuscator,
]


def detect_file_encoder(path: Path) -> EncoderMatch | None:
    """Analyze file header and sample to detect if it's encoded/obfuscated."""

    try:
        with path.open("rb") as handle:
            header = handle.read(256)
            handle.seek(0)
            sample = handle.read(4096)
    except OSError:
        return None

    match = _detect_ioncube(path, header, sample)
    if match is not None:
        return match

    for detector in ENCODER_DETECTORS:
        match = detector(path, header, sample)
        if match is not None:
            return match

    return None
