#!/usr/bin/env python3
"""Regenerate the encoded SourceGuardian corpus fixtures.

Each fixture is a real ``sg_load`` container: Blowfish-CBC over LZO1X, sealed
with the first key in ``engines/sourceguardian/keys.py`` so the normal decode
path can open it. The payloads are minimal PHP 8.1 op_arrays built with the
same primitives the SG unit tests use.

Usage:
    python tools/build_corpus_fixtures.py --name hello
    python tools/build_corpus_fixtures.py --name class -o /tmp/class.php
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

CORPUS = ROOT / "tests" / "corpus" / "sourceguardian"
SG_VERSION = 0x21
PHP_81_RETURN = 62
PHP_81_RECV_INIT = 64
PHP_81_ECHO = 136
ZEND_ACC_PUBLIC = 0x01
ZEND_ACC_STATIC = 0x10
ZEND_ACC_FINAL = 0x20


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
    op2_nibble: int = 0xF,
    payload: bytes = b"",
    lineno: int = 1,
) -> bytes:
    type_word = (0xF << 12) | (0xF << 8) | (op2_nibble << 4) | op1_nibble
    return bytes([number]) + u32(type_word) + payload + u32(lineno)


def op_array(
    *,
    function_name: str = "",
    literals: list[bytes] | None = None,
    opcodes: list[bytes] | None = None,
    num_args: int = 0,
    required_num_args: int = 0,
    arg_names: list[str] | None = None,
) -> bytes:
    literals = literals or []
    opcodes = opcodes or []
    arg_names = arg_names or []

    buf = bytearray()
    buf.append(0xFF)                 # version gate terminator
    buf.append(2)                    # full op_array
    buf.extend(u32(0))               # fn_flags
    buf.extend(b"\x00\x00\x00")
    buf.extend(u32(num_args))
    buf.extend(u32(required_num_args))
    for arg_name in arg_names:
        buf.extend(zstr(arg_name))
        buf.extend(u32(0))           # arg type info
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


def property_record(name: str, flags: int, default: bytes) -> bytes:
    return (
        zstr(name)
        + u32(flags)
        + zstr(None)                 # mangled/typed name
        + zstr(None)                 # doc comment
        + default
        + u32(0)                     # type info
        + u32(0)                     # attributes
    )


def class_record(
    name: str,
    *,
    flags: int = 0,
    properties: list[bytes] | None = None,
    static_properties: int = 0,
    methods: list[tuple[str, bytes]] | None = None,
) -> bytes:
    properties = properties or []
    methods = methods or []

    buf = bytearray()
    buf.append(0xFF)                 # version gate
    buf.append(2)                    # class type
    buf.extend(zstr(name))
    buf.extend(u32(flags))
    buf.extend(zstr(None))           # parent
    buf.extend(u32(0))               # interfaces
    buf.extend(u32(0))               # traits
    buf.extend(u32(0))               # trait aliases
    buf.extend(u32(0))               # trait precedences
    buf.extend(zstr(None))           # doc comment
    buf.extend(u32(0))               # constants
    buf.extend(u32(len(properties)))
    buf.extend(u32(static_properties))
    for prop in properties:
        buf.extend(prop)
    buf.extend(u32(0))               # class attributes
    buf.extend(u32(0))               # trailing flags/line
    buf.extend(u32(0))               # static properties table
    buf.extend(u32(len(methods)))
    for method_name, method_bytes in methods:
        buf.extend(zstr(method_name))
        buf.extend(method_bytes)
    return bytes(buf)


def body(
    *,
    classes: list[bytes] | None = None,
    function: bytes | None = None,
    main: bytes | None = None,
) -> bytes:
    classes = classes or []
    buf = bytearray()
    buf.extend(b"SOURCEGUARDIAN\x00")
    buf.extend(u32(SG_VERSION))
    buf.extend(u32(0))               # flags
    buf.extend(u32(0))
    buf.extend(u32(0))
    if function is not None:
        buf.append(2)                # function tag
        buf.extend(u32(0))           # composite key
        buf.extend(function)
    buf.append(0)                    # end of functions
    for cls in classes:
        buf.append(1)                # class tag
        buf.extend(u32(0))           # composite key
        buf.extend(cls)
    buf.append(0)                    # end of classes
    buf.extend(main or return_one())
    return bytes(buf)


def return_one() -> bytes:
    return op_array(
        literals=[zval_int(1)],
        opcodes=[opcode(PHP_81_RETURN, op1_nibble=3, payload=b"\x00" + u32(0))],
    )


def hello_body() -> bytes:
    main = op_array(
        literals=[zval_string("hello from sourceguardian"), zval_int(1)],
        opcodes=[
            opcode(PHP_81_ECHO, op1_nibble=3, payload=b"\x00" + u32(0)),
            opcode(PHP_81_RETURN, op1_nibble=3, payload=b"\x00" + u32(1)),
        ],
    )
    return body(main=main)


def class_body() -> bytes:
    greet = op_array(
        function_name="greet",
        literals=[zval_string("hello"), zval_int(1)],
        opcodes=[
            opcode(
                PHP_81_RECV_INIT,
                op1_nibble=2,
                op2_nibble=3,
                payload=b"\x00" + u32(1) + b"\x00" + u32(0),
            ),
            opcode(PHP_81_RETURN, op1_nibble=3, payload=b"\x00" + u32(1)),
        ],
        num_args=1,
        required_num_args=0,
        arg_names=["greeting"],
    )
    greeter = class_record(
        "Greeter",
        flags=ZEND_ACC_FINAL,
        properties=[
            property_record("count", ZEND_ACC_PUBLIC | ZEND_ACC_STATIC, zval_int(1)),
            property_record("name", ZEND_ACC_PUBLIC, zval_string("world")),
        ],
        static_properties=1,
        methods=[("greet", greet)],
    )
    return body(classes=[greeter], main=return_one())


CASES = {
    "hello": hello_body,
    "class": class_body,
}


def literal_stream(payload: bytes) -> bytes:
    """LZO1X literal-only stream, including the long-literal form."""
    size = len(payload)
    if size <= 238:
        return bytes([17 + size]) + payload + b"\x11\x00\x00"
    remaining = size - 18
    zeros = remaining // 255
    tail = remaining % 255
    return b"\x00" + (b"\x00" * zeros) + bytes([tail]) + payload + b"\x11\x00\x00"


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


def container(key: bytes, metadata: bytes, raw_body: bytes) -> bytes:
    encrypted_metadata = seal(key, literal_stream(metadata), len(metadata))
    encrypted_body = seal(key, literal_stream(raw_body), len(raw_body))
    preheader = (
        b"\x00" + u32(0) + u32(SG_VERSION)
        + b"\x04" + u32(len(encrypted_metadata))
        + b"\x80" + u32(4) + u32(0x7)
        + b"\xFF"
    )
    return preheader + encrypted_metadata + encrypted_body


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--name", choices=sorted(CASES), default="hello")
    parser.add_argument("-o", "--output", type=Path)
    args = parser.parse_args(argv)
    output = args.output or CORPUS / f"{args.name}.php"

    if not SG_KEYS:
        print("keys.py exports no SG_KEYS; run tools/sg_key_extractor.py first", file=sys.stderr)
        return 1
    payload = container(SG_KEYS[0], b'{"license":"corpus"}', CASES[args.name]())
    encoded = base64.b64encode(b"\x00" * 12 + payload).decode("ascii")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(f"<?php\nsg_load('{encoded}');\n", encoding="ascii", newline="\n")
    try:
        shown = output.relative_to(ROOT)
    except ValueError:
        shown = output
    print(f"wrote {shown} ({output.stat().st_size} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
