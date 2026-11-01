"""Tests for the project scanner: counts, version breakdown, progress bar."""

import json
from pathlib import Path

import pytest

from detector.scanner import (
    PROJECT_URL,
    REPORT_WIDTH,
    _ProgressBar,
    print_scan_report,
    scan_project,
)

CORPUS = Path("tests/corpus/sourceguardian")

YAKPRO = """<?php
/* Obfuscated by YAK Pro - Php Obfuscator 2.0.6 */
$v1 = "\\x41";
goto a; a: goto b; b: goto c; c: goto d; d: echo $v1;
"""


class FakeTty:
    encoding = "utf-8"

    def __init__(self, tty=True):
        self.chunks = []
        self._tty = tty

    def isatty(self):
        return self._tty

    def write(self, text):
        self.chunks.append(text)

    def flush(self):
        pass

    @property
    def text(self):
        return "".join(self.chunks)


def _project(root: Path) -> Path:
    (root / "app" / "sub").mkdir(parents=True)
    (root / "app" / "plain.php").write_text("<?php echo 'hi';\n", encoding="utf-8")
    (root / "app" / "yak.php").write_text(YAKPRO, encoding="utf-8")
    (root / "app" / "notes.txt").write_text("not php\n", encoding="utf-8")
    if CORPUS.exists():
        (root / "app" / "sg.php").write_bytes((CORPUS / "class.php").read_bytes())
    return root


def test_scan_counts_and_breakdown(tmp_path):
    report = scan_project(_project(tmp_path), progress=False)

    assert report.total_files_scanned == 4
    assert report.total_php_files == 3
    assert report.clean_php_count == 1
    assert report.encoder_summary == {"YAK Pro": 1, "SourceGuardian": 1}

    groups = report.encoder_groups()
    assert groups["YAK Pro"] == {"obfuscator 2.0.6": 1}
    assert groups["SourceGuardian"] == {"container v33": 1}


def test_scan_reports_versions_from_the_file(tmp_path):
    report = scan_project(_project(tmp_path), progress=False)
    by_name = {f.match.name: f.match for f in report.encoded_files}

    yak = by_name["YAK Pro"]
    assert yak.toolchain == "obfuscator 2.0.6"
    assert yak.php_version is None

    sg = by_name["SourceGuardian"]
    assert sg.toolchain == "container v33"


def test_broken_ioncube_payload_still_detected(tmp_path):
    sample = tmp_path / "broken.php"
    sample.write_bytes(b"<?php if(!extension_loaded('ionCube Loader')){}  HR+c garbage")
    report = scan_project(tmp_path, progress=False)

    assert report.encoded_count == 1
    match = report.encoded_files[0].match
    assert match.name == "ionCube"
    assert "header parse failed" in match.details


def test_json_output_carries_versions(tmp_path):
    document = scan_project(_project(tmp_path), progress=False).to_dict()

    assert document["total_php_files"] == 3
    assert document["clean_php_count"] == 1
    assert document["encoded_ratio"] == pytest.approx(2 / 3, abs=1e-4)
    assert document["encoder_groups"]["SourceGuardian"] == {"container v33": 1}
    assert {"php_version", "tool_version", "encoder"} <= set(document["files"][0])


def test_progress_bar_draws_and_clears_on_tty():
    stream = FakeTty()
    bar = _ProgressBar(4, stream=stream, enabled=True)
    bar.update(0, "a.php")
    bar.update(2, "b.php")
    bar.update(4)
    bar.close()

    frames = [chunk for chunk in stream.text.split("\r") if chunk.strip()]
    assert len(frames) == 3
    assert "2/4" in stream.text
    assert stream.text.endswith("\r")


def test_progress_bar_is_silent_off_tty():
    stream = FakeTty(tty=False)
    bar = _ProgressBar(4, stream=stream, enabled=True)
    bar.update(1, "a.php")
    bar.close()
    assert stream.text == ""


def test_report_prints_clean_message_when_nothing_found(tmp_path, capsys):
    (tmp_path / "plain.php").write_text("<?php echo 1;\n", encoding="utf-8")
    report = scan_project(tmp_path, progress=False)
    print_scan_report(report)
    output = capsys.readouterr().out

    assert "decode-anything".center(REPORT_WIDTH) in output
    assert f"source: {PROJECT_URL}".center(REPORT_WIDTH) in output
    assert "=" * 10 not in output
    assert "No encoded or obfuscated files detected" in output


def test_report_lists_variants_and_caps_the_file_list(tmp_path, capsys):
    for index in range(45):
        (tmp_path / f"f{index}.php").write_text(YAKPRO, encoding="utf-8")
    report = scan_project(tmp_path, progress=False)
    print_scan_report(report)
    output = capsys.readouterr().out

    assert "45 encoded files across 1 encoder" in output
    assert "obfuscator 2.0.6" in output
    assert "... and 5 more (use --json for the full list)" in output


def test_json_is_machine_readable(tmp_path):
    document = json.loads(json.dumps(scan_project(_project(tmp_path), progress=False).to_dict()))
    assert document["root_path"].endswith(str(tmp_path))
