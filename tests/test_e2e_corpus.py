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
ENCODERS = {"yakpro": "yakpro", "sourceguardian": "SourceGuardian"}


def _cases() -> list:
    cases = []
    for directory in sorted(CORPUS.iterdir()):
        encoder = ENCODERS.get(directory.name)
        if encoder is None:
            continue
        for encoded in sorted(directory.glob("*.php")):
            if encoded.name.endswith(".expected.php"):
                continue
            expected = encoded.with_name(encoded.stem + ".expected.php")
            cases.append(
                pytest.param(
                    encoded,
                    expected,
                    encoder,
                    id=f"{directory.name}-{encoded.stem}",
                )
            )
    return cases


def _normalized(path: Path) -> str:
    return path.read_text(encoding="utf-8").replace("\r\n", "\n").strip() + "\n"


@pytest.mark.parametrize(("encoded", "expected", "encoder"), _cases())
def test_encoded_corpus_decodes_to_golden(tmp_path, encoded, expected, encoder):
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


@pytest.mark.parametrize("name", ["hello", "class"])
def test_sourceguardian_fixture_is_reproducible(tmp_path, name):
    target = tmp_path / f"{name}.php"

    result = subprocess.run(
        [sys.executable, str(BUILDER), "--name", name, "--output", str(target)],
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr
    committed = CORPUS / "sourceguardian" / f"{name}.php"
    # Compare text so a CRLF checkout does not fail the fixture check.
    assert target.read_text(encoding="ascii") == committed.read_text(encoding="ascii")
