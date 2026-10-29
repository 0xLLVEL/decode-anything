"""Static parser for ionCube's serialized PHP 8.1-8.4 opcode blocks.

This module ports the data-oriented part of these loader routines:

    sub_1009B180  read the encoded-word and operand streams
    sub_1009B3C0  rebuild zend_op records
    sub_1009B200  materialize jump targets

It intentionally does not install VM handlers or execute the protected file.
The caller supplies the surrounding zend_op_array metadata and, when opcode
obfuscation is enabled, the already selected per-opcode XOR byte stream.
"""

from __future__ import annotations

import argparse
import json
import re
import struct
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any


ZEND_VM_LAST_OPCODE = 255  # upper bound for raw/handler-lane intermediate byte
U32_MASK = 0xFFFFFFFF

IS_UNUSED = 0
IS_CONST = 1
IS_TMP_VAR = 2
IS_VAR = 4
IS_CV = 8

OPERAND_TYPE_NAMES = {
    IS_UNUSED: "IS_UNUSED",
    IS_CONST: "IS_CONST",
    IS_TMP_VAR: "IS_TMP_VAR",
    IS_VAR: "IS_VAR",
    IS_CV: "IS_CV",
}

# sub_1009B200 cases. Values are one-based serialized opline indexes before
# Zend turns them into pointers or relative byte offsets.
OP1_JUMP_OPCODES = {0x2A, 0xA2}  # JMP, FAST_CALL
OP2_JUMP_OPCODES = {
    0x2B,
    0x2C,
    0x2D,
    0x2E,
    0x2F,
    0x4D,
    0x7D,
    0x97,
    0x98,
    0xA9,
}
EXTENDED_JUMP_OPCODES = {
    0x2D,  # JMPZNZ second branch
    0x4E,  # FE_FETCH_R
    0x7E,  # FE_FETCH_RW
    0xBB,  # SWITCH_LONG default
    0xBC,  # SWITCH_STRING default
    0xC3,  # MATCH default
}

SEND_RESULT_FROM_OP2 = {
    50,
    65,
    66,
    67,
    106,
    116,
    117,
    119,
    120,
    165,
    185,
}


class ParseError(ValueError):
    """Raised when a serialized structure is truncated or inconsistent."""


class ByteReader:
    def __init__(self, data: bytes, offset: int = 0):
        if offset < 0 or offset > len(data):
            raise ParseError(f"invalid initial offset {offset}")
        self.data = data
        self.offset = offset

    @property
    def remaining(self) -> int:
        return len(self.data) - self.offset

    def read(self, size: int) -> bytes:
        if size < 0 or self.offset + size > len(self.data):
            raise ParseError(
                f"need {size} bytes at 0x{self.offset:X}, "
                f"only {self.remaining} remain"
            )
        start = self.offset
        self.offset += size
        return self.data[start : start + size]

    def u8(self) -> int:
        return self.read(1)[0]

    def u32(self) -> int:
        return struct.unpack("<I", self.read(4))[0]

    def i32(self) -> int:
        return struct.unpack("<i", self.read(4))[0]


@dataclass
class OpArrayMetadata:
    last_var: int
    literal_count: int
    fn_flags: int = 0
    line_start: int | None = None
    line_end: int | None = None
    num_args: int | None = None
    required_num_args: int | None = None
    function_name: str | None = None
    filename: str | None = None
    variables: list[str] = field(default_factory=list)

    def validate(self) -> None:
        if self.last_var < 0:
            raise ParseError("last_var cannot be negative")
        if self.literal_count < 0:
            raise ParseError("literal_count cannot be negative")
        if self.variables and len(self.variables) != self.last_var:
            raise ParseError(
                f"metadata has {len(self.variables)} variable names, "
                f"expected {self.last_var}"
            )


@dataclass
class SerializedOpcodeBlock:
    opcode_count: int
    words: list[int]
    auxiliary_records: bytes
    start_offset: int
    end_offset: int

    @classmethod
    def read(cls, reader: ByteReader) -> "SerializedOpcodeBlock":
        """Port sub_1009B180."""

        start = reader.offset
        opcode_count = reader.u32()
        word_count = reader.u32()
        words = list(struct.unpack(f"<{word_count}I", reader.read(4 * word_count)))
        auxiliary_count = reader.u32()
        auxiliary_records = reader.read(5 * auxiliary_count)
        return cls(
            opcode_count=opcode_count,
            words=words,
            auxiliary_records=auxiliary_records,
            start_offset=start,
            end_offset=reader.offset,
        )


@dataclass
class DynamicMainRecord:
    blob: bytes
    metadata: OpArrayMetadata
    temp_variable_count: int
    outer_literal_count: int
    record_flags: int
    blob_tag: int
    start_offset: int
    blob_offset: int
    end_offset: int
    outer_key_words: tuple[int, int] | None = None
    outer_descriptor: "OuterDescriptor | None" = None
    table_name: str | None = None
    layout_words: tuple[int, int, int] | None = None
    arg_type_info: list[dict[str, Any]] | None = None


@dataclass
class OuterDescriptor:
    """Variable-width descriptor read by sub_10002FC0."""

    tag: int
    payload_length: int
    item_lengths: list[int]
    word10: int
    word11: int
    start_offset: int
    end_offset: int


@dataclass
class DynamicMethodRecord:
    """CD30/CB50 dynamic-key method prelude paired with its body blob."""

    method_name: str
    table_name: str | None
    record_start: int
    body_length: int
    body_length_offset: int
    body_offset: int
    body_end: int
    opcode_seed_words: tuple[int, int]
    key_spec_words: tuple[int, int, int]
    descriptor: OuterDescriptor


@dataclass
class InnerOpArrayRecord:
    block: SerializedOpcodeBlock
    metadata: OpArrayMetadata
    raw_metadata_words: list[int]
    metadata_tag: int
    variable_records: bytes
    try_catch_records: bytes
    opcode_data: bytes
    literal_pool: bytes
    literals: list["SerializedLiteral"]
    arg_type_info: list[dict[str, Any]]
    nested_function_count: int
    start_offset: int
    end_offset: int


@dataclass
class SerializedLiteral:
    index: int
    type: int
    type_name: str
    raw_type_info: int
    raw_fields: tuple[int, int, int]
    value: Any = None
    encoded_payload: str | None = None
    string_offset: int | None = None
    string_offset_raw: int | None = None
    string_length: int | None = None
    string_flags: int = 0
    unresolved: str | None = None


@dataclass
class Operand:
    type: int
    type_name: str
    serialized_value: int
    zend_value: int
    literal_index: int | None = None
    variable_index: int | None = None
    variable_name: str | None = None
    jump_target: int | None = None


@dataclass
class DecodedOpcode:
    index: int
    opcode: int
    opcode_name: str | None
    encoded_word: int
    handler_word: int | None
    op1: Operand
    op2: Operand
    result: Operand
    extended_value: int
    lineno: int
    extended_jump_target: int | None = None
    opcode_xor_byte: int | None = None
    opcode_raw: int | None = None
    handler_key_dword: int | None = None
    handler_index: int | None = None
    handler_variant: int | None = None
    handler_candidates: list[int] = field(default_factory=list)
    opcode_source: str = "serialized"
    warnings: list[str] = field(default_factory=list)


@dataclass
class DecodedOpcodeBlock:
    metadata: OpArrayMetadata
    opcodes: list[DecodedOpcode]
    encoded_word_count: int
    auxiliary_record_count: int
    consumed_words: int
    consumed_auxiliary_records: int
    start_offset: int
    end_offset: int

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class RawOpcodeEntry:
    index: int
    encoded_opcode_byte: int
    encoded_word: int
    lineno: int
    op1: Operand
    op2: Operand
    result: Operand
    extended_value: int


@dataclass
class RawOpcodeBlock:
    metadata: OpArrayMetadata
    opcode_count: int
    encoded_word_count: int
    auxiliary_record_count: int
    entries: list[RawOpcodeEntry]
    consumed_words: int
    consumed_auxiliary_records: int


@dataclass
class OpcodeXorStream:
    """Static C3D0/B3C0 opcode-byte material for supported v15 streams."""

    request_key: int
    seed_a: int
    seed_b: int
    descriptor_delta: int
    key_bytes: bytes
    xor_bytes: bytes
    raw_opcode_bytes: bytes
    decoded_opcode_bytes: bytes
    source: str = "sub_1009C3D0/sub_1009B3C0 opcode_raw"


class LoaderHandlerTables:
    """Versioned static handler tables for the supported PHP 8.1-8.4 loaders."""

    # PHP 8.1 loader 15.5.0 (sub_1001ACC0 / sub_10070050)
    VARIANT_TABLES = (
        (0x100E2C00, 0x100B2BA0),
        (0x101664E0, 0x100F2C00),
        (0x100A2830, 0x100D2C00),
        (0x10176528, 0x10132E28),
        (0x10102C00, 0x100C2BA0),
        (0x10112C20, 0x10156450),
        (0x10122C90, 0x10142E28),
    )
    OPCODE_HANDLER_META = 0x100B2830
    OPCODE_META_ID      = 0x10132CB0
    TYPE_DIMENSION_TABLE= 0x100A280C
    GLOBAL_FEATURE_WORD = 0x100A26BC

    # PHP 8.2 loader — extracted from ioncube_loader_win_8.2.dll
    # sub_1001BFE0 (decode_handler_index) / sub_100725F0 (_select_handler_index)
    VARIANT_TABLES_82 = (
        (0x100E6CF0, 0x100B6C90),
        (0x1016A5E0, 0x100F6CF0),
        (0x100A6850, 0x100D6CF0),
        (0x1017A628, 0x10136F18),
        (0x10106CF0, 0x100C6C90),
        (0x10116D10, 0x1015A570),
        (0x10126D80, 0x10146F18),
    )
    OPCODE_HANDLER_META_82 = 0x100B6850
    OPCODE_META_ID_82      = 0x10136DA0
    TYPE_DIMENSION_TABLE_82= 0x100A682C
    GLOBAL_FEATURE_WORD_82 = 0x100A66C8  # zend_observer_fcall_op_array_extension

    # PHP 8.3 loader — extracted from ioncube_loader_win_8.3.dll
    # sub_1001CEC0 (decode_handler_index) / sub_10074540 (_select_handler_index)
    VARIANT_TABLES_83 = (
        (0x100E8D10, 0x100B8CB0),
        (0x1016C658, 0x100F8D10),
        (0x100A8870, 0x100D8D10),
        (0x1017C6A0, 0x10138F38),
        (0x10108D10, 0x100C8CB0),
        (0x10118D30, 0x1015C5C0),
        (0x10128DA0, 0x10148F38),
    )
    OPCODE_HANDLER_META_83 = 0x100B8870
    OPCODE_META_ID_83      = 0x10138DC0
    TYPE_DIMENSION_TABLE_83= 0x100A884C
    GLOBAL_FEATURE_WORD_83 = 0x100A86E0  # zend_observer_fcall_op_array_extension

    # PHP 8.4 loader — extracted from ioncube_loader_win_8.4.dll
    # sub_1001E5F0 (decode_handler_index) / sub_1007D570 (_select_handler_index)
    VARIANT_TABLES_84 = (
        (0x100F3D58, 0x100C3CF8),
        (0x101776D0, 0x10103D58),
        (0x100B3890, 0x100E3D58),
        (0x10187738, 0x10143FB8),
        (0x10113D58, 0x100D3CF8),
        (0x10123D78, 0x10167668),
        (0x10133E00, 0x10153FB8),
    )
    OPCODE_HANDLER_META_84 = 0x100C3890
    OPCODE_META_ID_84      = 0x10143E20
    TYPE_DIMENSION_TABLE_84= 0x100C3C90
    GLOBAL_FEATURE_WORD_84 = 0x100B3714  # zend_observer_fcall_op_array_extension

    # 64-bit loaders shipped in this repo use image base 0x180000000 and a
    # different layout. Addresses below are RVAs so they follow the PE image
    # base instead of assuming the old 32-bit 0x10000000 base.
    TABLES_BY_VERSION_X64_RVA: "dict[int, dict]" = {
        81: {
            "VARIANT_TABLES": (
                (0x0F54A0, 0x0C53E0),
                (0x17C490, 0x1054A0),
                (0x0B5000, 0x0E54A0),
                (0x18C510, 0x1457A0),
                (0x1154A0, 0x0D53E0),
                (0x1254E0, 0x16C3F0),
                (0x1355A0, 0x1557A0),
            ),
            "OPCODE_HANDLER_META":   0x0C5000,
            "OPCODE_META_ID":        0x1455E0,
            "TYPE_DIMENSION_TABLE":  0x0C5330,
            "GLOBAL_FEATURE_WORD":   0x0B4DA0,
            "last_opcode":           202,
        },
        82: {
            "VARIANT_TABLES": (
                (0x1045C0, 0x0D4500),
                (0x18B5B0, 0x1145C0),
                (0x0C4050, 0x0F45C0),
                (0x19B630, 0x1548C0),
                (0x1245C0, 0x0E4500),
                (0x134600, 0x17B500),
                (0x1446C0, 0x1648C0),
            ),
            "OPCODE_HANDLER_META":   0x0D4050,
            "OPCODE_META_ID":        0x154700,
            "TYPE_DIMENSION_TABLE":  0x0D4450,
            "GLOBAL_FEATURE_WORD":   0x0C3DB8,
            "last_opcode":           202,
        },
        83: {
            "VARIANT_TABLES": (
                (0x1075F0, 0x0D7530),
                (0x18E6C0, 0x1175F0),
                (0x0C7080, 0x0F75F0),
                (0x19E740, 0x157900),
                (0x1275F0, 0x0E7530),
                (0x137630, 0x17E610),
                (0x1476F0, 0x167900),
            ),
            "OPCODE_HANDLER_META":   0x0D7080,
            "OPCODE_META_ID":        0x157730,
            "TYPE_DIMENSION_TABLE":  0x0D7480,
            "GLOBAL_FEATURE_WORD":   0x0C6DE8,
            "last_opcode":           203,
        },
        84: {
            "VARIANT_TABLES": (
                (0x10D670, 0x0DD5B0),
                (0x194810, 0x11D670),
                (0x0CD100, 0x0FD670),
                (0x1A48D0, 0x15D9F0),
                (0x12D670, 0x0ED5B0),
                (0x13D6B0, 0x184750),
                (0x14D7A0, 0x16D9F0),
            ),
            "OPCODE_HANDLER_META":   0x0DD100,
            "OPCODE_META_ID":        0x15D7E0,
            "TYPE_DIMENSION_TABLE":  0x0DD500,
            "GLOBAL_FEATURE_WORD":   0x0CCDE8,
            "last_opcode":           209,
        },
    }

    TABLES_BY_VERSION: "dict[int, dict]" = {}  # populated after class definition

    def __init__(self, image: bytes, image_base: int, php_version: int = 81):
        self.image = image
        self.image_base = image_base
        if image_base == 0x180000000:
            profile = self.TABLES_BY_VERSION_X64_RVA.get(php_version)
            if profile is None:
                raise ParseError(
                    f"no 64-bit handler tables for PHP {php_version // 10}.{php_version % 10}"
                )
            self.VARIANT_TABLES = tuple(
                (image_base + table_a, image_base + table_b)
                for table_a, table_b in profile["VARIANT_TABLES"]
            )
            self.OPCODE_HANDLER_META = image_base + profile["OPCODE_HANDLER_META"]
            self.OPCODE_META_ID = image_base + profile["OPCODE_META_ID"]
            self.TYPE_DIMENSION_TABLE = image_base + profile["TYPE_DIMENSION_TABLE"]
            self.GLOBAL_FEATURE_WORD = image_base + profile["GLOBAL_FEATURE_WORD"]
            self.last_opcode = profile["last_opcode"]
        else:
            t = self.TABLES_BY_VERSION.get(php_version, {})
            self.VARIANT_TABLES       = t.get("VARIANT_TABLES",        self.__class__.VARIANT_TABLES)
            self.OPCODE_HANDLER_META  = t.get("OPCODE_HANDLER_META",   self.__class__.OPCODE_HANDLER_META)
            self.OPCODE_META_ID       = t.get("OPCODE_META_ID",        self.__class__.OPCODE_META_ID)
            self.TYPE_DIMENSION_TABLE = t.get("TYPE_DIMENSION_TABLE",  self.__class__.TYPE_DIMENSION_TABLE)
            self.GLOBAL_FEATURE_WORD  = t.get("GLOBAL_FEATURE_WORD",   self.__class__.GLOBAL_FEATURE_WORD)
            # PHP 8.1/8.2 use opcodes 0-202 unless a version profile overrides it.
            self.last_opcode          = t.get("last_opcode", 202)
        self.global_feature_word  = self.u32(self.GLOBAL_FEATURE_WORD)

    @classmethod
    def from_dll(cls, path: Path, php_version: int = 81) -> "LoaderHandlerTables":
        try:
            import pefile  # type: ignore[import-not-found]
        except ImportError as exc:
            raise ParseError(
                "pefile is required for static handler-lane decoding"
            ) from exc

        pe = pefile.PE(str(path))
        return cls(
            image=pe.get_memory_mapped_image(),
            image_base=pe.OPTIONAL_HEADER.ImageBase,
            php_version=php_version,
        )

    def _offset(self, address: int, size: int) -> int:
        offset = address - self.image_base
        if offset < 0 or offset + size > len(self.image):
            raise ParseError(f"loader table address 0x{address:X} is outside image")
        return offset

    def u8(self, address: int) -> int:
        return self.image[self._offset(address, 1)]

    def u16(self, address: int) -> int:
        return struct.unpack_from("<H", self.image, self._offset(address, 2))[0]

    def u32(self, address: int) -> int:
        return struct.unpack_from("<I", self.image, self._offset(address, 4))[0]

    def _word_at(self, base: int, index: int) -> int:
        return self.u16(base + 2 * index)

    def _dword_at(self, base: int, index: int) -> int:
        return self.u32(base + 4 * index)

    def decode_handler_index(
        self,
        handler_word: int,
        handler_key_dword: int,
        variant: int,
    ) -> int:
        """Port sub_1001ACC0 for variants 0..6."""

        if variant < 0 or variant >= len(self.VARIANT_TABLES):
            raise ParseError(f"unsupported handler table variant {variant}")
        selector = handler_key_dword & 7
        mixed_low = (handler_word ^ handler_key_dword) & 0xFFFF
        table_index = (selector << 12) + mixed_low
        table_a, table_b = self.VARIANT_TABLES[variant]
        return self._word_at(table_a, table_index) ^ self._word_at(
            table_b, table_index
        )

    def _type_dimension(self, operand_type: int) -> int:
        return self._dword_at(self.TYPE_DIMENSION_TABLE, operand_type & 0xFF)

    def _select_handler_index(
        self,
        flags: int,
        opline: DecodedOpcode,
        next_opline: DecodedOpcode | None,
    ) -> int:
        """Port sub_10070050 for the zend_op fields represented statically."""

        selector = 0
        if flags & 0x10000:
            selector = self._type_dimension(opline.op1.type)
        if flags & 0x20000:
            selector = selector * 5 + self._type_dimension(opline.op2.type)

        if not flags & 0xFFFC0000:
            return (flags & 0xFFFF) + selector

        if flags & 0x80000:
            selector = (1 if opline.result.type else 0) + selector * 2
            if flags & 0x2000000 and self.global_feature_word != 0xFFFFFFFF:
                selector += 2
            return (flags & 0xFFFF) + selector

        if flags & 0x100000:
            selector = (
                1
                if 0x0C >= (opline.op2.serialized_value & U32_MASK)
                else 0
            ) + selector * 2
            return (flags & 0xFFFF) + selector

        if flags & 0x40000:
            # sub_10070050 reads byte [opline + 0x35]. With 0x1c-byte
            # serialized zend_op records, that is next_opline->op1_type.
            next_op1_type = next_opline.op1.type if next_opline else 0
            selector = selector * 5 + self._type_dimension(next_op1_type)
            return (flags & 0xFFFF) + selector

        if flags & 0x1000000:
            selector = (opline.extended_value & 1) + selector * 2
            return (flags & 0xFFFF) + selector

        if flags & 0x200000:
            selector *= 3
            result_type = opline.result.type & 0xFF
            if result_type == 0x12:
                selector += 1
            elif result_type == 0x22:
                selector += 2
            return (flags & 0xFFFF) + selector

        if flags & 0x2000000:
            selector *= 2
            if self.global_feature_word != 0xFFFFFFFF:
                selector += 1

        return (flags & 0xFFFF) + selector

    def opcode_handler_index(
        self,
        opcode: int,
        opline: DecodedOpcode,
        next_opline: DecodedOpcode | None,
    ) -> int:
        meta_id = self.u8(self.OPCODE_META_ID + opcode)
        flags = self._dword_at(self.OPCODE_HANDLER_META, meta_id)
        return self._select_handler_index(flags, opline, next_opline)

    def opcode_candidates_for_handler_index(
        self,
        handler_index: int,
        opline: DecodedOpcode,
        next_opline: DecodedOpcode | None,
    ) -> list[int]:
        candidates: list[int] = []
        for opcode in range(self.last_opcode + 1):
            if self.opcode_handler_index(opcode, opline, next_opline) == handler_index:
                candidates.append(opcode)
        return candidates


LoaderHandlerTables.TABLES_BY_VERSION = {
    81: {
        "VARIANT_TABLES":        LoaderHandlerTables.VARIANT_TABLES,
        "OPCODE_HANDLER_META":   LoaderHandlerTables.OPCODE_HANDLER_META,
        "OPCODE_META_ID":        LoaderHandlerTables.OPCODE_META_ID,
        "TYPE_DIMENSION_TABLE":  LoaderHandlerTables.TYPE_DIMENSION_TABLE,
        "GLOBAL_FEATURE_WORD":   LoaderHandlerTables.GLOBAL_FEATURE_WORD,
        "last_opcode":           202,
    },
    82: {
        "VARIANT_TABLES":        LoaderHandlerTables.VARIANT_TABLES_82,
        "OPCODE_HANDLER_META":   LoaderHandlerTables.OPCODE_HANDLER_META_82,
        "OPCODE_META_ID":        LoaderHandlerTables.OPCODE_META_ID_82,
        "TYPE_DIMENSION_TABLE":  LoaderHandlerTables.TYPE_DIMENSION_TABLE_82,
        "GLOBAL_FEATURE_WORD":   LoaderHandlerTables.GLOBAL_FEATURE_WORD_82,
        "last_opcode":           202,
    },
    83: {
        "VARIANT_TABLES":        LoaderHandlerTables.VARIANT_TABLES_83,
        "OPCODE_HANDLER_META":   LoaderHandlerTables.OPCODE_HANDLER_META_83,
        "OPCODE_META_ID":        LoaderHandlerTables.OPCODE_META_ID_83,
        "TYPE_DIMENSION_TABLE":  LoaderHandlerTables.TYPE_DIMENSION_TABLE_83,
        "GLOBAL_FEATURE_WORD":   LoaderHandlerTables.GLOBAL_FEATURE_WORD_83,
        "last_opcode":           203,
    },
    84: {
        "VARIANT_TABLES":        LoaderHandlerTables.VARIANT_TABLES_84,
        "OPCODE_HANDLER_META":   LoaderHandlerTables.OPCODE_HANDLER_META_84,
        "OPCODE_META_ID":        LoaderHandlerTables.OPCODE_META_ID_84,
        "TYPE_DIMENSION_TABLE":  LoaderHandlerTables.TYPE_DIMENSION_TABLE_84,
        "GLOBAL_FEATURE_WORD":   LoaderHandlerTables.GLOBAL_FEATURE_WORD_84,
        "last_opcode":           209,
    },
}


def decode_loader_static_string_entry(raw: bytes, key: bytes) -> str:
    """Decode one length-prefixed entry from the loader interned-string table."""

    if not raw:
        raise ParseError("empty loader static-string entry")
    if len(key) < 16:
        raise ParseError("loader static-string XOR key must contain 16 bytes")
    length = raw[0]
    if len(raw) < length + 2:
        raise ParseError(
            f"loader static-string entry needs {length + 2} bytes, "
            f"got {len(raw)}"
        )
    decoded = bytearray(raw[: length + 2])
    for index in range(length + 1):
        decoded[1 + index] ^= key[(length + index) & 0xF]
    if decoded[1 + length] != 0:
        raise ParseError("decoded loader static-string entry is not NUL-terminated")
    return bytes(decoded[1 : 1 + length]).decode("utf-8", errors="replace")


class LoaderInternedStringResolver:
    """Resolve negative literal string offsets through the loader string table."""

    # PHP 8.1 loader (sub_100804F0 / sub_10093C40)
    STRING_XOR_KEY = 0x10186690
    STRING_POINTER_TABLE = 0x101866C8

    # PHP 8.2 loader (sub_100804F0 / sub_10093C40 equivalent)
    STRING_XOR_KEY_82 = 0x1018A790
    STRING_POINTER_TABLE_82 = 0x1018A7C8

    # PHP 8.3 loader (sub_10082550 / unk_1018C840)
    # Key bytes identical to PHP 8.2; table offset differs (+0x30 from key)
    STRING_XOR_KEY_83 = 0x1018C810
    STRING_POINTER_TABLE_83 = 0x1018C840

    # PHP 8.4 loader (sub_1008B870 / sub_100A0C30)
    # Key bytes remain unchanged; this build uses +0x38 table alignment.
    STRING_XOR_KEY_84 = 0x101978B0
    STRING_POINTER_TABLE_84 = 0x101978E8

    # 64-bit loader RVAs (image base 0x180000000). The 16-byte XOR key is
    # unchanged; pointer tables use 8-byte entries instead of 4-byte entries.
    STRING_TABLES_X64_RVA: "dict[int, tuple[int, int]]" = {
        81: (0x19C6C0, 0x19C6F0),
        82: (0x1AB7D0, 0x1AB810),
        83: (0x1AE8E0, 0x1AE910),
        84: (0x1B4A90, 0x1B4AD0),
    }

    def __init__(
        self,
        image: bytes,
        image_base: int,
        php_version: int = 81,
        pointer_size: int = 4,
    ):
        self.image = image
        self.image_base = image_base
        self.pointer_size = pointer_size
        if pointer_size == 8:
            offsets = self.STRING_TABLES_X64_RVA.get(php_version)
            if offsets is None:
                raise ParseError(
                    f"no 64-bit string tables for PHP {php_version // 10}.{php_version % 10}"
                )
            key_rva, table_rva = offsets
            key_addr = image_base + key_rva
            self._table_addr = image_base + table_rva
        elif php_version == 84:
            key_addr = self.STRING_XOR_KEY_84
            self._table_addr = self.STRING_POINTER_TABLE_84
        elif php_version == 83:
            key_addr = self.STRING_XOR_KEY_83
            self._table_addr = self.STRING_POINTER_TABLE_83
        elif php_version == 82:
            key_addr = self.STRING_XOR_KEY_82
            self._table_addr = self.STRING_POINTER_TABLE_82
        else:
            key_addr = self.STRING_XOR_KEY
            self._table_addr = self.STRING_POINTER_TABLE
        self.key = self.read(key_addr, 16)

    @classmethod
    def from_dll(cls, path: Path, php_version: int = 81) -> "LoaderInternedStringResolver":
        try:
            import pefile  # type: ignore[import-not-found]
        except ImportError as exc:
            raise ParseError(
                "pefile is required for loader interned-string decoding"
            ) from exc

        pe = pefile.PE(str(path))
        return cls(
            image=pe.get_memory_mapped_image(),
            image_base=pe.OPTIONAL_HEADER.ImageBase,
            php_version=php_version,
            pointer_size=8 if pe.FILE_HEADER.Machine == 0x8664 else 4,
        )

    def _offset(self, address: int, size: int) -> int:
        offset = address - self.image_base
        if offset < 0 or offset + size > len(self.image):
            raise ParseError(f"loader table address 0x{address:X} is outside image")
        return offset

    def read(self, address: int, size: int) -> bytes:
        offset = self._offset(address, size)
        return self.image[offset : offset + size]

    def u8(self, address: int) -> int:
        return self.read(address, 1)[0]

    def u32(self, address: int) -> int:
        return struct.unpack("<I", self.read(address, 4))[0]

    def read_pointer(self, address: int) -> int:
        if self.pointer_size == 8:
            return struct.unpack("<Q", self.read(address, 8))[0]
        return self.u32(address)

    def decode_ref(self, signed_offset: int, expected_length: int | None = None) -> str | None:
        """Resolve offsets handled by sub_100906D0's static table branch."""

        if signed_offset >= -2:
            return None
        pointer = self.read_pointer(
            self._table_addr + self.pointer_size * (-signed_offset)
        )
        if pointer == 0:
            return None
        length = self.u8(pointer)
        raw = self.read(pointer, length + 2)
        decoded = decode_loader_static_string_entry(raw, self.key)
        if expected_length is not None and len(decoded) != expected_length:
            raise ParseError(
                "loader static-string length mismatch for "
                f"{signed_offset}: expected {expected_length}, got {len(decoded)}"
            )
        return decoded


def resolve_interned_literal_strings(
    literals: list[SerializedLiteral],
    resolver: LoaderInternedStringResolver,
) -> None:
    """Fill literal values for negative string offsets using loader tables."""

    for literal in literals:
        if literal.value is not None or literal.string_offset_raw is None:
            continue
        signed_offset = struct.unpack(
            "<i",
            struct.pack("<I", literal.string_offset_raw),
        )[0]
        try:
            decoded = resolver.decode_ref(signed_offset, literal.string_length)
        except ParseError:
            continue
        if decoded is not None:
            literal.value = decoded
            literal.unresolved = None


def resolve_interned_type_names(
    arg_type_info: list[dict[str, Any]],
    resolver: LoaderInternedStringResolver,
) -> None:
    """Fill class-typed arg/return type names from loader static strings."""

    for info in arg_type_info:
        if not isinstance(info, dict):
            continue
        ref = info.get("class_ref")
        if ref is None or not isinstance(ref, int) or info.get("class_name"):
            continue
        try:
            name = resolver.decode_ref(ref)
        except ParseError:
            continue
        if name:
            info["class_name"] = name


def _format_operand(operand: Operand) -> str:
    details = [operand.type_name, f"raw={operand.serialized_value}"]
    if operand.literal_index is not None:
        details.append(f"lit={operand.literal_index}")
    if operand.variable_index is not None:
        details.append(f"var={operand.variable_index}")
    if operand.variable_name:
        details.append(f"name=${operand.variable_name}")
    if operand.jump_target is not None:
        details.append(f"jmp={operand.jump_target}")
    if operand.zend_value != operand.serialized_value:
        details.append(f"zend={operand.zend_value}")
    return "<" + ", ".join(details) + ">"


def render_opcode_text(decoded: DecodedOpcodeBlock) -> str:
    """Render a small, stable text dump for human inspection."""

    metadata = decoded.metadata
    lines = [
        "ionCube PHP 8.1-8.4 static opcode dump",
        f"opcodes: {len(decoded.opcodes)}",
        f"encoded_words: {decoded.encoded_word_count}",
        f"aux_records: {decoded.auxiliary_record_count}",
        f"last_var: {metadata.last_var}",
        f"literal_count: {metadata.literal_count}",
        f"fn_flags: 0x{metadata.fn_flags:08X}",
    ]
    if any(op.opcode_source == "handler_lane" for op in decoded.opcodes):
        lines.append(
            "opcode_source: handler_lane "
            "(true Zend opcode resolved from loader handler tables)"
        )
    elif any(op.opcode_source.startswith("opcode_raw") for op in decoded.opcodes):
        lines.append(
            "opcode_source: opcode_raw "
            "(handler-lane opcode decode is a separate stage)"
        )
    if metadata.line_start is not None or metadata.line_end is not None:
        lines.append(f"lines: {metadata.line_start}..{metadata.line_end}")
    if metadata.variables:
        lines.append("variables:")
        for index, name in enumerate(metadata.variables):
            lines.append(f"  {index:04d}: ${name}")
    lines.append("")
    lines.append("idx   line   opcode name                         operands")
    lines.append("----  -----  ------ ---------------------------- ----------------")
    for op in decoded.opcodes:
        name = op.opcode_name or f"OP_{op.opcode}"
        operands = (
            f"op1={_format_operand(op.op1)} "
            f"op2={_format_operand(op.op2)} "
            f"res={_format_operand(op.result)} "
            f"ext={op.extended_value}"
        )
        if op.extended_jump_target is not None:
            operands += f" ext_jmp={op.extended_jump_target}"
        if op.opcode_raw is not None and op.opcode_raw != op.opcode:
            operands += f" raw_opcode={op.opcode_raw}"
        if op.warnings:
            operands += " warnings=[" + "; ".join(op.warnings) + "]"
        lines.append(
            f"{op.index:04d}  {op.lineno:5d}  {op.opcode:6d} "
            f"{name:<28} {operands}"
        )
    return "\n".join(lines) + "\n"


def render_dynamic_stage_text(
    outer: DynamicMainRecord,
    *,
    inner_error: Exception | None = None,
    inner_method: str | None = None,
    inner: InnerOpArrayRecord | None = None,
    opcode_xor_stream: OpcodeXorStream | None = None,
    handler_opcode_state: str | None = None,
    opcode_error: Exception | None = None,
    raw_block: RawOpcodeBlock | None = None,
) -> str:
    lines = [
        "ionCube PHP 8.1-8.4 static stage report",
        "stage: dynamic outer record",
        f"outer_offset: 0x{outer.start_offset:X}",
        f"inner_blob_offset: 0x{outer.blob_offset:X}",
        f"inner_blob_size: {len(outer.blob)}",
        f"inner_blob_first16: {outer.blob[:16].hex()}",
    ]
    if outer.outer_key_words is not None:
        lines.append(
            "outer_key_words: "
            f"0x{outer.outer_key_words[0]:08X}, "
            f"0x{outer.outer_key_words[1]:08X}"
        )
    lines.extend(
        [
            f"last_var: {outer.metadata.last_var}",
            f"T: {outer.temp_variable_count}",
            f"literal_count: {outer.outer_literal_count}",
            f"fn_flags: 0x{outer.metadata.fn_flags:08X}",
            f"record_flags: 0x{outer.record_flags:02X}",
            f"blob_tag: 0x{outer.blob_tag:08X}",
        ]
    )
    if outer.metadata.variables:
        lines.append("variables:")
        for index, name in enumerate(outer.metadata.variables):
            lines.append(f"  {index:04d}: ${name}")
    if inner_error is not None:
        lines.extend(
            [
                "",
                "inner_blob_state: encrypted-or-not-yet-transformed",
                f"reason: {type(inner_error).__name__}: {inner_error}",
                "next_static_routine: sub_10002C50 -> sub_10003860 -> sub_10001D20",
            ]
        )
    if inner is not None:
        lines.extend(
            [
                "",
                "inner_blob_state: decrypted",
                f"inner_decryption: {inner_method or 'none'}",
                f"metadata_tag: {inner.metadata_tag}",
                f"inner_last_var: {inner.metadata.last_var}",
                f"inner_literal_count: {inner.metadata.literal_count}",
                f"inner_lines: {inner.metadata.line_start}..{inner.metadata.line_end}",
                f"b180_offset: 0x{inner.block.start_offset:X}",
                f"b180_end: 0x{inner.block.end_offset:X}",
                f"opcode_count: {inner.block.opcode_count}",
                f"encoded_word_count: {len(inner.block.words)}",
                f"aux_record_count: {len(inner.block.auxiliary_records) // 5}",
                f"remaining_inner_bytes: {len(outer.blob) - inner.end_offset}",
            ]
        )
    if opcode_error is not None:
        lines.extend(
            [
                "",
                "opcode_decode_state: blocked-at-per-opline-xor",
                f"reason: {type(opcode_error).__name__}: {opcode_error}",
                "next_static_routine: sub_1009C3D0 -> sub_10090A80 -> sub_1009B3C0 opcode_xor",
            ]
        )
    if opcode_xor_stream is not None:
        lines.extend(
            [
                "",
                "opcode_decode_state: opcode-raw-static",
                f"opcode_key_source: {opcode_xor_stream.source}",
                f"opcode_seed_words: 0x{opcode_xor_stream.seed_a:08X}, "
                f"0x{opcode_xor_stream.seed_b:08X}",
                f"request_key: 0x{opcode_xor_stream.request_key:08X}",
                f"opcode_stream_delta: {opcode_xor_stream.descriptor_delta}",
                f"opcode_xor_count: {len(opcode_xor_stream.xor_bytes)}",
                "handler_opcode_state: "
                + (
                    handler_opcode_state
                    if handler_opcode_state is not None
                    else (
                        "pending sub_10070170/sub_10070050 handler-lane "
                        "decode; opcode field is opcode_raw"
                    )
                ),
            ]
        )
    if raw_block is not None:
        lines.extend(
            [
                "",
                "raw_b180_stream:",
                "idx   line   enc_op  encoded_word  operands",
                "----  -----  ------  ------------  ----------------",
            ]
        )
        for entry in raw_block.entries[:200]:
            operands = (
                f"op1={_format_operand(entry.op1)} "
                f"op2={_format_operand(entry.op2)} "
                f"res={_format_operand(entry.result)} "
                f"ext={entry.extended_value}"
            )
            lines.append(
                f"{entry.index:04d}  {entry.lineno:5d}  "
                f"0x{entry.encoded_opcode_byte:02X}    "
                f"0x{entry.encoded_word:08X}  {operands}"
            )
        if len(raw_block.entries) > 200:
            lines.append(
                f"... truncated raw_b180_stream at 200/{len(raw_block.entries)} entries"
            )
    return "\n".join(lines) + "\n"


def u32(value: int) -> int:
    return value & U32_MASK


def rol32(value: int, bits: int) -> int:
    value &= U32_MASK
    return ((value << bits) | (value >> (32 - bits))) & U32_MASK


def _signed_byte(value: int) -> int:
    return value - 0x100 if value & 0x80 else value


def hash_10006680(data: bytes) -> int:
    """Port sub_10006680, used by cipher type 0 key setup."""

    state = 0
    for value in data:
        mixed = u32(1025 * u32(state + _signed_byte(value)))
        state = u32((mixed >> 6) ^ mixed)
    mixed = u32(9 * state)
    return u32(32769 * (mixed ^ (mixed >> 11)))


def hash_100066c0(data: bytes) -> int:
    """Port sub_100066C0, a MurmurHash3 x86-32 style hash with seed 31."""

    state = 31
    block_end = len(data) & ~3
    for offset in range(0, block_end, 4):
        block = struct.unpack_from("<I", data, offset)[0]
        block = u32(0xCC9E2D51 * block)
        block = rol32(block, 15)
        block = u32(0x1B873593 * block)
        state ^= block
        state = rol32(state, 13)
        state = u32(state * 5 + 0xE6546B64)

    tail = data[block_end:]
    block = 0
    if len(tail) == 3:
        block ^= tail[2] << 16
    if len(tail) >= 2:
        block ^= tail[1] << 8
    if len(tail) >= 1:
        block ^= tail[0]
        block = u32(0xCC9E2D51 * block)
        block = rol32(block, 15)
        block = u32(0x1B873593 * block)
        state ^= block

    state ^= len(data)
    state = u32(0x85EBCA6B * (state ^ (state >> 16)))
    state = u32(0xC2B2AE35 * (state ^ (state >> 13)))
    return u32(state ^ (state >> 16))


class PRNG6:
    """PRNG type 6 from sub_100912E0/sub_10091140/sub_10091150."""

    def __init__(self, seed_a: int, seed_b: int):
        self.seed_a = u32(seed_a)
        self.seed_b = u32(seed_b)
        self.cached = 0
        self.has_cached = False

    def next(self) -> int:
        if self.has_cached:
            self.has_cached = False
            return self.cached

        next_b = u32(
            (self.seed_b & 0xFFFF) * 0x7689 + (self.seed_b >> 16)
        )
        next_a = u32(
            (self.seed_a & 0xFFFF) * 0x4650 + (self.seed_a >> 16)
        )
        self.seed_b = next_b
        result = u32(rol32(next_b, 16) + next_a)
        self.seed_a = next_a
        self.cached = result
        return result


def decrypt_cipher0(data: bytes, key: bytes) -> bytes:
    """Port sub_10001C90: XOR bytes with PRNG6(hash1(key), hash2(key))."""

    prng = PRNG6(hash_10006680(key), hash_100066c0(key))
    return bytes(value ^ ((prng.next() >> 8) & 0xFF) for value in data)


def dynamic_fallback_cipher0_key() -> bytes:
    """Key from sub_10002390 -> sub_10002F00, with the hashed NUL terminator."""

    return (b"\x01" * 16) + b"\x00"


# Zend opcode table through PHP 8.4 (Zend/zend_vm_opcodes.h)
_SUPPORTED_OPCODE_NAMES: dict[int, str] = {
    0: "ZEND_NOP", 1: "ZEND_ADD", 2: "ZEND_SUB", 3: "ZEND_MUL",
    4: "ZEND_DIV", 5: "ZEND_MOD", 6: "ZEND_SL", 7: "ZEND_SR",
    8: "ZEND_CONCAT", 9: "ZEND_BW_OR", 10: "ZEND_BW_AND", 11: "ZEND_BW_XOR",
    12: "ZEND_POW", 13: "ZEND_BW_NOT", 14: "ZEND_BOOL_NOT", 15: "ZEND_BOOL_XOR",
    16: "ZEND_IS_IDENTICAL", 17: "ZEND_IS_NOT_IDENTICAL",
    18: "ZEND_IS_EQUAL", 19: "ZEND_IS_NOT_EQUAL",
    20: "ZEND_IS_SMALLER", 21: "ZEND_IS_SMALLER_OR_EQUAL",
    22: "ZEND_ASSIGN", 23: "ZEND_ASSIGN_DIM", 24: "ZEND_ASSIGN_OBJ",
    25: "ZEND_ASSIGN_STATIC_PROP", 26: "ZEND_ASSIGN_OP",
    27: "ZEND_ASSIGN_DIM_OP", 28: "ZEND_ASSIGN_OBJ_OP",
    29: "ZEND_ASSIGN_STATIC_PROP_OP", 30: "ZEND_ASSIGN_REF",
    31: "ZEND_QM_ASSIGN", 32: "ZEND_ASSIGN_OBJ_REF",
    33: "ZEND_ASSIGN_STATIC_PROP_REF", 34: "ZEND_PRE_INC",
    35: "ZEND_PRE_DEC", 36: "ZEND_POST_INC", 37: "ZEND_POST_DEC",
    38: "ZEND_PRE_INC_STATIC_PROP", 39: "ZEND_PRE_DEC_STATIC_PROP",
    40: "ZEND_POST_INC_STATIC_PROP", 41: "ZEND_POST_DEC_STATIC_PROP",
    42: "ZEND_JMP", 43: "ZEND_JMPZ", 44: "ZEND_JMPNZ", 45: "ZEND_JMPZNZ",
    46: "ZEND_JMPZ_EX", 47: "ZEND_JMPNZ_EX", 48: "ZEND_CASE",
    49: "ZEND_CHECK_VAR", 50: "ZEND_SEND_VAR_NO_REF_EX", 51: "ZEND_CAST",
    52: "ZEND_BOOL", 53: "ZEND_FAST_CONCAT",
    54: "ZEND_ROPE_INIT", 55: "ZEND_ROPE_ADD", 56: "ZEND_ROPE_END",
    57: "ZEND_BEGIN_SILENCE", 58: "ZEND_END_SILENCE",
    59: "ZEND_INIT_FCALL_BY_NAME", 60: "ZEND_DO_FCALL", 61: "ZEND_INIT_FCALL",
    62: "ZEND_RETURN", 63: "ZEND_RECV", 64: "ZEND_RECV_INIT",
    65: "ZEND_SEND_VAL", 66: "ZEND_SEND_VAR_EX", 67: "ZEND_SEND_REF",
    68: "ZEND_NEW", 69: "ZEND_INIT_NS_FCALL_BY_NAME",
    70: "ZEND_FREE", 71: "ZEND_INIT_ARRAY", 72: "ZEND_ADD_ARRAY_ELEMENT",
    73: "ZEND_INCLUDE_OR_EVAL", 74: "ZEND_UNSET_VAR",
    75: "ZEND_UNSET_DIM", 76: "ZEND_UNSET_OBJ",
    77: "ZEND_FE_RESET_R", 78: "ZEND_FE_FETCH_R", 79: "ZEND_EXIT",
    80: "ZEND_FETCH_R", 81: "ZEND_FETCH_DIM_R", 82: "ZEND_FETCH_OBJ_R",
    83: "ZEND_FETCH_W", 84: "ZEND_FETCH_DIM_W", 85: "ZEND_FETCH_OBJ_W",
    86: "ZEND_FETCH_RW", 87: "ZEND_FETCH_DIM_RW", 88: "ZEND_FETCH_OBJ_RW",
    89: "ZEND_FETCH_IS", 90: "ZEND_FETCH_DIM_IS", 91: "ZEND_FETCH_OBJ_IS",
    92: "ZEND_FETCH_FUNC_ARG", 93: "ZEND_FETCH_DIM_FUNC_ARG",
    94: "ZEND_FETCH_OBJ_FUNC_ARG",
    95: "ZEND_FETCH_UNSET", 96: "ZEND_FETCH_DIM_UNSET", 97: "ZEND_FETCH_OBJ_UNSET",
    98: "ZEND_FETCH_LIST_R", 99: "ZEND_FETCH_CONSTANT",
    100: "ZEND_CHECK_FUNC_ARG",
    101: "ZEND_EXT_STMT", 102: "ZEND_EXT_FCALL_BEGIN", 103: "ZEND_EXT_FCALL_END",
    104: "ZEND_EXT_NOP", 105: "ZEND_TICKS", 106: "ZEND_SEND_VAR_NO_REF",
    107: "ZEND_CATCH", 108: "ZEND_THROW", 109: "ZEND_FETCH_CLASS",
    110: "ZEND_CLONE", 111: "ZEND_RETURN_BY_REF",
    112: "ZEND_INIT_METHOD_CALL", 113: "ZEND_INIT_STATIC_METHOD_CALL",
    114: "ZEND_ISSET_ISEMPTY_VAR", 115: "ZEND_ISSET_ISEMPTY_DIM_OBJ",
    116: "ZEND_SEND_VAL_EX", 117: "ZEND_SEND_VAR",
    118: "ZEND_INIT_USER_CALL", 119: "ZEND_SEND_ARRAY", 120: "ZEND_SEND_USER",
    121: "ZEND_STRLEN", 122: "ZEND_DEFINED", 123: "ZEND_TYPE_CHECK",
    124: "ZEND_VERIFY_RETURN_TYPE",
    125: "ZEND_FE_RESET_RW", 126: "ZEND_FE_FETCH_RW", 127: "ZEND_FE_FREE",
    128: "ZEND_INIT_DYNAMIC_CALL",
    129: "ZEND_DO_ICALL", 130: "ZEND_DO_UCALL", 131: "ZEND_DO_FCALL_BY_NAME",
    132: "ZEND_PRE_INC_OBJ", 133: "ZEND_PRE_DEC_OBJ",
    134: "ZEND_POST_INC_OBJ", 135: "ZEND_POST_DEC_OBJ",
    136: "ZEND_ECHO", 137: "ZEND_OP_DATA",
    138: "ZEND_INSTANCEOF", 139: "ZEND_GENERATOR_CREATE",
    140: "ZEND_MAKE_REF", 141: "ZEND_DECLARE_FUNCTION",
    142: "ZEND_DECLARE_LAMBDA_FUNCTION", 143: "ZEND_DECLARE_CONST",
    144: "ZEND_DECLARE_CLASS", 145: "ZEND_DECLARE_CLASS_DELAYED",
    146: "ZEND_DECLARE_ANON_CLASS", 147: "ZEND_ADD_ARRAY_UNPACK",
    148: "ZEND_ISSET_ISEMPTY_PROP_OBJ", 149: "ZEND_HANDLE_EXCEPTION",
    150: "ZEND_USER_OPCODE", 151: "ZEND_ASSERT_CHECK",
    152: "ZEND_JMP_SET", 153: "ZEND_UNSET_CV",
    154: "ZEND_ISSET_ISEMPTY_CV", 155: "ZEND_FETCH_LIST_W",
    156: "ZEND_SEPARATE", 157: "ZEND_FETCH_CLASS_NAME",
    158: "ZEND_CALL_TRAMPOLINE", 159: "ZEND_DISCARD_EXCEPTION",
    160: "ZEND_YIELD", 161: "ZEND_GENERATOR_RETURN",
    162: "ZEND_FAST_CALL", 163: "ZEND_FAST_RET",
    164: "ZEND_RECV_VARIADIC", 165: "ZEND_SEND_UNPACK",
    166: "ZEND_YIELD_FROM", 167: "ZEND_COPY_TMP",
    168: "ZEND_BIND_GLOBAL", 169: "ZEND_COALESCE",
    170: "ZEND_SPACESHIP", 171: "ZEND_FUNC_NUM_ARGS",
    172: "ZEND_FUNC_GET_ARGS", 173: "ZEND_FETCH_STATIC_PROP_R",
    174: "ZEND_FETCH_STATIC_PROP_W", 175: "ZEND_FETCH_STATIC_PROP_RW",
    176: "ZEND_FETCH_STATIC_PROP_IS",
    177: "ZEND_FETCH_STATIC_PROP_FUNC_ARG",
    178: "ZEND_FETCH_STATIC_PROP_UNSET",
    179: "ZEND_UNSET_STATIC_PROP",
    180: "ZEND_ISSET_ISEMPTY_STATIC_PROP",
    181: "ZEND_FETCH_CLASS_CONSTANT", 182: "ZEND_BIND_LEXICAL",
    183: "ZEND_BIND_STATIC", 184: "ZEND_FETCH_THIS",
    185: "ZEND_SEND_FUNC_ARG", 186: "ZEND_ISSET_ISEMPTY_THIS",
    187: "ZEND_SWITCH_LONG", 188: "ZEND_SWITCH_STRING",
    189: "ZEND_IN_ARRAY", 190: "ZEND_COUNT",
    191: "ZEND_GET_CLASS", 192: "ZEND_GET_CALLED_CLASS",
    193: "ZEND_GET_TYPE", 194: "ZEND_ARRAY_KEY_EXISTS",
    195: "ZEND_MATCH", 196: "ZEND_CASE_STRICT",
    197: "ZEND_MATCH_ERROR", 198: "ZEND_JMP_NULL",
    199: "ZEND_CHECK_UNDEF_ARGS", 200: "ZEND_FETCH_GLOBALS",
    201: "ZEND_VERIFY_NEVER_TYPE", 202: "ZEND_CALLABLE_CONVERT",
    # PHP 8.3 addition and PHP 8.4 additions (Zend/zend_vm_opcodes.h)
    203: "ZEND_BIND_INIT_STATIC_OR_JMP",
    204: "ZEND_FRAMELESS_ICALL_0",
    205: "ZEND_FRAMELESS_ICALL_1",
    206: "ZEND_FRAMELESS_ICALL_2",
    207: "ZEND_FRAMELESS_ICALL_3",
    208: "ZEND_JMP_FRAMELESS",
    209: "ZEND_INIT_PARENT_PROPERTY_HOOK_CALL",
}


def load_opcode_names(header: Path | None = None) -> dict[int, str]:
    if header is None:
        header = (
            Path(__file__).resolve().parents[1]
            / "build"
            / "devel"
            / "php-8.1.34-devel-vs16-x86"
            / "include"
            / "Zend"
            / "zend_vm_opcodes.h"
        )
    if not header.exists():
        return dict(_SUPPORTED_OPCODE_NAMES)

    pattern = re.compile(r"^#define\s+(ZEND_[A-Z0-9_]+)\s+(\d+)\s*$")
    names: dict[int, str] = {}
    for line in header.read_text(encoding="ascii", errors="ignore").splitlines():
        match = pattern.match(line)
        if match:
            names[int(match.group(2))] = match.group(1)
    return names


def read_serialized_string(reader: ByteReader) -> str | None:
    """Read the sub_1009A290 string representation."""

    raw_length = reader.u32()
    if raw_length & 0x80000000:
        return None
    length = raw_length & 0x9FFFFFFF
    value = reader.read(length)
    return value.decode("utf-8", errors="replace")


def skip_interned_string(reader: ByteReader) -> None:
    """Skip sub_1009A240: a negative sentinel or two dictionary indexes."""

    first = reader.i32()
    if first >= 0:
        reader.u32()


def skip_serialized_type(reader: ByteReader, *, interned_names: bool) -> None:
    """Skip the stream portion consumed by sub_1009A350."""

    type_mask = reader.u32()
    if type_mask & 0x01000000:
        if interned_names:
            skip_interned_string(reader)
        else:
            read_serialized_string(reader)
        return

    if type_mask & 0x00400000:
        type_count = reader.u32()
        for _ in range(type_count):
            member_mask = reader.u32()
            if member_mask & 0x01000000:
                if interned_names:
                    skip_interned_string(reader)
                else:
                    read_serialized_string(reader)


def _read_interned_string_ref(
    reader: ByteReader,
) -> int | tuple[int, int] | None:
    """Read sub_1009A240's record and return the signed table offset or (offset, length).

    A negative sentinel ``>= -2`` carries no resolvable name; a value ``< -2``
    is a loader static-string offset; a non-negative value is a reference into
    opcode_data (raw_offset, length).
    """
    first = reader.i32()
    if first >= 0:
        length = reader.u32()
        return (first, length)
    return first


def read_serialized_type_info(
    reader: ByteReader, *, interned_names: bool
) -> dict[str, Any]:
    """Read enough of sub_1009A350's type stream for icdump arg_info."""

    type_mask = reader.u32()
    class_ref: int | tuple[int, int] | None = None
    class_name: str | None = None
    if type_mask & 0x01000000:
        if interned_names:
            class_ref = _read_interned_string_ref(reader)
        else:
            class_name = read_serialized_string(reader)
        return {
            "type_code": type_mask,
            "type_name": f"type({type_mask})" if type_mask else None,
            "class_name": class_name,
            "class_ref": class_ref,
        }

    if type_mask & 0x00400000:
        type_count = reader.u32()
        for _ in range(type_count):
            member_mask = reader.u32()
            if member_mask & 0x01000000:
                if interned_names:
                    ref = _read_interned_string_ref(reader)
                    if class_ref is None:
                        class_ref = ref
                else:
                    cname = read_serialized_string(reader)
                    if class_name is None:
                        class_name = cname

    return {
        "type_code": type_mask,
        "type_name": f"type({type_mask})" if type_mask else None,
        "class_name": class_name,
        "class_ref": class_ref,
    }


def read_arg_info(
    reader: ByteReader, count: int, *, interned_names: bool
) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    for _ in range(count):
        arg_name = None
        arg_name_ref = None
        if interned_names:
            arg_name_ref = _read_interned_string_ref(reader)
            _read_interned_string_ref(reader)
        else:
            arg_name = read_serialized_string(reader)
            read_serialized_string(reader)
        item = read_serialized_type_info(reader, interned_names=interned_names)
        if arg_name:
            item["arg_name"] = arg_name
        if arg_name_ref is not None:
            item["arg_name_ref"] = arg_name_ref
        items.append(item)
    return items


def skip_arg_info(
    reader: ByteReader, count: int, *, interned_names: bool
) -> None:
    for _ in range(count):
        if interned_names:
            skip_interned_string(reader)
            skip_interned_string(reader)
        else:
            read_serialized_string(reader)
            read_serialized_string(reader)
        skip_serialized_type(reader, interned_names=interned_names)


def skip_static_variables(reader: ByteReader) -> None:
    """Skip sub_1009A7A0.

    Current samples use the negative/null sentinel. Positive hash tables need
    the recursive zval reader from sub_1000A070 and are rejected explicitly.
    """

    count = reader.i32()
    if count > 0:
        raise ParseError(
            "positive serialized static-variable tables are not ported yet"
        )


def read_eac0_ref_record(reader: ByteReader) -> tuple[int, int, int, int]:
    """Read the deferred zend_string record consumed by sub_1009EAC0."""

    return struct.unpack("<4I", reader.read(16))


def _resolve_eac0_string(
    record: tuple[int, int, int, int] | None,
    opcode_data: bytes,
) -> str | None:
    if record is None:
        return None
    _, _, raw_offset, length = record
    value, _, _, unresolved = _decode_literal_string(
        opcode_data,
        raw_offset,
        length,
    )
    return value if unresolved is None else None


def sub_10009fc0_stream_size(length_word: int) -> int:
    """Return the byte count read from the stream by sub_10009FC0."""

    return length_word & 0xDFFFFFFF


LITERAL_TYPE_NAMES = {
    0: "IS_UNDEF",
    1: "IS_NULL",
    2: "IS_FALSE",
    3: "IS_TRUE",
    4: "IS_LONG",
    5: "IS_DOUBLE",
    6: "IS_STRING",
    7: "IC_ENCODED_ZVAL",
    11: "IS_CONSTANT_AST_OR_NAME",
    18: "IS_BOOL",
}


def _decode_literal_string(
    opcode_data: bytes,
    raw_offset: int,
    length: int,
) -> tuple[str | None, int, int, str | None]:
    if length == 0:
        return "", 0, 0, None
    signed_offset = struct.unpack("<i", struct.pack("<I", raw_offset))[0]
    flags = 0
    offset = signed_offset
    if signed_offset >= 0:
        flags = raw_offset >> 28
        offset = raw_offset & ~0x10000000
        if offset + length <= len(opcode_data):
            raw = opcode_data[offset : offset + length]
            return raw.decode("utf-8", errors="replace"), offset, flags, None
        return None, offset, flags, "string offset is outside opcode-data buffer"
    return None, signed_offset, flags, f"interned string ref {signed_offset}"


class _EncodedZvalReader:
    """Reader for ionCube's compact literal-array representation."""

    def __init__(self, value: str):
        self.value = value
        self.offset = 0

    def _take(self, size: int) -> str:
        end = self.offset + size
        if size < 0 or end > len(self.value):
            raise ParseError("truncated encoded zval")
        out = self.value[self.offset:end]
        self.offset = end
        return out

    def _decimal(self, delimiter: str) -> int:
        end = self.value.find(delimiter, self.offset)
        if end < 0:
            raise ParseError("encoded zval delimiter not found")
        raw = self.value[self.offset:end]
        self.offset = end + 1
        try:
            return int(raw, 10)
        except ValueError as exc:
            raise ParseError(f"invalid encoded zval integer {raw!r}") from exc

    def _skip_fields(self, count: int) -> None:
        for _ in range(count):
            self._decimal(";")

    def _key(self) -> str | int:
        marker_end = self.offset
        while marker_end < len(self.value) and self.value[marker_end].isdigit():
            marker_end += 1
        if marker_end == self.offset or marker_end >= len(self.value):
            raise ParseError("invalid encoded zval array key")
        size = int(self.value[self.offset:marker_end], 10)
        marker = self.value[marker_end]
        self.offset = marker_end + 1
        raw = self._take(size)
        if marker == "'":
            return raw
        if marker == ":":
            try:
                return int(raw, 10)
            except ValueError as exc:
                raise ParseError(f"invalid numeric array key {raw!r}") from exc
        raise ParseError(f"unknown encoded zval key marker {marker!r}")

    def parse(self) -> Any:
        if self.offset >= len(self.value):
            raise ParseError("missing encoded zval value")
        kind = self._take(1)
        if kind == "[":
            entries: list[tuple[str | int, Any]] = []
            while self.offset < len(self.value) and self.value[self.offset] != "}":
                key = self._key()
                entries.append((key, self.parse()))
            if self._take(1) != "}":
                raise ParseError("unterminated encoded zval array")
            self._skip_fields(5)
            if all(key == index for index, (key, _) in enumerate(entries)):
                return [item for _, item in entries]
            return {str(key): item for key, item in entries}
        if kind == "s":
            length = self._decimal("'")
            result = self._take(length)
            self._skip_fields(4)
            return result
        if kind == "i":
            result = self._decimal(";")
            self._skip_fields(2)
            return result
        if kind == "d":
            end = self.value.find(";", self.offset)
            if end < 0:
                raise ParseError("unterminated encoded zval float")
            result = float(self.value[self.offset:end])
            self.offset = end + 1
            self._skip_fields(2)
            return result
        if kind in {"t", "f"}:
            self._skip_fields(2)
            return kind == "t"
        if kind == "n":
            self._skip_fields(2)
            return None
        raise ParseError(f"unknown encoded zval type {kind!r}")


def decode_encoded_zval(value: str) -> Any:
    reader = _EncodedZvalReader(value)
    decoded = reader.parse()
    if reader.offset != len(value):
        raise ParseError(
            f"{len(value) - reader.offset} trailing bytes in encoded zval"
        )
    return decoded


def read_serialized_literals(
    reader: ByteReader,
    count: int,
    opcode_data: bytes,
) -> tuple[list[SerializedLiteral], bytes]:
    """Read the literal zvals consumed by sub_1009C190/sub_1009BFA0."""

    start = reader.offset
    literals: list[SerializedLiteral] = []
    for index in range(count):
        field0 = reader.u32()
        field1 = reader.u32()
        type_info = reader.u32()
        field3 = reader.u32()
        literal_type = type_info & 0xFF
        type_name = LITERAL_TYPE_NAMES.get(
            literal_type,
            f"TYPE_0x{literal_type:02X}",
        )
        value: Any = None
        string_offset = None
        string_offset_raw = None
        string_length = None
        string_flags = 0
        unresolved = None
        encoded_payload = None

        if literal_type == 1:
            value = None
        elif literal_type == 2:
            value = False
        elif literal_type == 3:
            value = True
        elif literal_type == 4:
            value = struct.unpack("<i", struct.pack("<I", field0))[0]
        elif literal_type == 18:
            value = bool(field0)
        elif literal_type in (6, 7, 11):
            string_offset_raw = reader.u32()
            string_length = reader.u32()
            decoded, offset, string_flags, unresolved = _decode_literal_string(
                opcode_data,
                string_offset_raw,
                string_length,
            )
            string_offset = offset
            if decoded is not None and string_flags & 1:
                decoded = decoded.lower()
            value = decoded
            if literal_type == 7:
                encoded_payload = decoded
                if decoded:
                    try:
                        value = decode_encoded_zval(decoded)
                    except ParseError:
                        # PHP 8.2 (sv=5) prepends a non-ASCII format byte (e.g. 0x81)
                        # that becomes U+FFFD after UTF-8 replacement decode.
                        # Strip it and retry before giving up.
                        if decoded[0] == "�" and len(decoded) > 1:
                            try:
                                value = decode_encoded_zval(decoded[1:])
                            except ParseError:
                                value = decoded
                        else:
                            value = decoded

        literals.append(
            SerializedLiteral(
                index=index,
                type=literal_type,
                type_name=type_name,
                raw_type_info=type_info,
                raw_fields=(field0, field1, field3),
                value=value,
                encoded_payload=encoded_payload,
                string_offset=string_offset,
                string_offset_raw=string_offset_raw,
                string_length=string_length,
                string_flags=string_flags,
                unresolved=unresolved,
            )
        )
    return literals, reader.data[start : reader.offset]


def read_variable_names(variable_records: bytes, opcode_data: bytes) -> list[str]:
    """Decode the 16-byte CV-name records read after B180."""

    if len(variable_records) % 16:
        raise ParseError("variable record area is not 16-byte aligned")

    names: list[str] = []
    for offset in range(0, len(variable_records), 16):
        field0, field1, string_offset_raw, string_length = struct.unpack_from(
            "<4I",
            variable_records,
            offset,
        )
        del field0, field1
        decoded, _, _, unresolved = _decode_literal_string(
            opcode_data,
            string_offset_raw,
            string_length,
        )
        names.append(decoded if decoded is not None and unresolved is None else "")
    return names


def read_outer_descriptor(reader: ByteReader) -> OuterDescriptor:
    """Read the variable descriptor populated by sub_10002FC0."""

    start = reader.offset
    tag = reader.u8()
    payload_length = reader.u32()
    reader.read(payload_length)
    item_count = reader.u32()
    item_lengths = []
    for _ in range(item_count):
        item_length = reader.u32()
        item_lengths.append(item_length)
        reader.read(item_length)
    word10 = reader.u32()
    word11 = reader.u32()
    return OuterDescriptor(
        tag=tag,
        payload_length=payload_length,
        item_lengths=item_lengths,
        word10=word10,
        word11=word11,
        start_offset=start,
        end_offset=reader.offset,
    )


def _read_outer_descriptor(reader: ByteReader) -> None:
    """Skip the descriptor populated by sub_10002FC0."""

    read_outer_descriptor(reader)


def _read_u16_string(reader: ByteReader) -> str | None:
    length = struct.unpack("<H", reader.read(2))[0]
    if not length:
        return None
    raw = reader.read(length + 1)
    return raw[:length].decode("utf-8", errors="replace")


def _serialized_string_offsets(data: bytes, value: bytes) -> list[int]:
    """Find sub_1009A290 string records whose decoded text equals value."""

    offsets: list[int] = []
    if not value:
        return offsets
    for offset in range(0, max(0, len(data) - 4 - len(value)) + 1):
        raw_length = struct.unpack_from("<I", data, offset)[0]
        if raw_length & 0x80000000:
            continue
        length = raw_length & 0x9FFFFFFF
        if length != len(value):
            continue
        start = offset + 4
        end = start + length
        if end <= len(data) and data[start:end] == value:
            offsets.append(offset)
    return offsets


def find_dynamic_method_records(
    data: bytes,
    method_name: str,
    *,
    search_back: int = 4096,
) -> list[DynamicMethodRecord]:
    """Locate CD30/CB50 dynamic-key method records for a serialized method.

    The caller in D330 reads the original method name as a sub_1009A290 string.
    The dynamic prelude immediately before it starts with:

        u32 body_len, u32 d19[3], u32 d19[4], sub_10002FC0 descriptor,
        u16 table/lowercase name, 12-byte key-spec header

    CD30 later reads another u32 expected body length followed by ``body_len``
    encrypted bytes; this function pairs those two halves.
    """

    method_bytes = method_name.encode("utf-8")
    records: list[DynamicMethodRecord] = []
    for name_offset in _serialized_string_offsets(data, method_bytes):
        body_length_offset = name_offset + 4 + len(method_bytes)
        if body_length_offset + 4 > len(data):
            continue
        body_length = struct.unpack_from("<I", data, body_length_offset)[0]
        body_offset = body_length_offset + 4
        body_end = body_offset + body_length
        if body_length <= 0 or body_end > len(data):
            continue

        start_min = max(0, name_offset - search_back)
        for record_start in range(start_min, max(start_min, name_offset - 11)):
            if record_start + 12 > name_offset:
                continue
            if struct.unpack_from("<I", data, record_start)[0] != body_length:
                continue
            seed_a = struct.unpack_from("<I", data, record_start + 4)[0]
            seed_b = struct.unpack_from("<I", data, record_start + 8)[0]
            reader = ByteReader(data, record_start + 12)
            try:
                descriptor = read_outer_descriptor(reader)
                table_name = _read_u16_string(reader)
                key_spec = struct.unpack("<3I", reader.read(12))
            except (ParseError, struct.error):
                continue
            if table_name is None:
                continue
            if table_name.lower() != method_name.lower():
                continue
            if reader.offset > name_offset:
                continue
            records.append(
                DynamicMethodRecord(
                    method_name=method_name,
                    table_name=table_name,
                    record_start=record_start,
                    body_length=body_length,
                    body_length_offset=body_length_offset,
                    body_offset=body_offset,
                    body_end=body_end,
                    opcode_seed_words=(seed_a, seed_b),
                    key_spec_words=key_spec,
                    descriptor=descriptor,
                )
            )
    if not records:
        records.extend(_find_dynamic_method_records_structural(data, method_name))
    return records


def _find_dynamic_method_records_structural(
    data: bytes,
    method_name: str,
) -> list[DynamicMethodRecord]:
    """Fallback discovery from the complete outer record structure.

    Some records do not expose the original mixed-case method string in the
    exact position expected by the old CD30/CB50 pairing heuristic. The loader
    record itself still contains the lowercase function-table key, so use that
    structural parse as the fallback.
    """

    target = method_name.lower()
    records: list[DynamicMethodRecord] = []
    for record_start in range(0, max(0, len(data) - 16)):
        body_length = struct.unpack_from("<I", data, record_start)[0]
        if not (0 < body_length <= len(data) - record_start):
            continue
        try:
            main = extract_dynamic_main_record(
                b"\0\0\0\0" + data[record_start:],
                php_flags=0,
                offset=0,
            )
        except Exception:
            continue
        if not main.table_name or main.table_name.lower() != target:
            continue
        if main.outer_descriptor is None or main.outer_key_words is None:
            continue
        body_offset = record_start + main.blob_offset - 4
        body_end = record_start + main.end_offset - 4
        if body_end > len(data) or body_end - body_offset != body_length:
            continue
        records.append(
            DynamicMethodRecord(
                method_name=method_name,
                table_name=main.table_name,
                record_start=record_start,
                body_length=body_length,
                body_length_offset=body_offset - 4,
                body_offset=body_offset,
                body_end=body_end,
                opcode_seed_words=main.outer_key_words,
                key_spec_words=main.layout_words or (0, 0, 0),
                descriptor=main.outer_descriptor,
            )
        )
    return records


def find_dynamic_method_record(data: bytes, method_name: str) -> DynamicMethodRecord:
    records = find_dynamic_method_records(data, method_name)
    if not records:
        raise ParseError(f"dynamic method record not found for {method_name!r}")
    if len(records) > 1:
        raise ParseError(
            f"multiple dynamic method records found for {method_name!r}; "
            "use find_dynamic_method_records and choose one explicitly"
        )
    return records[0]


def extract_dynamic_main_record(
    data: bytes,
    *,
    php_flags: int,
    offset: int = 0,
) -> DynamicMainRecord:
    """Extract the C5B0 stream embedded by the CD30/CB50 dynamic branch."""

    reader = ByteReader(data, offset)
    start = reader.offset
    if reader.u32() != 0:
        raise ParseError("body does not start with the expected zero marker")

    blob_length = reader.u32()
    outer_key_words = (reader.u32(), reader.u32())
    outer_descriptor = read_outer_descriptor(reader)
    table_name = _read_u16_string(reader)
    raw_layout = struct.unpack("<3I", reader.read(12))
    last_var, temp_variable_count, outer_literal_count = raw_layout

    num_args = reader.u32()
    required_num_args = reader.u32()
    fn_flags = reader.u32()
    arg_count = num_args
    if fn_flags & 0x2000:
        arg_count += 1
    if fn_flags & 0x4000:
        arg_count += 1
    arg_type_info = read_arg_info(reader, arg_count, interned_names=False)
    skip_static_variables(reader)

    line_start = None
    if not php_flags & 0x800:
        line_start = reader.u32()

    variables = [
        read_serialized_string(reader) or "" for _ in range(last_var)
    ]
    reader.u32()
    record_flags = reader.u8()
    if record_flags & 1 and not record_flags & 2:
        read_serialized_string(reader)

    blob_tag = reader.u32()
    blob_offset = reader.offset
    blob = reader.read(blob_length)
    return DynamicMainRecord(
        blob=blob,
        metadata=OpArrayMetadata(
            last_var=last_var,
            literal_count=outer_literal_count,
            fn_flags=fn_flags,
            line_start=line_start,
            num_args=num_args,
            required_num_args=required_num_args,
            variables=variables,
        ),
        temp_variable_count=temp_variable_count,
        outer_literal_count=outer_literal_count,
        record_flags=record_flags,
        blob_tag=blob_tag,
        start_offset=start,
        blob_offset=blob_offset,
        end_offset=reader.offset,
        outer_key_words=outer_key_words,
        outer_descriptor=outer_descriptor,
        table_name=table_name,
        layout_words=raw_layout,
        arg_type_info=arg_type_info,
    )


def _metadata_checksum(data: bytes) -> int:
    low = 0
    high = 0
    for value in data:
        low = (low + value) & 0xFF
        high = (high + low) & 0xFF
    return low | (high << 8)


def read_inner_op_array_record(
    blob: bytes,
    *,
    outer: DynamicMainRecord | None = None,
    offset: int = 0,
) -> InnerOpArrayRecord:
    """Locate B180 inside the C5B0 stream and parse its surrounding metadata."""

    reader = ByteReader(blob, offset)
    start = reader.offset
    raw_metadata = reader.read(124)
    words = list(struct.unpack("<31I", raw_metadata))
    stored_checksum = reader.u32() & 0xFFFF
    calculated_checksum = _metadata_checksum(raw_metadata)
    if stored_checksum != calculated_checksum:
        raise ParseError(
            "op_array metadata checksum mismatch: "
            f"stored 0x{stored_checksum:04X}, "
            f"calculated 0x{calculated_checksum:04X}"
        )
    metadata_tag = reader.u32()

    filename_ref = read_eac0_ref_record(reader) if words[26] else None
    function_name_ref = read_eac0_ref_record(reader) if words[2] else None

    hash_count = reader.u32()
    if hash_count:
        for _ in range(min(hash_count, 10000)):
            for _ in range(2):  # key then value (both use sub_1000A010 format)
                lw = reader.u32()
                if not (lw >> 31):
                    datalen = lw & 0x1FFFFFFF
                    if not (lw & 0x20000000):
                        datalen += 1
                    reader.read(datalen)

    last_var = words[10]
    num_args = words[5]
    # ionCube stores an internal flag bit here.  Zend's materialized op_array
    # keeps 0x04000000 (returns-reference in the dumper IR) but not 0x02000000.
    fn_flags = words[1] & ~0x02000000
    last_try_catch = words[20]
    last_live_range = words[19]
    literal_count = words[27]
    nested_function_count = words[28]

    try_catch_records = reader.read(16 * last_try_catch)
    arg_count = num_args
    if fn_flags & 0x2000:
        arg_count += 1
    if fn_flags & 0x4000:
        arg_count += 1
    arg_type_info = read_arg_info(reader, arg_count, interned_names=True)
    skip_static_variables(reader)

    block = SerializedOpcodeBlock.read(reader)
    variable_records = reader.read(16 * last_var)
    live_range_records = reader.read(16 * last_live_range)
    reader.u32()
    opcode_data_size = sub_10009fc0_stream_size(reader.u32())
    opcode_data = reader.read(opcode_data_size)

    for item in arg_type_info:
        c_ref = item.get("class_ref")
        if isinstance(c_ref, tuple) and len(c_ref) == 2:
            off, ln = c_ref
            val, _, _, unres = _decode_literal_string(opcode_data, off, ln)
            if val and unres is None:
                item["class_name"] = val
                item["class_ref"] = None
        a_ref = item.get("arg_name_ref")
        if isinstance(a_ref, tuple) and len(a_ref) == 2:
            off, ln = a_ref
            val, _, _, unres = _decode_literal_string(opcode_data, off, ln)
            if val and unres is None:
                item["arg_name"] = val
                item["arg_name_ref"] = None

    if outer and outer.arg_type_info:
        for idx, outer_item in enumerate(outer.arg_type_info):
            if idx < len(arg_type_info):
                if outer_item.get("class_name") and not arg_type_info[idx].get("class_name"):
                    arg_type_info[idx]["class_name"] = outer_item["class_name"]
                if outer_item.get("arg_name") and not arg_type_info[idx].get("arg_name"):
                    arg_type_info[idx]["arg_name"] = outer_item["arg_name"]
            else:
                arg_type_info.append(dict(outer_item))
    elif outer and not arg_type_info and outer.arg_type_info:
        arg_type_info = [dict(x) for x in outer.arg_type_info]

    decoded_variables = read_variable_names(variable_records, opcode_data)
    literals, literal_pool = read_serialized_literals(
        reader,
        literal_count,
        opcode_data,
    )

    variables = decoded_variables
    if len(variables) != last_var and outer:
        variables = outer.metadata.variables
    metadata = OpArrayMetadata(
        last_var=last_var,
        literal_count=literal_count,
        fn_flags=fn_flags,
        line_start=words[24],
        line_end=words[25],
        num_args=num_args,
        required_num_args=words[6],
        function_name=_resolve_eac0_string(function_name_ref, opcode_data),
        filename=_resolve_eac0_string(filename_ref, opcode_data),
        variables=variables if len(variables) == last_var else [],
    )
    return InnerOpArrayRecord(
        block=block,
        metadata=metadata,
        raw_metadata_words=words,
        metadata_tag=metadata_tag,
        variable_records=variable_records,
        try_catch_records=try_catch_records,
        opcode_data=opcode_data,
        literal_pool=literal_pool,
        literals=literals,
        arg_type_info=arg_type_info,
        nested_function_count=nested_function_count,
        start_offset=start,
        end_offset=reader.offset,
    )


def _read_aux_operand(aux: ByteReader) -> tuple[int, int]:
    operand_type = aux.u8()
    value = struct.unpack("<I", aux.read(4))[0]
    return operand_type, value


def _zend_variable_offset(
    operand_type: int, serialized_value: int, last_var: int
) -> int:
    if operand_type & IS_CV:
        return 16 * (serialized_value + 3)
    if operand_type & (IS_TMP_VAR | IS_VAR):
        return 16 * (last_var + serialized_value + 3)
    return serialized_value


def _make_operand(
    operand_type: int,
    serialized_value: int,
    metadata: OpArrayMetadata,
) -> Operand:
    base_type = operand_type & 0x0F
    operand = Operand(
        type=operand_type,
        type_name=OPERAND_TYPE_NAMES.get(base_type, f"TYPE_0x{operand_type:02X}"),
        serialized_value=serialized_value,
        zend_value=_zend_variable_offset(
            operand_type, serialized_value, metadata.last_var
        ),
    )

    if base_type == IS_CONST:
        operand.literal_index = serialized_value
    elif base_type == IS_CV:
        operand.variable_index = serialized_value
        if serialized_value < len(metadata.variables):
            operand.variable_name = metadata.variables[serialized_value]
    elif base_type in (IS_TMP_VAR, IS_VAR):
        operand.variable_index = serialized_value
    return operand


def _validate_target(
    serialized_value: int,
    opcode_count: int,
    label: str,
    warnings: list[str],
    *,
    one_based: bool = True,
    self_index: int | None = None,
) -> int:
    """Resolve a serialized jump operand to an opline index.

    Mirrors the loader's pass-two (sub_1009B200), which converts every jump
    operand uniformly via ``opline = base + sizeof(zend_op) * value``. The only
    family-level difference is how the value is *encoded* in ionCube's stream:
    the conditional/unconditional jumps (JMP, JMPZ, JMPNZ, ...) store
    ``opline_num + 1`` (``one_based``), while the foreach helpers (FE_RESET_R/RW,
    FE_FETCH_R/RW) store ``opline_num`` directly (``one_based=False``).

    ``self_index`` is the index of the instruction owning this operand. When
    provided, a resolved target that equals it is flagged as a diagnostic only:
    a jump to itself is provably invalid, so it almost always signals a corrupt
    or decoy record rather than a real branch. The value is NOT rewritten -- we
    never fabricate a target; the formula stays uniform.
    """
    target = serialized_value - 1 if one_based else serialized_value
    if target < 0 or target >= opcode_count:
        warnings.append(
            f"{label} target {target} from serialized value "
            f"{serialized_value} is outside 0..{opcode_count - 1}"
        )
    elif self_index is not None and target == self_index:
        warnings.append(
            f"{label} target {target} from serialized value "
            f"{serialized_value} is a self-target (instruction {self_index} "
            "jumps to itself); the record is likely corrupt or a decoy"
        )
    return target


def _apply_jump_targets(opline: DecodedOpcode, opcode_count: int) -> None:
    """Static equivalent of sub_1009B200, retaining indexes."""

    def terminal_if_lazy_self_target(target: int, label: str) -> int:
        if target != opline.index or opcode_count <= 0:
            return target
        repaired = opcode_count - 1
        opline.warnings.append(
            f"{label} lazy self-target {target} resolved to terminal opline "
            f"{repaired}"
        )
        return repaired

    if opline.opcode in OP1_JUMP_OPCODES:
        target = _validate_target(
            opline.op1.serialized_value,
            opcode_count,
            "op1",
            opline.warnings,
            self_index=opline.index,
        )
        opline.op1.jump_target = terminal_if_lazy_self_target(target, "op1")

    if opline.opcode in (0x4D, 0x7D, 0xC6):  # FE_RESET_R / FE_RESET_RW / ZEND_JMP_NULL
        opline.op2.jump_target = _validate_target(
            opline.op2.serialized_value,
            opcode_count,
            "op2",
            opline.warnings,
            one_based=False,
        )
    elif opline.opcode in OP2_JUMP_OPCODES:
        target = _validate_target(
            opline.op2.serialized_value,
            opcode_count,
            "op2",
            opline.warnings,
            self_index=opline.index,
        )
        opline.op2.jump_target = terminal_if_lazy_self_target(target, "op2")

    if opline.opcode == 0x6B and not (opline.extended_value & 1):
        opline.op2.jump_target = _validate_target(
            opline.op2.serialized_value,
            opcode_count,
            "catch op2",
            opline.warnings,
        )

    if opline.opcode in (0x4E, 0x7E):  # FE_FETCH_R / FE_FETCH_RW
        target = _validate_target(
            opline.extended_value,
            opcode_count,
            "extended_value",
            opline.warnings,
            one_based=False,
        )
        opline.extended_jump_target = target
        opline.extended_value = (target - opline.index) * 28
    elif opline.opcode in (0xBB, 0xBC, 0xC3):
        target = _validate_target(
            opline.extended_value,
            opcode_count,
            "extended_value",
            opline.warnings,
            one_based=False,
        )
        opline.extended_value = (target - opline.index) * 28
    elif opline.opcode in EXTENDED_JUMP_OPCODES:
        opline.extended_jump_target = _validate_target(
            opline.extended_value,
            opcode_count,
            "extended_value",
            opline.warnings,
        )


def _apply_opcode_fixups(
    opline: DecodedOpcode,
    metadata: OpArrayMetadata,
    php_format_id: int,
) -> None:
    """Port the deterministic opcode-specific fixups in sub_1009B3C0."""

    if (
        opline.opcode in (63, 164)
        and php_format_id >= 120002
        and opline.extended_value != 0xFFFFFFFF
    ):
        value = opline.extended_value
        opline.extended_value = (value & 3) | ((value >> 1) & 0x7FFFFFFE)

    if opline.opcode in (182, 183):
        value = opline.extended_value
        opline.extended_value = (value & 3) | (24 * (value // 24))

    if opline.opcode in SEND_RESULT_FROM_OP2 and opline.op2.type != IS_CONST:
        opline.result.zend_value = 16 * (opline.op2.serialized_value + 2)

    if opline.opcode == 61 and opline.op1.serialized_value != 0xFFFFFFFF:
        opline.op1.zend_value = 16 * (opline.op1.serialized_value + 3)

    if opline.opcode in (62, 111) and metadata.fn_flags & 0x01000000:
        opline.opcode = 161


def collect_raw_opcode_block(
    block: SerializedOpcodeBlock,
    metadata: OpArrayMetadata,
    *,
    serialization_version: int,
    header_flags: int = 0,
) -> RawOpcodeBlock:
    """Walk B180 without deobfuscating the opcode byte."""

    words = block.words
    word_index = 0
    aux = ByteReader(block.auxiliary_records)
    entries: list[RawOpcodeEntry] = []

    while word_index < len(words):
        if len(entries) >= block.opcode_count:
            raise ParseError(
                "encoded word stream produces more opcodes than opcode_count"
            )

        encoded_word = words[word_index]
        word_index += 1
        if serialization_version >= 6:
            if word_index >= len(words):
                raise ParseError("missing serialized handler word")
            word_index += 1

        def operand(mask: int) -> Operand:
            if not encoded_word & mask:
                return _make_operand(IS_UNUSED, 0, metadata)
            operand_type, value = _read_aux_operand(aux)
            return _make_operand(operand_type, value, metadata)

        result = operand(0x100)
        op1 = operand(0x200)
        op2 = operand(0x400)

        extended_mode = encoded_word & 0x1800
        if extended_mode == 0:
            extended_value = 0
        elif extended_mode == 0x800:
            extended_value = 1
        elif extended_mode == 0x1000:
            extended_value = 0x3C
        else:
            if word_index >= len(words):
                raise ParseError("missing extended_value word")
            extended_value = words[word_index]
            word_index += 1

        if header_flags & 0x800:
            lineno = 0
        else:
            lineno = encoded_word >> 16
            if lineno == 0xFFFF:
                if word_index >= len(words):
                    raise ParseError("missing extended line-number word")
                lineno = words[word_index]
                word_index += 1

        entries.append(
            RawOpcodeEntry(
                index=len(entries),
                encoded_opcode_byte=encoded_word & 0xFF,
                encoded_word=encoded_word,
                lineno=lineno,
                op1=op1,
                op2=op2,
                result=result,
                extended_value=extended_value,
            )
        )

    if len(entries) != block.opcode_count:
        raise ParseError(
            f"walked {len(entries)} raw opcodes, expected {block.opcode_count}"
        )

    return RawOpcodeBlock(
        metadata=metadata,
        opcode_count=block.opcode_count,
        encoded_word_count=len(block.words),
        auxiliary_record_count=len(block.auxiliary_records) // 5,
        entries=entries,
        consumed_words=word_index,
        consumed_auxiliary_records=aux.offset // 5,
    )


def generate_c3d0_key_bytes(
    *,
    seed_a: int,
    seed_b: int,
    opcode_count: int,
    request_key: int,
) -> bytes:
    """Generate the byte view of C3D0's ``opcode_count + 1`` dword stream."""

    prng = PRNG6(seed_a, seed_b)
    chunks = bytearray()
    for _ in range(opcode_count + 1):
        chunks.extend(u32(prng.next() ^ request_key).to_bytes(4, "little"))
    return bytes(chunks)


def _b3c0_opcode_sentinel(
    key_bytes: bytes,
    *,
    opcode_count: int,
    opcode_index: int,
    serialization_version: int,
    descriptor_delta: int,
) -> int | None:
    """Return the sentinel byte used by B3C0's first opcode lane."""

    if serialization_version < 3:
        return None
    if serialization_version < 6:
        return 0x95

    stream_index = opcode_count + descriptor_delta + opcode_index
    if stream_index >= len(key_bytes):
        raise ParseError(
            "generated key stream is too short for opcode stream "
            f"delta {descriptor_delta}"
        )
    return key_bytes[stream_index] ^ 0x95


def build_php81_opcode_xor_stream(
    block: SerializedOpcodeBlock,
    metadata: OpArrayMetadata,
    *,
    outer: DynamicMainRecord,
    request_key: int,
    serialization_version: int,
    header_flags: int = 0,
    descriptor_delta: int = 2,
) -> OpcodeXorStream:
    """Port the supported v15 opcode-byte lane in C3D0 and B3C0.

    The result decodes the serialized opcode byte to ionCube's materialized
    handler-selector byte (CH at 0x1009BD4A). For serialization version 5 this
    is already the direct Zend opcode. For version 6+ the real VM opcode can
    still differ because B3C0 may materialize a handler through sub_10070170,
    which is a separate handler-lane decode.
    """

    if outer.outer_key_words is None:
        raise ParseError("dynamic outer record does not expose C3D0 seed words")

    raw_block = collect_raw_opcode_block(
        block,
        metadata,
        serialization_version=serialization_version,
        header_flags=header_flags,
    )
    opcode_count = raw_block.opcode_count
    key_bytes = generate_c3d0_key_bytes(
        seed_a=outer.outer_key_words[0],
        seed_b=outer.outer_key_words[1],
        opcode_count=opcode_count,
        request_key=request_key,
    )
    if len(key_bytes) < opcode_count:
        raise ParseError("generated key stream is too short for opcode bytes")

    xor_bytes = bytearray()
    raw_lane = bytearray()
    decoded = bytearray()
    for index, entry in enumerate(raw_block.entries):
        raw_opcode = entry.encoded_opcode_byte
        key_byte = key_bytes[index]
        sentinel = _b3c0_opcode_sentinel(
            key_bytes,
            opcode_count=opcode_count,
            opcode_index=index,
            serialization_version=serialization_version,
            descriptor_delta=descriptor_delta,
        )

        if sentinel is not None and raw_opcode == sentinel:
            key_byte = 0

        mixed = key_byte ^ raw_opcode
        if sentinel is not None and mixed == sentinel:
            key_byte = 0
            mixed = raw_opcode

        if serialization_version >= 6:
            stream_byte = key_bytes[opcode_count + descriptor_delta + index]
            opcode = stream_byte ^ mixed
        else:
            opcode = mixed
        raw_lane.append(mixed)
        decoded.append(opcode)
        xor_bytes.append(raw_opcode ^ opcode)

    return OpcodeXorStream(
        request_key=u32(request_key),
        seed_a=u32(outer.outer_key_words[0]),
        seed_b=u32(outer.outer_key_words[1]),
        descriptor_delta=descriptor_delta,
        key_bytes=key_bytes,
        xor_bytes=bytes(xor_bytes),
        raw_opcode_bytes=bytes(raw_lane),
        decoded_opcode_bytes=bytes(decoded),
    )


def handler_key_dword_for_index(key_bytes: bytes, opcode_count: int, index: int) -> int:
    """Build the BCF0 handler key dword from C3D0's byte stream."""

    offset = opcode_count + 3 * index
    if offset + 2 >= len(key_bytes):
        raise ParseError(f"handler key bytes are missing for opcode {index}")
    byte0 = key_bytes[offset]
    byte1 = key_bytes[offset + 1]
    byte2 = key_bytes[offset + 2]
    return (
        ((byte0 ^ byte1) << 24)
        | (byte2 << 16)
        | (byte1 << 8)
        | byte0
    )


def apply_php81_handler_opcode_decode(
    decoded: DecodedOpcodeBlock,
    *,
    opcode_xor_stream: OpcodeXorStream,
    handler_tables: LoaderHandlerTables,
    handler_variant: int,
    opcode_names: dict[int, str] | None = None,
    php_format_id: int = 120002,
) -> None:
    """Resolve B3C0's handler lane to the true Zend opcode when possible."""

    opcode_names = opcode_names or {}
    opcodes = decoded.opcodes
    opcode_count = len(opcodes)
    for index, opline in enumerate(opcodes):
        next_opline = opcodes[index + 1] if index + 1 < opcode_count else None
        handler_key = handler_key_dword_for_index(
            opcode_xor_stream.key_bytes,
            opcode_count,
            index,
        )
        opline.opcode_raw = opline.opcode
        opline.handler_key_dword = handler_key
        opline.handler_variant = handler_variant

        if opline.handler_word == u32(~handler_key):
            opline.opcode_source = "opcode_raw_direct_handler"
            continue

        if opline.handler_word is None:
            opline.warnings.append("missing handler word for handler-lane decode")
            continue

        handler_index = handler_tables.decode_handler_index(
            opline.handler_word,
            handler_key,
            handler_variant,
        )
        candidates = handler_tables.opcode_candidates_for_handler_index(
            handler_index,
            opline,
            next_opline,
        )
        opline.handler_index = handler_index
        opline.handler_candidates = candidates

        if len(candidates) != 1:
            opline.warnings.append(
                "handler-lane opcode is ambiguous: "
                + ", ".join(str(item) for item in candidates)
            )
            continue

        opline.opcode = candidates[0]
        opline.opcode_source = "handler_lane"
        _apply_opcode_fixups(opline, decoded.metadata, php_format_id)
        opline.opcode_name = opcode_names.get(opline.opcode)
        _apply_jump_targets(opline, opcode_count)


def decode_opcode_block(
    block: SerializedOpcodeBlock,
    metadata: OpArrayMetadata,
    *,
    serialization_version: int,
    php_format_id: int = 120002,
    header_flags: int = 0,
    opcode_xor: bytes | None = None,
    opcode_names: dict[int, str] | None = None,
) -> DecodedOpcodeBlock:
    """Port the structural reconstruction performed by sub_1009B3C0.

    ``opcode_xor`` is the final XOR byte for each opcode after the loader's
    PRNG lane selection and sentinel handling. Keeping this boundary explicit
    separates B3C0 from the surrounding per-file key schedule.
    """

    metadata.validate()
    opcode_names = opcode_names or {}

    if opcode_xor is not None and len(opcode_xor) < block.opcode_count:
        raise ParseError(
            f"opcode_xor has {len(opcode_xor)} bytes, "
            f"expected at least {block.opcode_count}"
        )

    words = block.words
    word_index = 0
    aux = ByteReader(block.auxiliary_records)
    decoded: list[DecodedOpcode] = []

    while word_index < len(words):
        if len(decoded) >= block.opcode_count:
            raise ParseError(
                "encoded word stream produces more opcodes than opcode_count"
            )

        encoded_word = words[word_index]
        word_index += 1
        handler_word = None
        if serialization_version >= 6:
            if word_index >= len(words):
                raise ParseError("missing serialized handler word")
            handler_word = words[word_index]
            word_index += 1

        encoded_opcode = encoded_word & 0xFF
        opcode = encoded_opcode
        opcode_xor_byte = None
        opcode_source = "serialized"
        if opcode_xor is not None:
            opcode_xor_byte = opcode_xor[len(decoded)]
            opcode ^= opcode_xor_byte
            opcode_source = "opcode_raw"
        if opcode > ZEND_VM_LAST_OPCODE:
            raise ParseError(
                f"decoded opcode {opcode} at index {len(decoded)} "
                f"exceeds {ZEND_VM_LAST_OPCODE}"
            )

        def operand(mask: int) -> Operand:
            if not encoded_word & mask:
                return _make_operand(IS_UNUSED, 0, metadata)
            operand_type, value = _read_aux_operand(aux)
            return _make_operand(operand_type, value, metadata)

        result = operand(0x100)
        op1 = operand(0x200)
        op2 = operand(0x400)

        extended_mode = encoded_word & 0x1800
        if extended_mode == 0:
            extended_value = 0
        elif extended_mode == 0x800:
            extended_value = 1
        elif extended_mode == 0x1000:
            extended_value = 0x3C
        else:
            if word_index >= len(words):
                raise ParseError("missing extended_value word")
            extended_value = words[word_index]
            word_index += 1

        if header_flags & 0x800:
            lineno = 0
        else:
            lineno = encoded_word >> 16
            if lineno == 0xFFFF:
                if word_index >= len(words):
                    raise ParseError("missing extended line-number word")
                lineno = words[word_index]
                word_index += 1

        opline = DecodedOpcode(
            index=len(decoded),
            opcode=opcode,
            opcode_name=opcode_names.get(opcode),
            encoded_word=encoded_word,
            handler_word=handler_word,
            op1=op1,
            op2=op2,
            result=result,
            extended_value=extended_value,
            lineno=lineno,
            opcode_xor_byte=opcode_xor_byte,
            opcode_source=opcode_source,
        )

        for label, item in (("op1", op1), ("op2", op2)):
            if (
                item.literal_index is not None
                and item.literal_index >= metadata.literal_count
            ):
                opline.warnings.append(
                    f"{label} literal {item.literal_index} is outside "
                    f"0..{metadata.literal_count - 1}"
                )

        _apply_opcode_fixups(opline, metadata, php_format_id)
        opline.opcode_name = opcode_names.get(opline.opcode)
        _apply_jump_targets(opline, block.opcode_count)
        decoded.append(opline)

    if len(decoded) != block.opcode_count:
        raise ParseError(
            f"decoded {len(decoded)} opcodes, expected {block.opcode_count}"
        )
    if aux.remaining:
        raise ParseError(
            f"{aux.remaining} auxiliary bytes remain after opcode decoding"
        )

    return DecodedOpcodeBlock(
        metadata=metadata,
        opcodes=decoded,
        encoded_word_count=len(block.words),
        auxiliary_record_count=len(block.auxiliary_records) // 5,
        consumed_words=word_index,
        consumed_auxiliary_records=aux.offset // 5,
        start_offset=block.start_offset,
        end_offset=block.end_offset,
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path, help="binary containing a B180 block")
    parser.add_argument("--offset", type=lambda value: int(value, 0), default=0)
    parser.add_argument("--last-var", type=int)
    parser.add_argument("--literal-count", type=int)
    parser.add_argument("--serialization-version", type=int, required=True)
    parser.add_argument("--php-format-id", type=int, default=120002)
    parser.add_argument(
        "--header-flags", type=lambda value: int(value, 0), default=0
    )
    parser.add_argument(
        "--opcode-xor",
        type=Path,
        help="file containing one final XOR byte per opcode",
    )
    parser.add_argument(
        "--request-key",
        type=lambda value: int(value, 0),
        help=(
            "loader dword_101B00E0 / header bytecode_xor_key, used to "
            "generate the v15 C3D0 opcode stream"
        ),
    )
    parser.add_argument(
        "--opcode-stream-delta",
        type=int,
        default=2,
        help="descriptor delta added before the v15 opcode byte stream",
    )
    parser.add_argument(
        "--loader-dll",
        type=Path,
        default=(
            Path(__file__).resolve().parents[1]
            / "runtime"
            / "ext"
            / "ioncube_loader_win_8.1.dll"
        ),
        help="ionCube loader DLL used for static handler-lane tables",
    )
    parser.add_argument(
        "--handler-variant",
        type=int,
        default=2,
        help="handler table variant for the selected PHP v15 loader profile",
    )
    parser.add_argument(
        "--php-version",
        type=int,
        choices=(81, 82, 83, 84),
        default=81,
        help="PHP ABI profile (81, 82, 83, or 84)",
    )
    parser.add_argument(
        "--no-handler-decode",
        action="store_true",
        help="stop after opcode_raw and do not resolve the handler lane",
    )
    parser.add_argument("--output", type=Path)
    parser.add_argument(
        "--text-output",
        type=Path,
        help="write a compact human-readable text dump/report",
    )
    parser.add_argument(
        "--dynamic-main",
        action="store_true",
        help="input is a full inflated body using the CD30 dynamic branch",
    )
    parser.add_argument(
        "--php-flags",
        type=lambda value: int(value, 0),
        default=0,
        help="header trailer php_flags, needed with --dynamic-main",
    )
    args = parser.parse_args()

    input_data = args.input.read_bytes()
    stage_text: str | None = None
    outer: DynamicMainRecord | None = None
    inner: InnerOpArrayRecord | None = None
    inner_method: str | None = None
    generated_opcode_xor: OpcodeXorStream | None = None
    generated_opcode_error: Exception | None = None
    if args.dynamic_main:
        outer = extract_dynamic_main_record(
            input_data,
            php_flags=args.php_flags,
            offset=args.offset,
        )
        try:
            inner = read_inner_op_array_record(outer.blob, outer=outer)
            inner_method = "none"
        except Exception as exc:
            decrypted_blob = decrypt_cipher0(
                outer.blob,
                dynamic_fallback_cipher0_key(),
            )
            try:
                inner = read_inner_op_array_record(decrypted_blob, outer=outer)
                inner_method = "cipher0-fallback-zero-key-spec"
            except Exception:
                if not args.text_output:
                    raise exc
                args.text_output.write_text(
                    render_dynamic_stage_text(outer, inner_error=exc),
                    encoding="utf-8",
                )
                return 0
        stage_text = render_dynamic_stage_text(
            outer,
            inner=inner,
            inner_method=inner_method,
        )
        block = inner.block
        metadata = inner.metadata
    else:
        if args.last_var is None or args.literal_count is None:
            parser.error(
                "--last-var and --literal-count are required "
                "without --dynamic-main"
            )
        reader = ByteReader(input_data, args.offset)
        block = SerializedOpcodeBlock.read(reader)
        metadata = OpArrayMetadata(
            last_var=args.last_var,
            literal_count=args.literal_count,
        )
    opcode_xor = args.opcode_xor.read_bytes() if args.opcode_xor else None
    if (
        args.dynamic_main
        and opcode_xor is None
        and args.request_key is not None
        and outer is not None
        and inner is not None
    ):
        try:
            generated_opcode_xor = build_php81_opcode_xor_stream(
                block,
                metadata,
                outer=outer,
                request_key=args.request_key,
                serialization_version=args.serialization_version,
                header_flags=args.header_flags,
                descriptor_delta=args.opcode_stream_delta,
            )
            opcode_xor = generated_opcode_xor.xor_bytes
            stage_text = render_dynamic_stage_text(
                outer,
                inner=inner,
                inner_method=inner_method,
                opcode_xor_stream=generated_opcode_xor,
            )
        except Exception as exc:
            generated_opcode_error = exc
    if args.dynamic_main and opcode_xor is None and args.php_flags & 0x2C80:
        if args.text_output and outer and inner:
            raw_block = None
            raw_error: Exception | None = None
            for raw_version in (5, args.serialization_version):
                try:
                    raw_block = collect_raw_opcode_block(
                        block,
                        metadata,
                        serialization_version=raw_version,
                        header_flags=args.header_flags,
                    )
                    break
                except Exception as exc:
                    raw_error = exc
            args.text_output.write_text(
                render_dynamic_stage_text(
                    outer,
                    inner=inner,
                    inner_method=inner_method,
                    opcode_error=ParseError(
                        "opcode_xor stream is required by php_flags; "
                        + (
                            str(generated_opcode_error)
                            if generated_opcode_error is not None
                            else "provide --request-key to generate it"
                        )
                    ),
                    raw_block=raw_block,
                ),
                encoding="utf-8",
            )
            if raw_block is None and raw_error is not None:
                raise raw_error
            return 0
        raise ParseError(
            "opcode_xor stream is required by php_flags but was not supplied"
        )
    try:
        opcode_names = load_opcode_names()
        decoded = decode_opcode_block(
            block,
            metadata,
            serialization_version=args.serialization_version,
            php_format_id=args.php_format_id,
            header_flags=args.header_flags,
            opcode_xor=opcode_xor,
            opcode_names=opcode_names,
        )
        handler_state: str | None = None
        if generated_opcode_xor is not None and not args.no_handler_decode:
            if args.serialization_version < 6:
                handler_state = (
                    "not used for serialization_version < 6; "
                    "opcode byte is direct"
                )
            elif args.loader_dll.exists():
                handler_tables = LoaderHandlerTables.from_dll(args.loader_dll, php_version=args.php_version)
                apply_php81_handler_opcode_decode(
                    decoded,
                    opcode_xor_stream=generated_opcode_xor,
                    handler_tables=handler_tables,
                    handler_variant=args.handler_variant,
                    opcode_names=opcode_names,
                    php_format_id=args.php_format_id,
                )
                direct_count = sum(
                    1
                    for item in decoded.opcodes
                    if item.opcode_source == "opcode_raw_direct_handler"
                )
                handler_count = sum(
                    1
                    for item in decoded.opcodes
                    if item.opcode_source == "handler_lane"
                )
                ambiguous_count = sum(
                    1
                    for item in decoded.opcodes
                    if item.handler_candidates and item.opcode_source != "handler_lane"
                )
                handler_state = (
                    "resolved via static loader tables "
                    f"variant {args.handler_variant}; "
                    f"direct={direct_count}, handler_lane={handler_count}, "
                    f"ambiguous={ambiguous_count}"
                )
            else:
                handler_state = f"skipped; loader DLL not found: {args.loader_dll}"
        if stage_text and outer and inner and generated_opcode_xor is not None:
            stage_text = render_dynamic_stage_text(
                outer,
                inner=inner,
                inner_method=inner_method,
                opcode_xor_stream=generated_opcode_xor,
                handler_opcode_state=handler_state,
            )
    except Exception as exc:
        if args.text_output and args.dynamic_main and outer and inner:
            raw_block = None
            for raw_version in (args.serialization_version, 5):
                try:
                    raw_block = collect_raw_opcode_block(
                        block,
                        metadata,
                        serialization_version=raw_version,
                        header_flags=args.header_flags,
                    )
                    break
                except Exception:
                    continue
            args.text_output.write_text(
                render_dynamic_stage_text(
                    outer,
                    inner=inner,
                    inner_method=inner_method,
                    opcode_error=exc,
                    raw_block=raw_block,
                ),
                encoding="utf-8",
            )
            return 0
        raise
    rendered = json.dumps(decoded.to_dict(), indent=2)
    if args.text_output:
        text = render_opcode_text(decoded)
        if stage_text:
            text = stage_text + "\n" + text
        args.text_output.write_text(text, encoding="utf-8")
    if args.output:
        args.output.write_text(rendered + "\n", encoding="utf-8")
    elif not args.text_output:
        print(rendered)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
