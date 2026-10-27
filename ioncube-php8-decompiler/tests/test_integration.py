"""Integration tests against the real ionCube dumps (skipped if absent)."""

from pathlib import Path

import pytest

from php_reconstructor.decompiler import decompile_program, optimize
from php_reconstructor.emitter import emit_php
from php_reconstructor.loader import load_dump

DUMP_DIR = Path(__file__).resolve().parents[2]
SAMPLE = DUMP_DIR / "sample.opcodes.json"

needs_sample = pytest.mark.skipif(not SAMPLE.exists(), reason="real dump not available")


@needs_sample
def test_sample_dump_reconstructs_cleanly():
    program = load_dump(SAMPLE)
    text = emit_php(optimize(decompile_program(program)))
    assert text.startswith("<?php")
    assert "class ModelModuleUkrcredits {" in text
    assert "public function checklicense() {" in text
    # No leaked internal temporaries and no fallback opcode comments.
    assert "$tmp" not in text
    assert "[opcode" not in text


@needs_sample
def test_sample_dump_deterministic():
    program1 = load_dump(SAMPLE)
    program2 = load_dump(SAMPLE)
    out1 = emit_php(optimize(decompile_program(program1)))
    out2 = emit_php(optimize(decompile_program(program2)))
    assert out1 == out2


@pytest.mark.parametrize("name", ["functions.opcodes.json", "contacts.opcodes.json"])
def test_large_dumps_do_not_crash(name):
    path = DUMP_DIR / name
    if not path.exists():
        pytest.skip("real dump not available")
    program = load_dump(path)
    text = emit_php(optimize(decompile_program(program)))
    assert text.startswith("<?php")
    assert "$tmp" not in text
