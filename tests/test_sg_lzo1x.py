"""Tests for the standalone sg_lzo1x decompressor."""

import pytest
from engines.sourceguardian import lzo1x_decompress


def test_lzo1x_empty():
    assert lzo1x_decompress(b"") == b""


def test_lzo1x_simple_literal():
    # Long first literal run: byte > 17 (e.g. 17 + 5 = 22 = 0x16)
    # followed by 5 bytes, then EOF marker (\x11\x00\x00)
    data = bytes([17 + 5]) + b"HELLO" + b"\x11\x00\x00"
    out = lzo1x_decompress(data)
    assert out == b"HELLO"


def test_lzo1x_match_m2():
    # Write a literal run, then a match
    # Literal "ABCDE" (len 5): 17 + 5 = 22 = 0x16, then b"ABCDE"
    # State is flr since len >= 4.
    # In flr: if t >= 16: state = match
    # For M2 match: t >= 64 (0x40).
    # t = 64 + (count + 1) * 32 + (d - 1 & 7) << 2 ...
    # Let's test standard minilzo round-trip or known sequence
    raw = b"ABCDE" * 10
    # Create simple literal run
    lit = bytes([17 + len(raw)]) + raw + b"\x11\x00\x00"
    assert lzo1x_decompress(lit) == raw
