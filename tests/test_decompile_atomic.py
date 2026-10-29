"""Tests for atomic writes and post-decompile validation failures."""

import decompile
from decompile import _result_exit_code, _write_output_atomically


def test_result_exit_code_distinguishes_syntax_failure():
    assert _result_exit_code(True, True) == 0
    assert _result_exit_code(True, False) == 2
    assert _result_exit_code(False, False) == 1


def test_atomic_write_replaces_target_when_syntax_is_valid(tmp_path, monkeypatch):
    monkeypatch.setattr(decompile, "validate_php_syntax", lambda path: (True, ""))
    target = tmp_path / "out.php"
    target.write_text("old")

    syntax_ok, structure_ok, message, wrote = _write_output_atomically(
        target, "new", preserve_on_failure=True
    )

    assert (syntax_ok, structure_ok, message, wrote) == (True, True, "", True)
    assert target.read_text() == "new"
    assert not any(p.name.endswith(".tmp") for p in tmp_path.iterdir())


def test_atomic_write_keeps_target_when_syntax_fails(tmp_path, monkeypatch):
    monkeypatch.setattr(
        decompile, "validate_php_syntax", lambda path: (False, "parse error")
    )
    target = tmp_path / "out.php"
    target.write_text("old")

    syntax_ok, structure_ok, message, wrote = _write_output_atomically(
        target, "new", preserve_on_failure=True
    )

    assert (syntax_ok, structure_ok, message, wrote) == (False, True, "parse error", False)
    assert target.read_text() == "old"
    assert not any(p.name.endswith(".tmp") for p in tmp_path.iterdir())


def test_atomic_write_keeps_invalid_output_for_non_in_place_target(tmp_path, monkeypatch):
    monkeypatch.setattr(
        decompile, "validate_php_syntax", lambda path: (False, "parse error")
    )
    target = tmp_path / "out.php"
    target.write_text("old")

    syntax_ok, structure_ok, message, wrote = _write_output_atomically(
        target, "new", preserve_on_failure=False
    )

    assert (syntax_ok, structure_ok, message, wrote) == (False, True, "parse error", True)
    assert target.read_text() == "new"
    assert not any(p.name.endswith(".tmp") for p in tmp_path.iterdir())


def test_atomic_write_rejects_empty_control_flow_body(tmp_path, monkeypatch):
    monkeypatch.setattr(decompile, "validate_php_syntax", lambda path: (True, ""))
    target = tmp_path / "out.php"
    target.write_text("old")

    syntax_ok, structure_ok, message, wrote = _write_output_atomically(
        target, "<?php\nif ($x) {\n}\n", preserve_on_failure=True
    )

    assert (syntax_ok, structure_ok, wrote) == (True, False, False)
    assert "empty if body" in message
    assert target.read_text() == "old"
    assert not any(p.name.endswith(".tmp") for p in tmp_path.iterdir())


def test_atomic_write_keeps_structurally_invalid_output_for_non_in_place_target(
    tmp_path, monkeypatch
):
    monkeypatch.setattr(decompile, "validate_php_syntax", lambda path: (True, ""))
    target = tmp_path / "out.php"

    syntax_ok, structure_ok, _message, wrote = _write_output_atomically(
        target, "<?php\nif ($x) {\n}\n", preserve_on_failure=False
    )

    assert (syntax_ok, structure_ok, wrote) == (True, False, True)
    assert target.read_text() == "<?php\nif ($x) {\n}\n"


def test_main_returns_two_when_syntax_check_fails(tmp_path, monkeypatch):
    source = tmp_path / "input.php"
    source.write_text("x")
    monkeypatch.setattr(
        decompile, "decompile_file", lambda *args, **kwargs: (True, False, None, {})
    )
    monkeypatch.setattr(decompile.sys, "argv", ["decompile.py", str(source)])

    assert decompile.main() == 2


def test_decompile_file_keeps_in_place_source_on_syntax_failure(tmp_path, monkeypatch):
    source = tmp_path / "encoded.php"
    source.write_text("original-bytes")
    fake_dump = {
        "format": "icdump-ir-v1",
        "source_file": str(source),
        "entry": "main",
        "op_arrays": {},
    }
    monkeypatch.setattr(
        decompile, "dump_file_to_ir", lambda *args, **kwargs: (fake_dump, "", {})
    )
    monkeypatch.setattr(
        decompile, "validate_php_syntax", lambda path: (False, "parse error")
    )

    success, syntax_ok, error, status = decompile.decompile_file(
        source, source, silent_header=True
    )

    assert (success, syntax_ok) == (False, False)
    assert error == "parse error"
    assert status["syntax"] == {"ok": False, "message": "parse error"}
    assert source.read_text() == "original-bytes"
    assert not any(p.name.endswith(".tmp") for p in tmp_path.iterdir())


def test_decompile_file_reports_empty_control_flow_and_preserves_source(
    tmp_path, monkeypatch
):
    source = tmp_path / "encoded.php"
    source.write_text("original-bytes")
    fake_dump = {
        "format": "icdump-ir-v1",
        "source_file": str(source),
        "entry": "main",
        "op_arrays": {},
    }
    monkeypatch.setattr(
        decompile, "dump_file_to_ir", lambda *args, **kwargs: (fake_dump, "", {})
    )
    monkeypatch.setattr(
        decompile, "clean_php_source", lambda code: "<?php\nif ($x) {\n}\n"
    )
    monkeypatch.setattr(decompile, "validate_php_syntax", lambda path: (True, ""))

    success, valid, error, status = decompile.decompile_file(
        source, source, silent_header=True
    )

    assert (success, valid) == (False, False)
    assert error == "line 2: empty if body"
    assert status["syntax"] == {"ok": True, "message": ""}
    assert status["structure"] == {"ok": False, "message": "line 2: empty if body"}
    assert source.read_text() == "original-bytes"
    assert not any(p.name.endswith(".tmp") for p in tmp_path.iterdir())
