"""ionCube 7.x (sv5) buffer decryption primitives, reversed from the 7.2 loader.

Function map (image base ``0x180000000``, module ``ioncube_loader_win_7.2.dll``):

===========================  ====================================================
``sub_180001E10``            buffer decrypt: ``pt[i] = ct[i] ^ BYTE1(next())``
``sub_1800031B0``            caller; resolves the key, decrypts ``a1+64`` and
                             swaps the buffer in place
``sub_180004170``            key resolver, dispatch on license mode ``1..5``
``sub_180004080``            mode 4: unpack the header license block, look the
                             key up through the PHP symbol table
``sub_180003BE0``            symbol-table lookup by name, SHA-1 fallback
``sub_18000C7C0``            ``bytes([13]) + SHA1(name + extra)`` key generator
``sub_18009D540``            PRNG factory (4, 5, 6)
``sub_18009D2F0``            PRNG 6 ``next()``: two-word LCG, 18000/30345 taps
``sub_18009D2E0``            PRNG 6 seeding: ``state = (seed0, seed1)``
``sub_180007340``            seed0, djb2x over the key bytes
``sub_180007390``            seed1, murmur3 ``fmix32`` over the key bytes
===========================  ====================================================

PRNG 6 is *not* ``MT4IC``; it is a 32-bit two-word generator whose output dword
is ``state0 + rol16(state1)``. Only ``BYTE1`` of that dword enters the XOR.
"""

from __future__ import annotations

import hashlib
import struct
from collections.abc import Sequence
from dataclasses import dataclass

M32 = 0xFFFFFFFF
KEY_PREFIX = 0x0D


def rol4(value: int, count: int) -> int:
    value &= M32
    return ((value << count) | (value >> (32 - count))) & M32


def seed0(key: bytes) -> int:
    """``sub_180007340`` — 1025*(h + signed byte), h = (h>>6)^h, then a final mix."""
    h = 0
    for byte in key:
        signed = byte - 256 if byte > 127 else byte
        h = (1025 * (h + signed)) & M32
        h = ((h >> 6) ^ h) & M32
    h9 = (9 * h) & M32
    return (32769 * (h9 ^ (h9 >> 11))) & M32


def _fmix32(h: int) -> int:
    h ^= h >> 16
    h = (h * 0x85EBCA6B) & M32
    h ^= h >> 13
    h = (h * 0xC2B2AE35) & M32
    h ^= h >> 16
    return h


def seed1(key: bytes) -> int:
    """``sub_180007390`` — murmur3 over the key bytes with seed 31."""
    h = 31
    blocks = len(key) // 4
    for index in range(blocks):
        k = struct.unpack_from("<I", key, index * 4)[0]
        k = (k * 0xCC9E2D51) & M32
        k = rol4(k, 15)
        k = (k * 0x1B873593) & M32
        h ^= k
        h = rol4(h, 13)
        h = (h * 5 + 0xE6546B64) & M32
    tail = key[blocks * 4:]
    k = 0
    if len(tail) >= 3:
        k ^= tail[2] << 16
    if len(tail) >= 2:
        k ^= tail[1] << 8
    if len(tail) >= 1:
        k ^= tail[0]
        k = (k * 0xCC9E2D51) & M32
        k = rol4(k, 15)
        k = (k * 0x1B873593) & M32
        h ^= k
    h ^= len(key)
    return _fmix32(h)


@dataclass
class Type6Rng:
    """``sub_18009D2F0``. The cached branch serves a repeat of the last dword."""

    state0: int
    state1: int
    cached: int = 0
    have_cached: bool = False

    @classmethod
    def from_key(cls, key: bytes) -> "Type6Rng":
        return cls(seed0(key), seed1(key))

    def next(self) -> int:
        if self.have_cached:
            self.have_cached = False
            return self.cached
        self.state1 = ((self.state1 >> 16) + 30345 * (self.state1 & 0xFFFF)) & M32
        self.state0 = ((self.state0 >> 16) + 18000 * (self.state0 & 0xFFFF)) & M32
        self.cached = (self.state0 + rol4(self.state1, 16)) & M32
        self.have_cached = True
        return self.cached


def derive_key(material: bytes, extra: bytes = b"") -> bytes:
    """``sub_18000C7C0`` — 0x0D + SHA1(material + extra)."""
    return bytes([KEY_PREFIX]) + hashlib.sha1(material + extra).digest()


def decrypt_buffer(ciphertext: bytes, key: bytes, shift: int = 8) -> bytes:
    """``sub_180001E10``. ``shift`` 8 is BYTE1, the only lane seen in the builder."""
    rng = Type6Rng.from_key(key)
    return bytes(
        byte ^ ((rng.next() >> shift) & 0xFF) for byte in ciphertext
    )


def keystream(key: bytes, count: int, shift: int = 8) -> bytes:
    rng = Type6Rng.from_key(key)
    return bytes((rng.next() >> shift) & 0xFF for _ in range(count))


def record_key(words: Sequence[int]) -> bytes:
    """``sub_180003570`` -- the 17-byte key from four little-endian dwords.

    Each dword is written big-endian, every byte is incremented by one, and a
    NUL terminator closes the buffer. The loader keeps the key length as
    ``zend_string->len + 1``, so the terminator is part of the hash input.
    """
    if len(words) != 4:
        raise ValueError("record_key wants exactly four dwords")
    return bytes((byte + 1) & 0xFF for word in words for byte in word.to_bytes(4, "big")) + b"\x00"


def decrypt_record(data: bytes, key: bytes) -> bytes:
    """``sub_180001E10`` -- the record cipher.

    Same two-word multiply-add as :class:`Type6Rng`, but the caller
    (``sub_18009CA40``) performs one state step per byte instead of serving the
    cached dword twice. The byte lane is ``BYTE1`` of the result.
    """
    state0, state1 = seed0(key), seed1(key)
    out = bytearray(len(data))
    for index, value in enumerate(data):
        state1 = ((state1 >> 16) + 30345 * (state1 & 0xFFFF)) & M32
        state0 = ((state0 >> 16) + 18000 * (state0 & 0xFFFF)) & M32
        word = (state0 + (((state1 << 16) | (state1 >> 16)) & M32)) & M32
        out[index] = value ^ ((word >> 8) & 0xFF)
    return bytes(out)
