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

from tools.ic74_static_dump import (  # noqa: E402
    compare_with_truth,
    decode_body,
    op_block_start,
    scan_body,
    walk_ops,
)
from tools.ic74_mask import (  # noqa: E402
    find_seed,
    key_stubs,
    predict,
    record_opcodes,
    stored_bytes,
)

# Mask stream for ``getTotalSendGroups``, recovered as ``stored_byte ^ opcode``
# from the runtime dump (docs/ioncube-74-static.md) and pinned for the walk.
TOTAL_SEND_GROUPS_MASK = bytes(
    [0x90, 0x2B, 0x8D, 0x91, 0x6E, 0xC2, 0xB7, 0x8A, 0x1A, 0xD4, 0xC2, 0xB2]
)

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


def test_word_walk_reproduces_the_runtime_opcodes(report):
    truth = json.loads(TRUTH.read_text(encoding="utf-8"))["op_arrays"]
    expected = next(
        value for value in truth.values() if value["function_name"]["value"] == "getTotalSendGroups"
    )["opcodes"]
    entry = next(
        item for item in report["scanned"]["entries"] if item["name"] == "getTotalSendGroups"
    )

    start = op_block_start(report["body"], entry["end"])
    ops, end = walk_ops(report["body"], start, len(expected), TOTAL_SEND_GROUPS_MASK)

    assert [op["opcode"] for op in ops] == [item["opcode"] for item in expected]
    assert end == 0x25C7  # the record's literal table starts right here


def test_word_walk_recovers_cache_slots(report):
    truth = json.loads(TRUTH.read_text(encoding="utf-8"))["op_arrays"]
    expected = next(
        value for value in truth.values() if value["function_name"]["value"] == "getTotalSendGroups"
    )["opcodes"]
    entry = next(
        item for item in report["scanned"]["entries"] if item["name"] == "getTotalSendGroups"
    )

    start = op_block_start(report["body"], entry["end"])
    ops, _ = walk_ops(report["body"], start, len(expected), TOTAL_SEND_GROUPS_MASK)

    slots = [op["slot"] for op in ops if op["slot"] is not None]
    assert slots == [item["extended_value"] for item in expected if item["extended_value"] not in (0,)]


FE_FETCH = "ZEND_FE_FETCH_R"


def test_every_op_block_start_matches_the_runtime_slot_pattern(report):
    """The derived start must place a cache slot on exactly the ops the dump says.

    Slot values must agree too, except on ``ZEND_FE_FETCH_R``: its word holds the
    jump target relative to the op_array, while the dumper reports the resolved
    byte offset.
    """

    truth = json.loads(TRUTH.read_text(encoding="utf-8"))["op_arrays"]
    expected = {
        value["function_name"]["value"]: value for value in truth.values()
    }

    compared = 0
    for entry in report["scanned"]["entries"]:
        want = expected[entry["name"]]
        ops = want["opcodes"]
        start = op_block_start(report["body"], entry["end"])
        walk, _ = walk_ops(report["body"], start, len(ops), bytes(len(ops)))

        assert [i for i, op in enumerate(walk) if op["slot"] is not None] == [
            i for i, op in enumerate(ops) if op["extended_value"] not in (0,)
        ], entry["name"]

        for got, op in zip(walk, ops):
            if got["slot"] is None or op["opcode_name"] == FE_FETCH:
                continue
            assert got["slot"] == op["extended_value"], (entry["name"], op["opcode_name"])
            compared += 1

    assert compared == 1731


def test_mask_stream_decodes_a_record_from_its_key_pair(report):
    """`getTotalSendGroups` is masked by `A[i] ^ A[i + ops + 2]` from one pair.

    The pair sits at body `0x2447`, ahead of the record, and the stream it starts
    reproduces all twelve runtime opcodes - no runtime, no loader.
    """

    body = report["body"]
    xor_key = 0x00363FA4
    entry = next(item for item in report["scanned"]["entries"] if item["name"] == "getTotalSendGroups")
    start = op_block_start(body, entry["end"])
    mask = predict(0x1BB0, 0x59EA, xor_key, entry["opcodes"])
    opcodes = [stored ^ mask[i] for i, stored in enumerate(stored_bytes(body, start, 12))]

    assert opcodes == [
        0x52, 0x70, 0x63, 0x0A, 0x04, 0x74, 0x3C, 0x02, 0x52, 0x51, 0x3E, 0x3E,
    ]
    hidden = bytes(stored ^ want for stored, want in zip(stored_bytes(body, start, 12), opcodes))
    assert hidden == bytes(
        [0x90, 0x2B, 0x8D, 0x91, 0x6E, 0xC2, 0xB7, 0x8A, 0x1A, 0xD4, 0xC2, 0xB2]
    )
    assert find_seed(body, entry["offset"], 12, xor_key, hidden, 1400) == (
        0x2447, 0x1BB0, 0x59EA,
    )


def test_every_record_decodes_from_its_own_key_stub(report):
    """All 112 records, all 6061 opcodes, read out of the body alone.

    The pair is not searched for: each record owns a stub shaped
    ``[record id][s0][s1][8 zero bytes]`` and the id at ``+0x00`` of the field
    block is what binds it. 27 instructions double-XOR to the ``0x95`` sentinel
    and take the escape, where the ``A[i]`` term is dropped.
    """

    truth = json.loads(TRUTH.read_text(encoding="utf-8"))
    expected: dict[str, list[int]] = {}
    for item in (truth.get("op_arrays") or {}).values():
        name = item.get("function_name")
        name = name.get("value") if isinstance(name, dict) else name
        if name:
            expected[name] = [op["opcode"] for op in item.get("opcodes") or []]

    body = report["body"]
    xor_key = 0x00363FA4
    index = key_stubs(body)
    decoded = escapes = 0
    total = 0
    unseeded: set[str] = set()
    for entry in report["scanned"]["entries"]:
        want = expected[entry["name"]]
        opcodes, taken, stub = record_opcodes(body, entry, xor_key, index)
        if stub is None:
            unseeded.add(entry["name"])
            continue
        assert opcodes == want, entry["name"]
        decoded += 1
        escapes += taken
        total += len(opcodes)

    assert unseeded == set()
    assert decoded == 112
    assert total == 6061
    assert escapes == 27


def test_compare_with_truth_matches_every_opcode_stream(report):
    header, body = decode_body(SAMPLE)
    xor_key = int(str(header["initial_header"]["bytecode_xor_key"]), 0)
    index = key_stubs(body)
    entries = [dict(entry) for entry in report["scanned"]["entries"]]
    for entry in entries:
        opcodes, _, _ = record_opcodes(body, entry, xor_key, index)
        entry["opcode_bytes"] = opcodes

    result = compare_with_truth({"entries": entries}, TRUTH)

    assert result["matched"] == 112
    assert result["mismatched"] == []
    assert result["opcode_streams_matched"] == 112


def test_json_report_is_serialisable(tmp_path, report):
    payload = {
        "format": "ic74-static-v1",
        "entries": report["scanned"]["entries"],
        "classes": [{"name": item["name"]} for item in report["scanned"]["classes"]],
    }
    path = tmp_path / "report.json"
    path.write_text(json.dumps(payload), encoding="utf-8")

    assert json.loads(path.read_text(encoding="utf-8"))["format"] == "ic74-static-v1"
