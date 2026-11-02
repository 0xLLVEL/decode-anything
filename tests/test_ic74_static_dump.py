"""The 7.4 static dumper must reproduce the runtime dumper's structural inventory.

Sample: `loader/refs/ic74dump-opcodes/` ships an encoder-15.0.1 artifact for PHP
7.4 next to `contacts.opcodes.json`, the runtime dumper's 113 op_arrays. Nothing
here runs PHP: the container gates, the body inflate and the field block are all
read out of the encoded file.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tools.ic74_static_dump import compare_with_truth, decode_body, scan_body  # noqa: E402

SAMPLE = ROOT / "loader" / "refs" / "ic74dump-opcodes" / "contacts.php"
TRUTH = SAMPLE.with_suffix(".opcodes.json")


pytestmark = pytest.mark.skipif(
    not (SAMPLE.exists() and TRUTH.exists()), reason="7.4 sample not vendored"
)


@pytest.fixture(scope="module")
def report() -> dict:
    header, body = decode_body(SAMPLE)
    scanned = scan_body(body)
    return {"header": header, "body": body, "scanned": scanned}


def test_container_gates_pass(report):
    header = report["header"]

    assert header["md4_matches"] is True
    assert header["transition_checksum_matches"] is True
    assert header["header_trailer"]["php_version_code"] == 74
    assert (
        header["header_trailer"]["encoder_major"],
        header["header_trailer"]["encoder_minor"],
    ) == (15, 0)
    assert len(report["body"]) == 398440


def test_every_runtime_op_array_is_found(report):
    entries = report["scanned"]["entries"]

    assert len(entries) == 112
    names = {entry["name"] for entry in entries}
    assert "addSendGroup" in names
    assert "getLicense" in names
    assert len(names) == len(entries)


def test_field_block_matches_the_runtime_dump(report):
    result = compare_with_truth({"entries": report["scanned"]["entries"]}, TRUTH)

    assert result["truth_op_arrays"] == 112
    assert result["matched"] == 112
    assert result["mismatched"] == []
    assert result["missing"] == []
    assert result["extra"] == []


def test_class_record_is_attributed(report):
    entries = report["scanned"]["entries"]
    classes = [item["name"] for item in report["scanned"]["classes"]]

    assert classes == ["ModelMarketingContacts"]
    owned = [entry for entry in entries if entry.get("class") == "ModelMarketingContacts"]
    assert len(owned) == len(entries)


def test_known_entry_values(report):
    by_name = {entry["name"]: entry for entry in report["scanned"]["entries"]}

    add = by_name["addSendGroup"]
    assert (add["opcodes"], add["variables"], add["temps"], add["literals"]) == (30, 2, 18, 22)
    assert (add["line_start"], add["line_end"]) == (5, 10)

    total = by_name["getTotalSendGroups"]
    assert (total["opcodes"], total["variables"], total["literals"]) == (12, 1, 11)
    assert (total["line_start"], total["line_end"]) == (46, 50)


def test_json_report_is_serialisable(tmp_path, report):
    payload = {
        "format": "ic74-static-v1",
        "entries": report["scanned"]["entries"],
        "classes": [{"name": item["name"]} for item in report["scanned"]["classes"]],
    }
    path = tmp_path / "report.json"
    path.write_text(json.dumps(payload), encoding="utf-8")

    assert json.loads(path.read_text(encoding="utf-8"))["format"] == "ic74-static-v1"
