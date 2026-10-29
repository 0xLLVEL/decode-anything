"""End-to-end corpus tests for the full decode pipeline.

Every case is an encoded PHP file under ``tests/corpus/<encoder>/`` that goes
through ``decompile_file`` and is compared with the committed golden output.
See ``tests/corpus/README.md`` for provenance and regeneration.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from decompile import decompile_file

CORPUS = Path(__file__).parent / "corpus"
BUILDER = Path(__file__).parents[1] / "tools" / "build_corpus_fixtures.py"
PHP_AVAILABLE = shutil.which("php") is not None


def _normalized(path: Path) -> str:
    return path.read_text(encoding="utf-8").replace("\r\n", "\n").strip() + "\n"


@pytest.mark.parametrize(
    ("case", "encoder"),
    [
        pytest.param("yakpro", "yakpro", id="yakpro"),
        pytest.param("sourceguardian", "SourceGuardian", id="sourceguardian"),
    ],
)
def test_encoded_corpus_decodes_to_golden(tmp_path, case, encoder):
    encoded = CORPUS / case / "hello.php"
    expected = CORPUS / case / "hello.expected.php"
    output = tmp_path / "hello.decoded.php"
    original = encoded.read_bytes()

    ok, valid, error, status = decompile_file(encoded, output, silent_header=True)

    assert ok is True, error
    assert error is None
    assert output.exists()
    assert encoded.read_bytes() == original
    reported = status.get("encoder") or status.get("type")
    assert reported == encoder
    assert _normalized(output) == _normalized(expected)
    if PHP_AVAILABLE:
        assert valid is True, status.get("syntax") or status.get("structure")


def test_sourceguardian_fixture_is_reproducible(tmp_path):
    target = tmp_path / "hello.php"

    result = subprocess.run(
        [sys.executable, str(BUILDER), "--output", str(target)],
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr
    committed = (CORPUS / "sourceguardian" / "hello.php").read_bytes()
    assert target.read_bytes() == committed
