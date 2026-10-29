"""Decode and verify the HR+c ionCube header and body used by PHP 8.1-8.4.

This follows the loader 15.5.0 path:

    sub_1007B3D0 -> sub_1007A030 -> sub_1009E160

The body stage validates its framed stream, decrypts it with PRNG type 5
(MT4IC), and inflates the resulting raw DEFLATE stream. Decoding PHP ABI
structures inside the inflated body is handled by a separate stage.
"""

from __future__ import annotations

import argparse
import base64
import json
import re
import struct
import zlib
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path


CUSTOM_B64 = b"0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"
STANDARD_B64 = b"ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789"
VERSION_XOR = 0x2853CEF2
HRC_VERSIONS = {            # v15 container revisions, not PHP ABI identifiers
    0x4FF571B7,
    0x17EFE671,
    0x2A4496DD,
    0x3CCC22E1,
}
FILE_SIZE_XOR = 0x23958CDE
FILE_SIZE_OFFSET = 12321
HEADER_SIZE_XOR = 0x184FF593
HEADER_SIZE_OFFSET = 0x0C21672E


def u32(value: int) -> int:
    return value & 0xFFFFFFFF


def rol8(value: int, bits: int = 3) -> int:
    return ((value << bits) | (value >> (8 - bits))) & 0xFF


def read_u32(data: bytes, offset: int) -> int:
    return struct.unpack_from("<I", data, offset)[0]


def decode_custom_base64(data: bytes) -> bytes:
    compact = b"".join(data.split()).rstrip(b"=")
    pad = (4 - len(compact) % 4) % 4
    compact += b"=" * pad
    translation = bytes.maketrans(CUSTOM_B64, STANDARD_B64)
    return base64.b64decode(compact.translate(translation), validate=False)


def decode_escaped_block(data: bytes, output_size: int) -> bytes:
    output = bytearray()
    position = 0
    while len(output) < output_size:
        if position >= len(data):
            raise ValueError("truncated escaped block")
        value = data[position]
        position += 1
        if value == 0xFF:
            if position >= len(data):
                raise ValueError("truncated escape sequence")
            value = 0x3C if data[position] & 0x80 else 0xFF
            position += 1
        output.append(value)
    return bytes(output)


def update_loader_checksum(checksum: int, data: bytes) -> int:
    """Update the loader's Adler-style checksum."""

    low = checksum & 0xFFFF
    high = checksum >> 16
    position = 0
    while position < len(data):
        end = min(position + 5552, len(data))
        for value in data[position:end]:
            low += value
            high += low
        low %= 0xFFF1
        high %= 0xFFF1
        position = end
    return low | (high << 16)


def loader_checksum(data: bytes) -> int:
    """Header checksum from sub_10074EF0, initialized with 17."""

    return update_loader_checksum(17, data)


@dataclass
class MetaHeader:
    raw_file_size: int
    raw_header_size: int
    seed: int
    logical_file_size: int
    header_size: int


def decode_meta_header(data: bytes) -> MetaHeader:
    decoded = decode_escaped_block(data[:24], 12)
    raw_file_size, raw_header_size, seed = struct.unpack("<III", decoded)
    logical_file_size = u32(
        (raw_file_size ^ seed ^ FILE_SIZE_XOR) - FILE_SIZE_OFFSET
    )
    header_size = u32(
        ((raw_header_size ^ HEADER_SIZE_XOR) - HEADER_SIZE_OFFSET) ^ seed
    )
    return MetaHeader(
        raw_file_size=raw_file_size,
        raw_header_size=raw_header_size,
        seed=seed,
        logical_file_size=logical_file_size,
        header_size=header_size,
    )


@dataclass
class Chunk:
    flag: int
    encoded_size: int
    output_start: int
    output_end: int


def unchunk_header(data: bytes, output_size: int) -> tuple[bytes, int, list[Chunk]]:
    position = 0
    output = bytearray()
    chunks: list[Chunk] = []

    while len(output) < output_size:
        if position + 2 > len(data):
            raise ValueError("truncated chunk header")
        flag = data[position]
        encoded_size = data[position + 1]
        position += 2
        output_start = len(output)

        if flag & 0x80:
            end = position + encoded_size
            if end > len(data):
                raise ValueError("truncated literal chunk")
            output.extend(data[position:end])
            position = end
            if flag & 0x40:
                output.append(0x3C)
        else:
            end = position + 0xE3
            if end > len(data):
                raise ValueError("truncated 0xE3-byte chunk")
            output.extend(data[position:end])
            position = end

        chunks.append(
            Chunk(
                flag=flag,
                encoded_size=encoded_size,
                output_start=output_start,
                output_end=len(output),
            )
        )

    if len(output) != output_size:
        raise ValueError(
            f"chunk stream produced {len(output)} bytes, expected {output_size}"
        )
    return bytes(output), position, chunks


class MT4IC:
    """PRNG type 5 from sub_10091250/sub_10090F30/sub_10091060."""

    COUNT = 0x1000
    MULTIPLIER = 0x10DCD
    CMWC_MULTIPLIER = 0x495E

    def __init__(self, seed: int):
        self.index = self.COUNT - 1
        self.t1 = u32(seed * self.MULTIPLIER + 0x12D687)
        self.t2 = u32(seed)
        for _ in range(seed % 9):
            self.t2 = u32(self.t2 ^ u32(self.t2 << 10))
            self.t2 = u32(self.t2 ^ (self.t2 >> 15))
            self.t2 = u32(self.t2 ^ u32(self.t2 << 4))
            self.t2 = u32(self.t2 ^ (self.t2 >> 13))
        self.carry = seed % self.CMWC_MULTIPLIER
        self.odd_seed = bool(seed & 1)
        self.values: list[int] = []

        for _ in range(self.COUNT):
            self.t1 = u32(self.t1 * self.MULTIPLIER + 0x7B)
            self.t2 = self._round_t2(self.t2)
            self.values.append(u32(self.t1 + self.t2))

    def _round_t2(self, value: int) -> int:
        if self.odd_seed:
            value = u32(value ^ u32(value << 13))
            value = u32(value ^ (value >> 17))
            return u32(value ^ u32(value << 5))
        value = u32(value ^ (value >> 9))
        value = u32(value ^ u32(value << 1))
        return u32(value ^ (value >> 7))

    def _update_entry(self) -> int:
        self.index = (self.index + 1) & (self.COUNT - 1)
        product = (
            self.values[self.index] * self.CMWC_MULTIPLIER + self.carry
        )
        low = product & 0xFFFFFFFF
        high = (product >> 32) & 0xFFFFFFFF
        folded = u32(low + high)

        if folded < high:
            folded = u32(folded + 1)
            high = u32(high + 1)
        if folded == 0xFFFFFFFF:
            folded = 0
            high = u32(high + 1)

        self.carry = high
        value = u32(0xFFFFFFFE - folded)
        self.values[self.index] = value
        return value

    def _update(self) -> None:
        for output_index in range(self.COUNT):
            self.t1 = u32(self.t1 * self.MULTIPLIER + 0x7B)
            self.t2 = self._round_t2(self.t2)
            entry = self._update_entry()
            self.values[output_index] = u32(entry + self.t1 + self.t2)
        self.index = 0

    def get(self) -> int:
        if self.index >= self.COUNT:
            self._update()
        value = self.values[self.index]
        self.index += 1
        return value


@dataclass
class BodyChecksum:
    offset: int
    stored: int
    calculated: int
    matches: bool


@dataclass
class DecodedBody:
    compressed: bytes
    decompressed: bytes
    report: dict[str, object]


def decode_payload_body(
    payload: bytes, body_offset: int, header_version: int
) -> DecodedBody:
    """Reproduce ic_decode_php81_payload/sub_1009DC50 for type-5 bodies."""

    if header_version < 5:
        raise ValueError(
            "this decoder currently implements the type-5 body PRNG only"
        )

    seed_size = 8 if header_version >= 4 else 4
    if body_offset + seed_size > len(payload):
        raise ValueError("truncated body seeds")

    primary_seed = read_u32(payload, body_offset)
    secondary_seed = (
        read_u32(payload, body_offset + 4)
        if header_version >= 4
        else None
    )
    frame_offset = body_offset + seed_size
    position = frame_offset
    checksum = 0
    prng = MT4IC(primary_seed)
    compressed = bytearray()
    checksums: list[BodyChecksum] = []
    event_counts = {
        "encrypted_chunks": 0,
        "literal_bytes": 0,
        "less_than_bytes": 0,
        "checksum_markers": 0,
        "control_markers": 0,
    }

    while position < len(payload):
        if position + 2 > len(payload):
            raise ValueError("truncated body frame header")

        frame_start = position
        flag = payload[position]
        second = payload[position + 1]
        position += 2

        if flag < 0x80:
            encrypted_end = position + second
            if encrypted_end > len(payload):
                raise ValueError("truncated encrypted body chunk")
            checksum = update_loader_checksum(
                checksum, payload[frame_start:encrypted_end]
            )
            for value in payload[position:encrypted_end]:
                compressed.append(value ^ (prng.get() & 0xFF))
            position = encrypted_end
            event_counts["encrypted_chunks"] += 1
            continue

        marker_type = flag & 0xE0
        if marker_type == 0xA0:
            decoded_checksum = bytearray()
            position = frame_start + 1
            while len(decoded_checksum) < 4:
                if position >= len(payload):
                    raise ValueError("truncated body checksum marker")
                value = payload[position]
                position += 1
                if value == 0xFF:
                    if position >= len(payload):
                        raise ValueError("truncated body checksum escape")
                    value = 0x3C if payload[position] & 0x80 else 0xFF
                    position += 1
                decoded_checksum.append(value)
            stored = read_u32(decoded_checksum, 0)
            checksums.append(
                BodyChecksum(
                    offset=frame_start,
                    stored=stored,
                    calculated=checksum,
                    matches=stored == checksum,
                )
            )
            event_counts["checksum_markers"] += 1
            if stored != checksum:
                raise ValueError(
                    "body checksum mismatch at "
                    f"0x{frame_start:X}: stored 0x{stored:08X}, "
                    f"calculated 0x{checksum:08X}"
                )
        elif marker_type in (0x80, 0xC0):
            checksum = update_loader_checksum(
                checksum, payload[frame_start : frame_start + 2]
            )
            if marker_type == 0x80:
                compressed.append(second)
                event_counts["literal_bytes"] += 1
            else:
                compressed.append(0x3C)
                event_counts["less_than_bytes"] += 1
        else:
            event_counts["control_markers"] += 1

    inflater = zlib.decompressobj(wbits=-15)
    decompressed = inflater.decompress(bytes(compressed))
    decompressed += inflater.flush()
    if not inflater.eof:
        raise ValueError("raw DEFLATE body did not reach end-of-stream")
    if inflater.unused_data or inflater.unconsumed_tail:
        raise ValueError("raw DEFLATE body has unconsumed input")

    report: dict[str, object] = {
        "primary_seed": f"0x{primary_seed:08X}",
        "secondary_seed": (
            f"0x{secondary_seed:08X}" if secondary_seed is not None else None
        ),
        "frame_offset": frame_offset,
        "framed_size": len(payload) - frame_offset,
        "compressed_size": len(compressed),
        "decompressed_size": len(decompressed),
        "inflate_eof": inflater.eof,
        "event_counts": event_counts,
        "checksums": [
            {
                "offset": item.offset,
                "stored": f"0x{item.stored:08X}",
                "calculated": f"0x{item.calculated:08X}",
                "matches": item.matches,
            }
            for item in checksums
        ],
        "all_checksums_match": all(item.matches for item in checksums),
    }
    return DecodedBody(
        compressed=bytes(compressed),
        decompressed=decompressed,
        report=report,
    )


def md4(data: bytes) -> bytes:
    """Small MD4 implementation used to avoid an optional crypto dependency."""

    def left_rotate(value: int, bits: int) -> int:
        return u32((value << bits) | (value >> (32 - bits)))

    original_bits = len(data) * 8
    padded = bytearray(data)
    padded.append(0x80)
    while len(padded) % 64 != 56:
        padded.append(0)
    padded.extend(struct.pack("<Q", original_bits))

    a0, b0, c0, d0 = 0x67452301, 0xEFCDAB89, 0x98BADCFE, 0x10325476
    round1_shifts = (3, 7, 11, 19)
    round2_order = (0, 4, 8, 12, 1, 5, 9, 13, 2, 6, 10, 14, 3, 7, 11, 15)
    round2_shifts = (3, 5, 9, 13)
    round3_order = (0, 8, 4, 12, 2, 10, 6, 14, 1, 9, 5, 13, 3, 11, 7, 15)
    round3_shifts = (3, 9, 11, 15)

    for block_offset in range(0, len(padded), 64):
        words = struct.unpack_from("<16I", padded, block_offset)
        a, b, c, d = a0, b0, c0, d0

        for index in range(16):
            f = (b & c) | (~b & d)
            a = left_rotate(u32(a + f + words[index]), round1_shifts[index % 4])
            a, b, c, d = d, a, b, c

        for index, word_index in enumerate(round2_order):
            g = (b & c) | (b & d) | (c & d)
            a = left_rotate(
                u32(a + g + words[word_index] + 0x5A827999),
                round2_shifts[index % 4],
            )
            a, b, c, d = d, a, b, c

        for index, word_index in enumerate(round3_order):
            h = b ^ c ^ d
            a = left_rotate(
                u32(a + h + words[word_index] + 0x6ED9EBA1),
                round3_shifts[index % 4],
            )
            a, b, c, d = d, a, b, c

        a0, b0, c0, d0 = (
            u32(a0 + a),
            u32(b0 + b),
            u32(c0 + c),
            u32(d0 + d),
        )

    return struct.pack("<4I", a0, b0, c0, d0)


@dataclass
class InitialHeader:
    version: int
    minimum_loader_version: int
    obfuscation_flags: int
    private_properties_tag: int
    private_properties_size: int
    private_properties_hex: str
    bytecode_xor_key: int
    owner_key: int
    v6_format_field: int | None
    metadata_schema: int


def parse_initial_header(data: bytes) -> InitialHeader:
    if len(data) < 20:
        raise ValueError("decrypted header is too short")

    version = read_u32(data, 0)
    private_tag = read_u32(data, 12)
    private_size = read_u32(data, 16)
    private_start = 20
    private_end = private_start + private_size
    required = private_end + 12 + (4 if version >= 6 else 0)
    if required > len(data):
        raise ValueError("truncated initial header fields")

    bytecode_xor_key = read_u32(data, private_end)
    owner_key = read_u32(data, private_end + 4)
    position = private_end + 8
    v6_format_field = None
    if version >= 6:
        v6_format_field = read_u32(data, position)
        position += 4

    return InitialHeader(
        version=version,
        minimum_loader_version=read_u32(data, 4),
        obfuscation_flags=read_u32(data, 8),
        private_properties_tag=private_tag,
        private_properties_size=private_size,
        private_properties_hex=data[private_start:private_end].hex(),
        bytecode_xor_key=bytecode_xor_key,
        owner_key=owner_key,
        v6_format_field=v6_format_field,
        metadata_schema=read_u32(data, position),
    )


@dataclass
class HeaderTrailer:
    php_format_id: int
    php_version_code: int
    inferred_php_version: str | None
    php_flags: int
    encoder_generation: int
    encoder_major: int
    encoder_minor: int
    encoder_revision: int
    member_id: int
    owner_key: int
    ip_address: str
    mac_address: str
    is_demo: bool
    padding: int
    evaluation_min_raw: int
    evaluation_max_raw: int
    evaluation_min_unix: int
    evaluation_max_unix: int
    evaluation_min_utc: str
    evaluation_max_utc: str


def parse_header_trailer(data: bytes) -> HeaderTrailer:
    if len(data) < 40:
        raise ValueError("decrypted header is too short for its trailer")
    trailer = data[-40:]
    php_format_id, php_version_code = struct.unpack_from("<HH", trailer, 0)
    inferred_php_version = None
    if 10 <= php_version_code <= 99:
        inferred_php_version = (
            f"{php_version_code // 10}.{php_version_code % 10}"
        )

    evaluation_min_raw = read_u32(trailer, 32)
    evaluation_max_raw = read_u32(trailer, 36)
    evaluation_min_unix = evaluation_min_raw + 1023976199
    evaluation_max_unix = evaluation_max_raw + 83941958

    def utc_timestamp(value: int) -> str:
        return datetime.fromtimestamp(value, timezone.utc).isoformat()

    return HeaderTrailer(
        php_format_id=php_format_id,
        php_version_code=php_version_code,
        inferred_php_version=inferred_php_version,
        php_flags=read_u32(trailer, 4),
        encoder_generation=trailer[8],
        encoder_major=trailer[9],
        encoder_minor=trailer[10],
        encoder_revision=trailer[11],
        member_id=read_u32(trailer, 12),
        owner_key=read_u32(trailer, 16),
        ip_address=".".join(str(value) for value in trailer[20:24]),
        mac_address=":".join(f"{value:02x}" for value in trailer[24:30]),
        is_demo=bool(trailer[30]),
        padding=trailer[31],
        evaluation_min_raw=evaluation_min_raw,
        evaluation_max_raw=evaluation_max_raw,
        evaluation_min_unix=evaluation_min_unix,
        evaluation_max_unix=evaluation_max_unix,
        evaluation_min_utc=utc_timestamp(evaluation_min_unix),
        evaluation_max_utc=utc_timestamp(evaluation_max_unix),
    )


def get_hrc_payload_slice(
    source: bytes, target_php: int | None = None, index: int = 0
) -> tuple[int, bytes]:
    markers = [m.start() for m in re.finditer(b"HR\\+c", source)]
    if not markers:
        raise ValueError("HR+c marker not found")

    selected_idx = index
    if target_php is not None and len(markers) > 1:
        for idx, start in enumerate(markers):
            end = markers[idx + 1] if idx + 1 < len(markers) else None
            chunk = source[start:end] if end else source[start:]
            try:
                p = decode_custom_base64(chunk)
                if len(p) >= 28:
                    m = decode_meta_header(p[4:28])
                    enc_hdr, _, _ = unchunk_header(p[28:], m.header_size)
                    cs = bytes(rol8(v) for v in enc_hdr[-16:])
                    prng = MT4IC(m.seed)
                    dec = bytes(
                        enc_hdr[k] ^ cs[k & 0x0F] ^ (prng.get() & 0xFF)
                        for k in range(m.header_size - 16)
                    )
                    trailer = parse_header_trailer(dec)
                    if trailer.php_version_code == target_php:
                        selected_idx = idx
                        break
            except Exception:
                continue

    if selected_idx >= len(markers):
        raise ValueError(
            f"payload index {selected_idx} out of range (found {len(markers)} payloads)"
        )

    start = markers[selected_idx]
    end = markers[selected_idx + 1] if selected_idx + 1 < len(markers) else None
    return start, (source[start:end] if end else source[start:])


def decode_file(
    path: Path, payload_index: int = 0, target_php: int | None = None
) -> tuple[dict[str, object], bytes]:
    source = path.read_bytes()
    marker_offset, raw_payload = get_hrc_payload_slice(
        source, target_php=target_php, index=payload_index
    )

    payload = decode_custom_base64(raw_payload)
    if len(payload) < 28:
        raise ValueError("decoded payload is too short")

    raw_version = read_u32(payload, 0)
    version = raw_version ^ VERSION_XOR
    if version not in HRC_VERSIONS:
        raise ValueError(f"unexpected HR+c version value 0x{version:08X}")

    meta = decode_meta_header(payload[4:28])
    chunked_header = payload[28:]
    encrypted_header, consumed, chunks = unchunk_header(
        chunked_header, meta.header_size
    )
    transition_offset = 28 + consumed
    if transition_offset + 8 > len(payload):
        raise ValueError("truncated header transition block")
    transition = payload[transition_offset : transition_offset + 8]
    stored_transition_checksum = read_u32(
        decode_escaped_block(transition, 4), 0
    )
    calculated_transition_checksum = loader_checksum(
        payload[4:transition_offset]
    )
    body_offset = transition_offset + 8
    if meta.header_size < 16:
        raise ValueError("header size is smaller than its MD4 trailer")

    checksum = bytes(rol8(value) for value in encrypted_header[-16:])
    prng = MT4IC(meta.seed)
    decrypted = bytes(
        encrypted_header[index]
        ^ checksum[index & 0x0F]
        ^ (prng.get() & 0xFF)
        for index in range(meta.header_size - 16)
    )
    calculated_checksum = md4(decrypted)
    initial = parse_initial_header(decrypted)
    trailer = parse_header_trailer(decrypted)

    report: dict[str, object] = {
        "source": str(path),
        "source_size": len(source),
        "marker_offset": marker_offset,
        "decoded_payload_size": len(payload),
        "logical_size_from_layout": marker_offset + len(payload),
        "raw_version": f"0x{raw_version:08X}",
        "decoded_version": f"0x{version:08X}",
        "meta_header": {
            **asdict(meta),
            "raw_file_size": f"0x{meta.raw_file_size:08X}",
            "raw_header_size": f"0x{meta.raw_header_size:08X}",
            "seed": f"0x{meta.seed:08X}",
        },
        "logical_size_matches": (
            meta.logical_file_size == marker_offset + len(payload)
        ),
        "chunk_bytes_consumed": consumed,
        "chunks": [
            {
                **asdict(chunk),
                "flag": f"0x{chunk.flag:02X}",
            }
            for chunk in chunks
        ],
        "transition_offset": transition_offset,
        "stored_transition_checksum": (
            f"0x{stored_transition_checksum:08X}"
        ),
        "calculated_transition_checksum": (
            f"0x{calculated_transition_checksum:08X}"
        ),
        "transition_checksum_matches": (
            stored_transition_checksum == calculated_transition_checksum
        ),
        "transition_reserved_hex": transition[4:].hex(),
        "body_offset": body_offset,
        "body_size": len(payload) - body_offset,
        "stored_md4": checksum.hex(),
        "calculated_md4": calculated_checksum.hex(),
        "md4_matches": checksum == calculated_checksum,
        "initial_header": {
            **asdict(initial),
            "bytecode_xor_key": f"0x{initial.bytecode_xor_key:08X}",
            "owner_key": f"0x{initial.owner_key:08X}",
        },
        "header_trailer": {
            **asdict(trailer),
            "php_flags": f"0x{trailer.php_flags:08X}",
            "member_id": f"0x{trailer.member_id:08X}",
            "owner_key": f"0x{trailer.owner_key:08X}",
            "evaluation_min_raw": f"0x{trailer.evaluation_min_raw:08X}",
            "evaluation_max_raw": f"0x{trailer.evaluation_max_raw:08X}",
        },
        "owner_key_matches": initial.owner_key == trailer.owner_key,
        "decrypted_header_size": len(decrypted),
    }
    return report, decrypted


def read_encoded_payload(
    path: Path, payload_index: int = 0, target_php: int | None = None
) -> bytes:
    source = path.read_bytes()
    _, raw_payload = get_hrc_payload_slice(
        source, target_php=target_php, index=payload_index
    )
    return decode_custom_base64(raw_payload)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path, help="ionCube-protected PHP file")
    parser.add_argument(
        "--payload-index",
        type=int,
        default=0,
        help="index of HR+c payload in multi-bundle file (default: 0)",
    )
    parser.add_argument(
        "--php-version",
        type=int,
        choices=(81, 82, 83, 84),
        help="target PHP ABI version in multi-bundle file (e.g. 81, 82)",
    )
    parser.add_argument(
        "--header-out",
        type=Path,
        help="write the decrypted header bytes to this file",
    )
    parser.add_argument(
        "--body-compressed-out",
        type=Path,
        help="write the decrypted raw DEFLATE stream to this file",
    )
    parser.add_argument(
        "--body-out",
        type=Path,
        help="write the inflated PHP body stream to this file",
    )
    args = parser.parse_args()

    report, decrypted = decode_file(
        args.input, payload_index=args.payload_index, target_php=args.php_version
    )
    payload = read_encoded_payload(
        args.input, payload_index=args.payload_index, target_php=args.php_version
    )
    body = decode_payload_body(
        payload,
        int(report["body_offset"]),
        int(report["initial_header"]["version"]),
    )
    report["body"] = body.report
    if args.header_out:
        args.header_out.write_bytes(decrypted)
        report["header_output"] = str(args.header_out)
    if args.body_compressed_out:
        args.body_compressed_out.write_bytes(body.compressed)
        report["body_compressed_output"] = str(args.body_compressed_out)
    if args.body_out:
        args.body_out.write_bytes(body.decompressed)
        report["body_output"] = str(args.body_out)
    print(json.dumps(report, indent=2))
    return (
        0
        if report["md4_matches"]
        and report["transition_checksum_matches"]
        and body.report["all_checksums_match"]
        and body.report["inflate_eof"]
        else 1
    )


if __name__ == "__main__":
    raise SystemExit(main())
