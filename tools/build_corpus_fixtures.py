#!/usr/bin/env python3
"""Regenerate the encoded SourceGuardian corpus fixture.

The fixture is a real ``sg_load`` container: Blowfish-CBC over LZO1X, sealed
with the first key in ``engines/sourceguardian/keys.py`` so the normal decode
path can open it. The payload is a minimal PHP 8.1 op_array that echoes a
string, built with the same primitives the SG unit tests use.

Usage:
    python tools/build_corpus_fixtures.py
"""

from __future__ import annotations

import argparse
import base64
import struct
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from engines.sourceguardian.container import Blowfish, rol1
from engines.sourceguardian.keys import SG_KEYS

DEFAULT_OUTPUT = ROOT / "tests" / "corpus" / "sourceguardian" / "hello.php"
SG_VERSION = 0x21
PHP_81_ECHO = 136
PHP_81_RETURN = 62


def u32(value: int) -> bytes:
    return struct.pack("<I", value)


def zstr(value: str | None) -> bytes:
    if value is None:
        return u32(0xFFFFFFFF)
    encoded = value.encode("utf-8")
    return u32(len(encoded)) + encoded


def zval_int(value: int) -> bytes:
    return u32(4) + u32(0) + u32(value)


def zval_string(value: str) -> bytes:
    return u32(6) + u32(0) + zstr(value)


def opcode(
    number: int,
    *,
    op1_nibble: int = 0xF,
    payload: bytes = b"",
    lineno: int = 1,
) -> bytes:
    type_word = (0xF << 12) | (0xF << 8) | (0xF << 4) | op1_nibble
    return bytes([number]) + u32(type_word) + payload + u32(lineno)


def op_array(
    *,
    function_name: str = "",
    literals: list[bytes] | None = None,
    opcodes: list[bytes] | None = None,
) -> bytes:
    literals = literals or []
    opcodes = opcodes or []

    buf = bytearray()
    buf.append(0xFF)                 # version gate terminator
    buf.append(2)                    # full op_array
    buf.extend(u32(0))               # fn_flags
    buf.extend(b"\x00\x00\x00")
    buf.extend(u32(0))               # num_args
    buf.extend(u32(0))               # required_num_args
    buf.extend(zstr(function_name or None))
    buf.extend(zstr(None))           # scope name
    buf.extend(u32(len(literals)))
    for literal in literals:
        buf.extend(literal)
    buf.extend(u32(0))               # ext handles
    buf.extend(u32(16))              # literal slot size
    buf.extend(u32(len(opcodes)))
    buf.extend(u32(1))               # temp count
    buf.extend(u32(0))               # cv count
    for op in opcodes:
        buf.extend(op)
    buf.extend(u32(0))               # line records
    buf.extend(u32(0))               # try/catch entries
    buf.extend(u32(0))               # static variables
    buf.extend(zstr(None))           # doc comment
    buf.extend(u32(1))               # line start
    buf.extend(u32(1))               # line end
    buf.extend(u32(0))               # prototype depth
    buf.extend(u32(0))               # attributes
    buf.extend(u32(0))               # nested op_arrays
    return bytes(buf)


def bytecode_body() -> bytes:
    body = bytearray()
    body.extend(b"SOURCEGUARDIAN\x00")
    body.extend(u32(SG_VERSION))
    body.extend(u32(0))              # flags
    body.extend(u32(0))
    body.extend(u32(0))
    body.append(0)                   # no functions
    body.append(0)                   # no classes
    body.extend(
        op_array(
            literals=[zval_string("hello from sourceguardian"), zval_int(1)],
            opcodes=[
                opcode(PHP_81_ECHO, op1_nibble=3, payload=b"\x00" + u32(0)),
                opcode(PHP_81_RETURN, op1_nibble=3, payload=b"\x00" + u32(1)),
            ],
        )
    )
    return bytes(body)


def literal_stream(payload: bytes) -> bytes:
    """LZO1X literal-only stream for payloads of at most 238 bytes."""
    if not 4 <= len(payload) <= 238:
        raise ValueError(f"payload must be 4..238 bytes, got {len(payload)}")
    return bytes([17 + len(payload)]) + payload + b"\x11\x00\x00"


def seal(key: bytes, stream: bytes, declen: int) -> bytes:
    length = 12 + len(stream) + 3
    data = struct.pack("<III", 0, length, declen) + stream + b"\x00\x00\x00"
    data = struct.pack("<I", rol1(b"\x00\x00\x00\x00" + data[4:])) + data[4:]
    data += b"\x00" * ((-len(data)) % 8)
    return cbc_encrypt(Blowfish(key), data)


def cbc_encrypt(cipher: Blowfish, data: bytes) -> bytes:
    out = bytearray()
    prev_left = prev_right = 0
    for offset in range(0, len(data) - 7, 8):
        left = int.from_bytes(data[offset:offset + 4], "big") ^ prev_left
        right = int.from_bytes(data[offset + 4:offset + 8], "big") ^ prev_right
        prev_left, prev_right = cipher.encrypt_block(left, right)
        out += struct.pack(">II", prev_left, prev_right)
    return bytes(out)


def container(key: bytes, metadata: bytes, body: bytes) -> bytes:
    encrypted_metadata = seal(key, literal_stream(metadata), len(metadata))
    encrypted_body = seal(key, literal_stream(body), len(body))
    preheader = (
        b"\x00" + u32(0) + u32(SG_VERSION)
        + b"\x04" + u32(len(encrypted_metadata))
        + b"\x80" + u32(4) + u32(0x7)
        + b"\xFF"
    )
    return preheader + encrypted_metadata + encrypted_body


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("-o", "--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args(argv)

    if not SG_KEYS:
        print("keys.py exports no SG_KEYS; run tools/sg_key_extractor.py first", file=sys.stderr)
        return 1
    payload = container(SG_KEYS[0], b'{"license":"corpus"}', bytecode_body())
    encoded = base64.b64encode(b"\x00" * 12 + payload).decode("ascii")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(f"<?php\nsg_load('{encoded}');\n", encoding="ascii", newline="\n")
    try:
        shown = args.output.relative_to(ROOT)
    except ValueError:
        shown = args.output
    print(f"wrote {shown} ({args.output.stat().st_size} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
