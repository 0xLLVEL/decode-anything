"""Regression tests for the SourceGuardian container decoder.

The cipher and checksum are checked against published values; the container
path is checked against a synthetic container this file seals itself, so it
locks the parser and the ROL1 gate without needing a real encoded fixture.
"""

from __future__ import annotations

import base64
import struct

import pytest

from engines.sourceguardian.container import (
    Blowfish,
    SGError,
    build_candidates,
    cbc_decrypt,
    decode_bytes,
    decrypt_section,
    get_payload,
    lzo1x_decompress,
    parse_metadata,
    parse_preheader,
    rol1,
)

KEY_A = b"A" * 44
KEY_B = b"B" * 44
KEY_C = b"C" * 44
KEYS = (KEY_A, KEY_B, KEY_C)
MAGIC = b"SOURCEGUARDIAN\x00"
METADATA = b'{"license":"test"}'
BODY = MAGIC + struct.pack("<II", 0x21, 0x0007) + b"payload"


def _cbc_encrypt(cipher: Blowfish, data: bytes) -> bytes:
    out = bytearray()
    prev_left = prev_right = 0
    for offset in range(0, len(data) - 7, 8):
        left = int.from_bytes(data[offset:offset + 4], "big") ^ prev_left
        right = int.from_bytes(data[offset + 4:offset + 8], "big") ^ prev_right
        prev_left, prev_right = cipher.encrypt_block(left, right)
        out += struct.pack(">II", prev_left, prev_right)
    return bytes(out)


def _literal_stream(payload: bytes) -> bytes:
    """LZO1X literal-only stream: long first literal run, then the EOF marker."""
    assert 4 <= len(payload) <= 238
    return bytes([17 + len(payload)]) + payload + b"\x11\x00\x00"


def _seal(key: bytes, stream: bytes, declen: int) -> bytes:
    length = 12 + len(stream) + 3
    data = struct.pack("<III", 0, length, declen) + stream + b"\x00\x00\x00"
    checksum = rol1(b"\x00\x00\x00\x00" + data[4:])
    data = struct.pack("<I", checksum) + data[4:]
    data += b"\x00" * ((-len(data)) % 8)
    return _cbc_encrypt(Blowfish(key), data)


def _preheader(metadata_size: int, version: int = 0x21, flags: int = 0x7) -> bytes:
    return (
        b"\x00" + struct.pack("<I", 0) + struct.pack("<I", version)
        + b"\x04" + struct.pack("<I", metadata_size)
        + b"\x80" + struct.pack("<I", 4) + struct.pack("<I", flags)
        + b"\xff"
    )


def _container(key: bytes, metadata: bytes, body: bytes) -> bytes:
    encrypted_metadata = _seal(key, _literal_stream(metadata), len(metadata))
    encrypted_body = _seal(key, _literal_stream(body), len(body))
    return _preheader(len(encrypted_metadata)) + encrypted_metadata + encrypted_body


def _marked_container(key: bytes, metadata: bytes, bodies: list[bytes]) -> bytes:
    encrypted_metadata = _seal(key, _literal_stream(metadata), len(metadata))
    chunks = []
    for index, body in enumerate(bodies):
        sealed = _seal(key, _literal_stream(body), len(body))
        chunks.append(struct.pack("<II", 0x51 + index, len(sealed)) + sealed)
    return (
        _preheader(len(encrypted_metadata))
        + encrypted_metadata
        + b"".join(chunks)
        + b"\x00" * 4
    )


@pytest.mark.parametrize(
    ("key", "plain", "expected"),
    [
        (bytes.fromhex("0000000000000000"), bytes.fromhex("0000000000000000"), "4EF997456198DD78"),
        (bytes.fromhex("FFFFFFFFFFFFFFFF"), bytes.fromhex("FFFFFFFFFFFFFFFF"), "51866FD5B85ECB8A"),
        (bytes.fromhex("0123456789ABCDEF"), bytes.fromhex("1111111111111111"), "61F9C3802281B096"),
        (b"abcdefghijklmnopqrstuvwxyz", b"BLOWFISH", "324ED0FEF413A203"),
    ],
)
def test_blowfish_matches_published_vectors(key: bytes, plain: bytes, expected: str) -> None:
    cipher = Blowfish(key)
    left = int.from_bytes(plain[:4], "big")
    right = int.from_bytes(plain[4:], "big")
    cipher_left, cipher_right = cipher.encrypt_block(left, right)
    assert f"{cipher_left:08X}{cipher_right:08X}" == expected
    assert cipher.decrypt_block(cipher_left, cipher_right) == (left, right)


def test_rol1_rotates_after_every_addition() -> None:
    assert rol1(b"") == 0
    assert rol1(b"\x01") == 2
    assert rol1(b"\x01\x02") == 8
    assert rol1(b"\x01\x02\x03") == 22


def test_lzo_literal_stream_round_trips() -> None:
    assert lzo1x_decompress(_literal_stream(METADATA)) == METADATA
    assert lzo1x_decompress(_literal_stream(BODY)) == BODY


def test_lzo_rejects_truncated_stream() -> None:
    with pytest.raises(SGError):
        lzo1x_decompress(b"")
    with pytest.raises(SGError):
        lzo1x_decompress(bytes([17 + 8]) + b"short")


def test_rol1_gate_rejects_foreign_key() -> None:
    sealed = _seal(KEY_B, _literal_stream(METADATA), len(METADATA))
    assert decrypt_section(KEY_C, sealed, 0) is None
    assert decrypt_section(KEY_A, sealed, 0) is None
    opened = decrypt_section(KEY_B, sealed, 0)
    assert opened is not None
    assert opened[0] == 12 + len(_literal_stream(METADATA)) + 3
    assert opened[1] == len(METADATA)


def test_preheader_fields_are_parsed() -> None:
    buf = _preheader(0x40)
    version, metadata_size, flags, offset = parse_preheader(buf)
    assert (version, metadata_size, flags) == (0x21, 0x40, 0x7)
    assert offset == len(buf)


def test_synthetic_container_decodes_end_to_end() -> None:
    result = decode_bytes(_container(KEY_B, METADATA, BODY), KEYS)
    assert result["key"] == "commercial-key1"
    assert result["metadata"] == METADATA
    assert result["bodies"] == [BODY]
    assert result["version"] == 0x21
    assert result["flags"] == 0x7


def test_marked_body_list_is_walked_until_terminator() -> None:
    bodies = [BODY, MAGIC + struct.pack("<II", 0x21, 0x0007) + b"second"]
    result = decode_bytes(_marked_container(KEY_A, METADATA, bodies), KEYS)
    assert result["key"] == "commercial-key0"
    assert result["metadata"] == METADATA
    assert result["bodies"] == bodies


def test_container_with_unknown_key_is_rejected() -> None:
    buf = _container(b"Z" * 44, METADATA, BODY)
    with pytest.raises(SGError):
        decode_bytes(buf, KEYS)


def test_candidates_cover_commercial_and_eval_modes() -> None:
    candidates = build_candidates(KEYS)
    assert [name for name, _ in candidates[:3]] == [
        "commercial-key0",
        "commercial-key1",
        "commercial-key2",
    ]
    assert len(candidates) == 3 + 253
    assert candidates[3][1][:16] == KEY_B[:16]
    assert len(candidates[3][1]) == 17


def test_metadata_tlv_covers_every_field_kind() -> None:
    meta = (
        b"\x02" + struct.pack("<I", 33) + b"A" * 32 + b"\x00"
        + b"\x03" + struct.pack("<I", 4) + b"1234"
        + b"\x00" + struct.pack("<I", 6) + b"Name\x00\x00"
        + b"\x0a" + struct.pack("<I", 0xDEADBEEF)
        + b"\x01" + b"\x00"
        + b"\x06" + struct.pack("<I", 4) + b"kvWi"
        + b"\xff"
        + b"\x0d" + struct.pack("<I", 2)
        + struct.pack("<I", 4) + b"foo\x00"
        + struct.pack("<I", 4) + b"bar\x00"
        + b"\xff"
    )
    parsed = parse_metadata(meta)
    assert parsed["regkey"] == "A" * 32
    assert parsed["size"] == len(meta)
    machine, policy = parsed["records"]
    assert [(field["tag"], field["kind"]) for field in machine] == [
        (0x03, "bytes"),
        (0x00, "bytes"),
        (0x0A, "fixed4"),
        (0x01, "fixed1"),
        (0x06, "bytes"),
    ]
    assert machine[2]["value"] == 0xDEADBEEF
    assert machine[3]["value"] == 0
    assert policy[0]["items"] == [b"foo\x00", b"bar\x00"]


def test_metadata_rejects_a_missing_terminator() -> None:
    meta = b"\x02" + struct.pack("<I", 33) + b"A" * 32 + b"\x00" + b"\x03"
    with pytest.raises(SGError):
        parse_metadata(meta)


def test_get_payload_strips_machine_prefix(tmp_path) -> None:
    buf = _preheader(0x40)
    encoded = base64.b64encode(b"\x00" * 12 + buf).decode("ascii")
    path = tmp_path / "encoded.php"
    path.write_text(f"<?php // stub\nsg_load('{encoded}') ?>\n", encoding="latin-1")
    assert get_payload(path) == buf
