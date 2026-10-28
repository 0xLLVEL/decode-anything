"""Encoder signatures and detection patterns for PHP codebases."""

from __future__ import annotations
from dataclasses import dataclass
from typing import Callable
from pathlib import Path


@dataclass(frozen=True)
class EncoderMatch:
    name: str
    version_hint: str | None = None
    confidence: float = 1.0
    details: str = ""


def _detect_ioncube(header: bytes, content_sample: bytes) -> EncoderMatch | None:
    # Magic bytes check
    if b"HR+c" in header:
        version = None
        if b"HR+c\x08\x01" in header or b"8.1" in header:
            version = "PHP 8.1"
        elif b"HR+c\x08\x02" in header or b"8.2" in header:
            version = "PHP 8.2"
        elif b"HR+c\x08\x03" in header or b"8.3" in header:
            version = "PHP 8.3"
        elif b"HR+c\x08\x04" in header or b"8.4" in header:
            version = "PHP 8.4"
        return EncoderMatch(
            name="ionCube",
            version_hint=version,
            confidence=1.0,
            details="ionCube v12/v13 encoded bytecode",
        )

    if b"ionCube Loader" in content_sample or b"ioncube_file_info" in content_sample:
        return EncoderMatch(
            name="ionCube",
            version_hint=None,
            confidence=0.95,
            details="ionCube loader bootstrap banner detected",
        )
    return None


def _detect_sourceguardian(header: bytes, content_sample: bytes) -> EncoderMatch | None:
    if b"sg_load(" in content_sample or b"__SG_EXT__" in content_sample:
        return EncoderMatch(
            name="SourceGuardian",
            confidence=1.0,
            details="SourceGuardian loader call detected",
        )
    if header.startswith(b"SG") or b"sourceguardian" in content_sample.lower():
        return EncoderMatch(
            name="SourceGuardian",
            confidence=0.9,
            details="SourceGuardian signature detected",
        )
    return None


def _detect_zend_guard(header: bytes, content_sample: bytes) -> EncoderMatch | None:
    if b"Zend Guard" in content_sample or b"Zend Engine" in content_sample or header.startswith(b"Zend\x00"):
        return EncoderMatch(
            name="Zend Guard",
            confidence=1.0,
            details="Zend Guard encoded binary detected",
        )
    return None


def _detect_php_bolt(header: bytes, content_sample: bytes) -> EncoderMatch | None:
    if b"bolt_encrypt" in content_sample or b"boltr_" in content_sample:
        return EncoderMatch(
            name="PHP Bolt",
            confidence=1.0,
            details="PHP Bolt encryption wrapper detected",
        )
    return None


def _detect_general_obfuscator(header: bytes, content_sample: bytes) -> EncoderMatch | None:
    # Yakpro-Po / general PHP scramblers
    if b"$$GLOBALS" in content_sample and content_sample.count(b"$$") > 5:
        return EncoderMatch(
            name="Yakpro-Po / Obfuscated",
            confidence=0.8,
            details="Heavily scrambled variable names detected",
        )
    if b"eval(base64_decode(" in content_sample or b"eval(gzinflate(" in content_sample:
        return EncoderMatch(
            name="Eval Packer",
            confidence=0.85,
            details="eval(base64_decode/gzinflate) packing detected",
        )
    return None


ENCODER_DETECTORS: list[Callable[[bytes, bytes], EncoderMatch | None]] = [
    _detect_ioncube,
    _detect_sourceguardian,
    _detect_zend_guard,
    _detect_php_bolt,
    _detect_general_obfuscator,
]


def detect_file_encoder(path: Path) -> EncoderMatch | None:
    """Analyze file header and sample to detect if it's encoded/obfuscated."""
    try:
        with path.open("rb") as f:
            header = f.read(256)
            f.seek(0)
            sample = f.read(4096)
    except Exception:
        return None

    for detector in ENCODER_DETECTORS:
        match = detector(header, sample)
        if match is not None:
            return match

    return None
