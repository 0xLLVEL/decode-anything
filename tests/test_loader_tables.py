"""Regression tests for the bundled 64-bit loader tables."""

from pathlib import Path

import pytest

from engines.ioncube.body import (
    LoaderHandlerTables,
    LoaderInternedStringResolver,
    ParseError,
)
from engines.ioncube.dumper import (
    _get_dll_candidates,
    _require_supported_body_layout,
)

VERSIONS = (81, 82, 83, 84)
SEVEN_X_VERSIONS = (72, 73, 74)


def _bundled_loader(php_version):
    candidates = _get_dll_candidates(None, php_version)
    if not candidates:
        pytest.skip(f"PHP {php_version} loader not available")
    return candidates[0]


@pytest.mark.parametrize("php_version", VERSIONS)
def test_x64_handler_tables_are_addressable(php_version):
    tables = LoaderHandlerTables.from_dll(
        _bundled_loader(php_version), php_version
    )

    assert tables.image_base == 0x180000000
    for table_a, table_b in tables.VARIANT_TABLES:
        tables.u16(table_a + 2 * 0x1FFFF)
        tables.u16(table_b + 2 * 0x1FFFF)
    assert tables.u8(tables.OPCODE_META_ID) == 0
    assert tables._dword_at(tables.OPCODE_HANDLER_META, 0) == 0
    assert tables._dword_at(tables.TYPE_DIMENSION_TABLE, 0) == 3
    assert tables.global_feature_word != 0xFFFFFFFF


@pytest.mark.parametrize("php_version", VERSIONS)
def test_x64_string_resolver_uses_pointer_table(php_version):
    resolver = LoaderInternedStringResolver.from_dll(
        _bundled_loader(php_version), php_version
    )

    assert resolver.pointer_size == 8
    assert resolver.decode_ref(-8) == "_GET"
    assert resolver.decode_ref(-9) == "_POST"


@pytest.mark.parametrize("php_version", SEVEN_X_VERSIONS)
def test_php7_string_resolver_uses_pointer_table(php_version):
    resolver = LoaderInternedStringResolver.from_dll(
        _bundled_loader(php_version), php_version
    )

    assert resolver.pointer_size == 8
    assert resolver.decode_ref(-8) == "_GET"
    assert resolver.decode_ref(-9) == "_POST"
    assert resolver.decode_ref(-12) == "_GLOBALS"
    assert resolver.decode_ref(-13) == "this"


@pytest.mark.parametrize("php_version", SEVEN_X_VERSIONS)
def test_php7_body_layout_points_at_the_runtime_dump(php_version):
    with pytest.raises(ParseError, match="runtime opcode dump"):
        _require_supported_body_layout(php_version)


def test_php81_body_layout_is_accepted():
    _require_supported_body_layout(81)
