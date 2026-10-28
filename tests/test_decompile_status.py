"""Tests for version-exact loader selection and partial-decode status."""

from pathlib import Path
from types import SimpleNamespace

from dump_plain_file_static import (
    _get_dll_candidates,
    _load_handler_tables,
    _load_resolver,
    build_decompile_status,
)


def test_php82_loader_selection_never_falls_back_to_81():
    candidates = _get_dll_candidates(None, 82)

    assert all(p.name == "ioncube_loader_win_8.2.dll" for p in candidates)


def test_explicit_loader_path_is_preserved(tmp_path):
    explicit = tmp_path / "ioncube_loader_win_8.2.dll"
    explicit.write_bytes(b"")

    assert _get_dll_candidates(explicit, 82) == [explicit]


def test_php82_loader_never_returns_81_tables():
    resolver = _load_resolver(None, 82)
    handler_tables = _load_handler_tables(None, 82)

    assert resolver is None or resolver.loaded_php_version == 82
    assert handler_tables is None or handler_tables.loaded_php_version == 82


def test_partial_status_counts_methods_and_missing_loader():
    status = build_decompile_status(
        82,
        [{"name": "main", "state": "ok", "opcodes": 1}],
        resolver=None,
        handler_tables=None,
    )

    assert status["partial"] is True
    assert status["methods"] == {
        "total": 1,
        "ok": 1,
        "stubs": 0,
        "opcode_errors": 0,
        "failed": 0,
    }
    assert status["loader"]["degraded"] is True
    assert status["loader"]["expected_php_version"] == 82


def test_partial_status_lists_stub_opcode_error_and_failure():
    resolver = SimpleNamespace(
        source_path=Path("ioncube_loader_win_8.2.dll"),
        loaded_php_version=82,
    )
    handler_tables = SimpleNamespace(
        source_path=Path("ioncube_loader_win_8.2.dll"),
        loaded_php_version=82,
    )
    methods = [
        {"name": "main", "state": "ok", "opcodes": 3},
        {"name": "stub_method", "state": "stub:dynamic_key"},
        {"name": "broken_method", "state": "opcode_error: bad stream"},
        {"name": "failed_method", "state": "failed"},
    ]

    status = build_decompile_status(82, methods, resolver, handler_tables)

    assert status["partial"] is True
    assert status["methods"] == {
        "total": 4,
        "ok": 1,
        "stubs": 1,
        "opcode_errors": 1,
        "failed": 1,
    }
    assert status["loader"]["degraded"] is False
    assert status["problems"] == [
        {"name": "stub_method", "state": "stub:dynamic_key"},
        {"name": "broken_method", "state": "opcode_error: bad stream"},
        {"name": "failed_method", "state": "failed"},
    ]


def test_clean_status_is_not_partial():
    loader = SimpleNamespace(
        source_path=Path("ioncube_loader_win_8.1.dll"),
        loaded_php_version=81,
    )

    status = build_decompile_status(
        81,
        [{"name": "main", "state": "ok", "opcodes": 3}],
        loader,
        loader,
    )

    assert status["partial"] is False
    assert status["loader"]["degraded"] is False
    assert status["problems"] == []
