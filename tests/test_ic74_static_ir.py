"""The static 7.4 body reaches ``icdump-ir-v1``, operands included.

Pinned here: record identity, opcode bytes, line ranges, class/method indexing,
the literal pool, the CV names and the operand slot of every live operand.
What is *not* pinned is the jump destination: a branch operand in the body is
not the opline the loader reports, so ``decompile.py`` still routes 7.4 through
the runtime dump until that encoding is read.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "ioncube-php8-decompiler" / "src"))

from engines.ioncube.static74 import document, static74_icdump  # noqa: E402

SAMPLE = ROOT / "loader" / "refs" / "ic74dump-opcodes" / "contacts.php"
TRUTH = ROOT / "loader" / "refs" / "ic74dump-opcodes" / "contacts.opcodes.json"


@pytest.fixture(scope="module")
def icdump() -> dict:
    return static74_icdump(SAMPLE)


@pytest.fixture(scope="module")
def truth() -> dict[str, dict]:
    data = json.loads(TRUTH.read_text(encoding="utf-8"))
    out: dict[str, dict] = {}
    for item in (data.get("op_arrays") or {}).values():
        name = item.get("function_name")
        name = name.get("value") if isinstance(name, dict) else name
        if name:
            out[name] = item
    return out


def test_every_record_becomes_an_op_array(icdump, truth):
    entries = icdump["op_arrays"]
    assert icdump["format"] == "icdump-ir-v1"
    assert len(entries) == 112
    names = {entry["function_name"]["value"] for entry in entries.values()}
    assert names == set(truth)


def test_the_class_owns_all_of_them(icdump):
    classes = icdump["class_index"]
    assert list(classes) == ["class:4d6f64656c4d61726b6574696e67436f6e7461637473"]
    owner = classes["class:4d6f64656c4d61726b6574696e67436f6e7461637473"]
    assert owner["name"] == "ModelMarketingContacts"
    assert len(owner["methods"]) == 112
    assert all(entry["kind"] == "method" for entry in icdump["op_arrays"].values())


def test_opcode_streams_match_the_runtime_dump(icdump, truth):
    mismatched = []
    for name, want in truth.items():
        entry = next(
            item
            for item in icdump["op_arrays"].values()
            if item["function_name"]["value"] == name
        )
        got = [op["opcode"] for op in entry["opcodes"]]
        if got != [op["opcode"] for op in want["opcodes"]]:
            mismatched.append(name)
    assert mismatched == []


def test_line_ranges_and_counts_match(icdump, truth):
    for name, want in truth.items():
        entry = next(
            item
            for item in icdump["op_arrays"].values()
            if item["function_name"]["value"] == name
        )
        assert (entry["line_start"], entry["line_end"]) == (
            want["line_start"],
            want["line_end"],
        ), name
        assert len(entry["opcodes"]) == len(want["opcodes"]), name


def _by_name(icdump: dict, truth: dict[str, dict]) -> list[tuple[dict, dict]]:
    pairs = []
    for name, want in truth.items():
        entry = next(
            item
            for item in icdump["op_arrays"].values()
            if item["function_name"]["value"] == name
        )
        pairs.append((entry, want))
    return pairs


def test_every_live_operand_matches_the_runtime_dump(icdump, truth):
    checked = 0
    mismatched = []
    for entry, want in _by_name(icdump, truth):
        for got_op, want_op in zip(entry["opcodes"], want["opcodes"]):
            for key in ("op1", "op2", "result"):
                if want_op[key]["type"] == 0:
                    continue
                checked += 1
                if (got_op[key]["type"], got_op[key]["var"]) != (
                    want_op[key]["type"],
                    want_op[key]["var"],
                ):
                    mismatched.append((entry["function_name"]["value"], got_op["index"], key))
    assert checked == 11473
    assert mismatched == []


def test_cv_names_come_from_the_pool(truth):
    static = {
        entry["function_name"]: entry
        for entry in document(SAMPLE)["op_arrays"].values()
    }
    for name, want in truth.items():
        entry = static[name]
        assert entry["vars"] == [item["value"] for item in want["vars"]["value"]]
        for got_op, want_op in zip(entry["opcodes"], want["opcodes"]):
            for key in ("op1", "op2", "result"):
                if want_op[key]["type"] != 8:
                    continue
                assert got_op[key]["cv_name"] == want_op[key]["cv_name"]


def test_literals_match_the_runtime_dump(icdump, truth):
    for entry, want in _by_name(icdump, truth):
        got, expected = entry["literals"], want["literals"]
        assert len(got) == len(expected)
        for got_lit, want_lit in zip(got, expected):
            assert got_lit["type"] == want_lit["type"]
            if want_lit["type"] == "string" and want_lit["value"] is not None:
                assert got_lit["value"] == want_lit["value"]
            elif want_lit["type"] in ("int", "bool", "null"):
                assert got_lit["value"] == want_lit["value"]


def test_status_reports_the_static_operand_source(icdump):
    status = icdump["summary"]["decompile_status"]
    assert status["status"] == "static_body"
    assert status["operands"] == "static"


def test_static_summary_counts(icdump):
    static = icdump["summary"]["static_74"]
    assert static["opcode_total"] == 6061
    assert static["opcode_escapes"] == 27
    assert static["unseeded"] == []
    assert static["opcode_names"] is True


def test_document_is_deterministic():
    first = document(SAMPLE)["summary"]
    second = document(SAMPLE)["summary"]
    assert first == second


def test_the_ast_layer_accepts_the_document(icdump):
    from php_reconstructor.loader.json_loader import parse_dump

    program = parse_dump(icdump)
    assert len(program.op_arrays) == 112
