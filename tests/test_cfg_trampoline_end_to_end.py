"""End-to-end regressions for CFG rewriting and loop reconstruction.

The trampoline fixtures keep the scrambled block order the rewriter exists
for: a conditional's fallthrough is a one-op ``JMP`` trampoline, not the body.
Feeding them through ``deobfuscate_cfg`` and then the normal reconstruction
pipeline must produce real ``if``/loop bodies rather than empty branches.
"""

from __future__ import annotations

import copy
import json
import re
import sys
from pathlib import Path

SRC = Path(__file__).resolve().parents[1] / "ioncube-php8-decompiler" / "src"
sys.path.insert(0, str(SRC))

from dump_plain_file_static import deobfuscate_cfg  # noqa: E402
from php_reconstructor.decompiler import decompile_program, optimize  # noqa: E402
from php_reconstructor.emitter import emit_php  # noqa: E402
from php_reconstructor.loader import parse_dump  # noqa: E402

FIXTURE = Path(__file__).parent / "fixtures" / "cfg_conditional_trampoline.json"
FUNCTION_ID = "function:63686f6f7365"

NESTED_FIXTURE = Path(__file__).parent / "fixtures" / "cfg_nested_trampolines.json"
NESTED_FUNCTION_ID = "function:636c617373696679"

JMPNZ_FIXTURE = Path(__file__).parent / "fixtures" / "cfg_nested_jmpnz_trampolines.json"
JMPNZ_FUNCTION_ID = "function:636c617373696679"

LOOP_FIXTURE = Path(__file__).parent / "fixtures" / "cfg_loop_nested_conditional.json"
LOOP_FUNCTION_ID = "function:7363616e5f6c6f6f70"

WHILE_FIXTURE = Path(__file__).parent / "fixtures" / "cfg_while_nested_conditional.json"
WHILE_FUNCTION_ID = "function:7768696c655f7363616e"

BREAK_FIXTURE = Path(__file__).parent / "fixtures" / "cfg_while_break_continue.json"
BREAK_FUNCTION_ID = "function:6c6f6f705f6578697473"

EXIT_FIXTURE = Path(__file__).parent / "fixtures" / "cfg_conditional_exit_jumps.json"
EXIT_FUNCTION_ID = "function:657869745f6775617264"

CONVERGE_FIXTURE = Path(__file__).parent / "fixtures" / "cfg_converging_branches.json"
CONVERGE_FUNCTION_ID = "function:636f6e7665726765"

LOOP_GUARD_FIXTURE = Path(__file__).parent / "fixtures" / "cfg_loop_guard.json"
LOOP_GUARD_FUNCTION_ID = "function:6c6f6f705f6775617264"

FOREACH_FIXTURE = Path(__file__).parent / "fixtures" / "cfg_foreach_header_trampoline.json"
FOREACH_FUNCTION_ID = "function:666f72656163685f7363616e"

FOREACH_NOP_FIXTURE = Path(__file__).parent / "fixtures" / "cfg_foreach_nop_merge.json"
FOREACH_NOP_FUNCTION_ID = "function:666f72656163685f6e6f705f6d65726765"

CLOSURE_FIXTURE = Path(__file__).parent / "fixtures" / "cfg_closure_backward_trampoline.json"
CLOSURE_FUNCTION_ID = (
    "function:6764706c617965725c636f72655c7b636c6f737572657d#closure_2"
)

BACKWARD_STUB_FIXTURE = Path(__file__).parent / "fixtures" / "cfg_backward_forward_stub.json"
BACKWARD_STUB_FUNCTION_ID = "function:6261636b776172645f73747562"

ENTRY_INIT_FIXTURE = Path(__file__).parent / "fixtures" / "cfg_entry_init_dead_return.json"
ENTRY_DEAD_FUNCTION_ID = "function:656e7472795f64656164"
ENTRY_COMMON_FUNCTION_ID = "function:656e7472795f636f6d6d6f6e"


def _rewrite_fixture(fixture: Path, function_id: str) -> tuple[dict, list[dict]]:
    raw = json.loads(fixture.read_text(encoding="utf-8"))
    original_ops = copy.deepcopy(raw["op_arrays"][function_id]["opcodes"])

    rewritten = copy.deepcopy(raw)
    for oa_id, entry in rewritten["op_arrays"].items():
        rewritten["op_arrays"][oa_id] = deobfuscate_cfg(entry)
    return rewritten, original_ops


def _load_rewritten() -> tuple[dict, list[dict]]:
    return _rewrite_fixture(FIXTURE, FUNCTION_ID)


def _load_nested_rewritten() -> tuple[dict, list[dict]]:
    return _rewrite_fixture(NESTED_FIXTURE, NESTED_FUNCTION_ID)


def _load_jmpnz_rewritten() -> tuple[dict, list[dict]]:
    return _rewrite_fixture(JMPNZ_FIXTURE, JMPNZ_FUNCTION_ID)


def _load_loop_rewritten() -> tuple[dict, list[dict]]:
    return _rewrite_fixture(LOOP_FIXTURE, LOOP_FUNCTION_ID)


def _load_while_rewritten() -> tuple[dict, list[dict]]:
    return _rewrite_fixture(WHILE_FIXTURE, WHILE_FUNCTION_ID)


def _load_break_rewritten() -> tuple[dict, list[dict]]:
    return _rewrite_fixture(BREAK_FIXTURE, BREAK_FUNCTION_ID)


def _load_exit_rewritten() -> tuple[dict, list[dict]]:
    return _rewrite_fixture(EXIT_FIXTURE, EXIT_FUNCTION_ID)


def _load_converge_rewritten() -> tuple[dict, list[dict]]:
    return _rewrite_fixture(CONVERGE_FIXTURE, CONVERGE_FUNCTION_ID)


def _load_loop_guard_rewritten() -> tuple[dict, list[dict]]:
    return _rewrite_fixture(LOOP_GUARD_FIXTURE, LOOP_GUARD_FUNCTION_ID)


def _load_foreach_rewritten() -> tuple[dict, list[dict]]:
    return _rewrite_fixture(FOREACH_FIXTURE, FOREACH_FUNCTION_ID)


def _load_foreach_nop_rewritten() -> tuple[dict, list[dict]]:
    return _rewrite_fixture(FOREACH_NOP_FIXTURE, FOREACH_NOP_FUNCTION_ID)


def _load_closure_rewritten() -> tuple[dict, list[dict]]:
    return _rewrite_fixture(CLOSURE_FIXTURE, CLOSURE_FUNCTION_ID)


def _load_backward_stub_rewritten() -> tuple[dict, list[dict]]:
    return _rewrite_fixture(BACKWARD_STUB_FIXTURE, BACKWARD_STUB_FUNCTION_ID)


def _load_entry_init_rewritten(function_id: str) -> tuple[dict, list[dict]]:
    return _rewrite_fixture(ENTRY_INIT_FIXTURE, function_id)


def test_conditional_trampoline_is_removed():
    rewritten, original_ops = _load_rewritten()

    assert [op["opcode_name"] for op in original_ops[1:3]] == ["ZEND_JMPZ", "ZEND_JMP"]
    new_ops = rewritten["op_arrays"][FUNCTION_ID]["opcodes"]
    assert "ZEND_JMP" not in [op["opcode_name"] for op in new_ops]
    assert [op["opcode_name"] for op in new_ops[:4]] == [
        "ZEND_RECV",
        "ZEND_JMPZ",
        "ZEND_RETURN",
        "ZEND_RETURN",
    ]


def test_rewritten_fixture_reconstructs_non_empty_if_body():
    rewritten, _ = _load_rewritten()

    php = emit_php(optimize(decompile_program(parse_dump(rewritten))))

    assert "function choose($x) {" in php
    assert "if ($x) {" in php
    assert "return 'yes';" in php
    assert "return 'no';" in php
    assert not re.search(r"if \(\$x\) \{\s*\}", php)

    normalized = php.replace("\r\n", "\n")
    assert "if ($x) {\n        return 'yes';\n    }\n    return 'no';" in normalized


def test_nested_trampolines_are_removed_and_ordered():
    rewritten, original_ops = _load_nested_rewritten()

    assert [op["opcode_name"] for op in original_ops[2:6]] == [
        "ZEND_JMPZ",
        "ZEND_JMP",
        "ZEND_JMPZ",
        "ZEND_JMP",
    ]

    new_ops = rewritten["op_arrays"][NESTED_FUNCTION_ID]["opcodes"]
    assert "ZEND_JMP" not in [op["opcode_name"] for op in new_ops]
    assert [op["opcode_name"] for op in new_ops[:4]] == [
        "ZEND_RECV",
        "ZEND_RECV",
        "ZEND_JMPZ",
        "ZEND_JMPZ",
    ]
    assert new_ops[2]["jump_targets"] == [6]
    assert new_ops[3]["jump_targets"] == [5]


def test_nested_fixture_reconstructs_nested_ifs():
    rewritten, _ = _load_nested_rewritten()

    php = emit_php(optimize(decompile_program(parse_dump(rewritten))))
    normalized = php.replace("\r\n", "\n")

    assert "function classify($a, $b) {" in normalized
    expected = (
        "    if ($a) {\n"
        "        if ($b) {\n"
        "            return 'ab';\n"
        "        }\n"
        "        return 'a';\n"
        "    }\n"
        "    return 'none';"
    )
    assert expected in normalized
    assert not re.search(r"if \(\$[ab]\) \{\s*\}", normalized)


def test_jmpnz_trampolines_preserve_branch_direction():
    rewritten, original_ops = _load_jmpnz_rewritten()

    assert [op["opcode_name"] for op in original_ops[2:6]] == [
        "ZEND_JMPNZ",
        "ZEND_JMP",
        "ZEND_JMPNZ",
        "ZEND_JMP",
    ]

    new_ops = rewritten["op_arrays"][JMPNZ_FUNCTION_ID]["opcodes"]
    assert "ZEND_JMP" not in [op["opcode_name"] for op in new_ops]
    assert [op["opcode_name"] for op in new_ops[:4]] == [
        "ZEND_RECV",
        "ZEND_RECV",
        "ZEND_JMPZ",
        "ZEND_JMPZ",
    ]
    assert new_ops[2]["jump_targets"] == [6]
    assert new_ops[3]["jump_targets"] == [5]


def test_jmpnz_fixture_keeps_positive_conditions():
    rewritten, _ = _load_jmpnz_rewritten()

    php = emit_php(optimize(decompile_program(parse_dump(rewritten))))
    normalized = php.replace("\r\n", "\n")

    expected = (
        "    if ($a) {\n"
        "        if ($b) {\n"
        "            return 'ab';\n"
        "        }\n"
        "        return 'a';\n"
        "    }\n"
        "    return 'none';"
    )
    assert expected in normalized
    assert "if (!$a)" not in normalized
    assert "if (!$b)" not in normalized


def test_loop_nested_trampolines_are_scheduled_in_order():
    rewritten, original_ops = _load_loop_rewritten()

    assert [op["opcode_name"] for op in original_ops[3:10]] == [
        "ZEND_JMPZ",
        "ZEND_JMP",
        "ZEND_JMPZ",
        "ZEND_JMP",
        "ZEND_ECHO",
        "ZEND_JMP",
        "ZEND_JMPNZ",
    ]

    new_ops = rewritten["op_arrays"][LOOP_FUNCTION_ID]["opcodes"]
    assert [op["opcode_name"] for op in new_ops] == [
        "ZEND_RECV",
        "ZEND_RECV",
        "ZEND_RECV",
        "ZEND_JMPZ",
        "ZEND_JMPZ",
        "ZEND_ECHO",
        "ZEND_JMPNZ",
        "ZEND_RETURN",
    ]
    assert new_ops[3]["jump_targets"] == [6]
    assert new_ops[4]["jump_targets"] == [6]
    assert new_ops[6]["jump_targets"] == [3]


def test_loop_fixture_reconstructs_do_while_with_nested_if():
    rewritten, _ = _load_loop_rewritten()

    php = emit_php(optimize(decompile_program(parse_dump(rewritten))))
    normalized = php.replace("\r\n", "\n")

    expected = (
        "function scan_loop($a, $b, $again) {\n"
        "    do {\n"
        "        if ($a) {\n"
        "            if ($b) {\n"
        "                echo 'ab';\n"
        "            }\n"
        "        }\n"
        "    } while ($again);"
    )
    assert expected in normalized
    assert "while (true)" not in normalized
    assert "goto " not in normalized


def test_while_loop_condition_survives_branch_rewrite():
    rewritten, original_ops = _load_while_rewritten()

    assert [op["opcode_name"] for op in original_ops[3:11]] == [
        "ZEND_JMPZ",
        "ZEND_JMPZ",
        "ZEND_JMP",
        "ZEND_JMPZ",
        "ZEND_JMP",
        "ZEND_ECHO",
        "ZEND_JMP",
        "ZEND_RETURN",
    ]

    new_ops = rewritten["op_arrays"][WHILE_FUNCTION_ID]["opcodes"]
    assert [op["opcode_name"] for op in new_ops] == [
        "ZEND_RECV",
        "ZEND_RECV",
        "ZEND_RECV",
        "ZEND_JMPZ",
        "ZEND_JMPZ",
        "ZEND_JMPZ",
        "ZEND_ECHO",
        "ZEND_JMP",
        "ZEND_RETURN",
    ]
    assert new_ops[3]["jump_targets"] == [8]
    assert new_ops[4]["jump_targets"] == [7]
    assert new_ops[5]["jump_targets"] == [7]
    assert new_ops[7]["jump_targets"] == [3]


def test_while_fixture_reconstructs_while_with_nested_if():
    rewritten, _ = _load_while_rewritten()

    php = emit_php(optimize(decompile_program(parse_dump(rewritten))))
    normalized = php.replace("\r\n", "\n")

    expected = (
        "function while_scan($a, $b, $again) {\n"
        "    while ($again) {\n"
        "        if ($a) {\n"
        "            if ($b) {\n"
        "                echo 'ab';\n"
        "            }\n"
        "        }\n"
        "    }"
    )
    assert expected in normalized
    assert "do {" not in normalized
    assert "goto " not in normalized


def test_conditional_exit_jumps_are_not_folded():
    rewritten, original_ops = _load_exit_rewritten()

    expected_names = [
        "ZEND_RECV",
        "ZEND_RECV",
        "ZEND_RECV",
        "ZEND_JMPZ",
        "ZEND_JMPZ",
        "ZEND_JMP",
        "ZEND_JMPZ",
        "ZEND_JMP",
        "ZEND_ECHO",
        "ZEND_JMP",
        "ZEND_RETURN",
    ]
    assert [op["opcode_name"] for op in original_ops] == expected_names

    new_ops = rewritten["op_arrays"][EXIT_FUNCTION_ID]["opcodes"]
    assert [op["opcode_name"] for op in new_ops] == expected_names
    assert new_ops[5]["jump_targets"] == [10]
    assert new_ops[7]["jump_targets"] == [3]
    assert new_ops[9]["jump_targets"] == [3]


def test_conditional_exit_fixture_has_no_empty_if():
    rewritten, _ = _load_exit_rewritten()

    php = emit_php(optimize(decompile_program(parse_dump(rewritten))))
    normalized = php.replace("\r\n", "\n")

    expected = (
        "function exit_guard($a, $b, $again) {\n"
        "    while ($again) {\n"
        "        if ($a) {\n"
        "            break;\n"
        "        }\n"
        "        if ($b) {\n"
        "            continue;\n"
        "        }\n"
        "        echo 'ab';\n"
        "    }"
    )
    assert expected in normalized
    assert not re.search(r"if \(\$[ab]\) \{\s*\}", normalized)


def test_converging_branch_fixture_is_not_rewritten():
    rewritten, original_ops = _load_converge_rewritten()
    new_ops = rewritten["op_arrays"][CONVERGE_FUNCTION_ID]["opcodes"]

    assert [op["opcode_name"] for op in new_ops] == [
        op["opcode_name"] for op in original_ops
    ]
    assert [op["jump_targets"] for op in new_ops] == [
        op["jump_targets"] for op in original_ops
    ]

    php = emit_php(optimize(decompile_program(parse_dump(rewritten))))
    normalized = php.replace("\r\n", "\n")
    assert "if ($a) {\n        return null;\n    }\n    return null;" in normalized
    assert not re.search(r"if \(\$a\) \{\s*\}", normalized)


def test_loop_guard_fixture_keeps_while_condition():
    rewritten, _ = _load_loop_guard_rewritten()
    new_ops = rewritten["op_arrays"][LOOP_GUARD_FUNCTION_ID]["opcodes"]

    assert [op["opcode_name"] for op in new_ops] == [
        "ZEND_RECV",
        "ZEND_JMPZ",
        "ZEND_ECHO",
        "ZEND_JMP",
        "ZEND_RETURN",
    ]
    assert new_ops[1]["jump_targets"] == [4]
    assert new_ops[3]["jump_targets"] == [1]

    php = emit_php(optimize(decompile_program(parse_dump(rewritten))))
    normalized = php.replace("\r\n", "\n")
    assert "while ($again) {\n        echo 'x';\n    }" in normalized
    assert "while (true)" not in normalized
    assert "goto " not in normalized


def test_foreach_header_survives_trampoline_rewrite():
    rewritten, original_ops = _load_foreach_rewritten()

    assert [op["opcode_name"] for op in original_ops] == [
        "ZEND_RECV",
        "ZEND_FE_RESET_R",
        "ZEND_FE_FETCH_R",
        "ZEND_JMPZ",
        "ZEND_JMP",
        "ZEND_ECHO",
        "ZEND_JMP",
        "ZEND_NOP",
        "ZEND_RETURN",
    ]

    new_ops = rewritten["op_arrays"][FOREACH_FUNCTION_ID]["opcodes"]
    assert [op["opcode_name"] for op in new_ops] == [
        "ZEND_RECV",
        "ZEND_FE_RESET_R",
        "ZEND_FE_FETCH_R",
        "ZEND_JMPZ",
        "ZEND_ECHO",
        "ZEND_NOP",
        "ZEND_RETURN",
    ]
    assert new_ops[1]["jump_targets"] == [5]
    assert new_ops[2]["jump_targets"] == [5]
    assert new_ops[3]["jump_targets"] == [2]

    php = emit_php(optimize(decompile_program(parse_dump(rewritten))))
    normalized = php.replace("\r\n", "\n")
    assert "foreach ($items as $item) {\n        if (!$item) {\n            continue;\n        }\n        echo 'x';\n    }" in normalized
    assert "goto " not in normalized


def test_foreach_nop_merge_chain_keeps_loop_structure():
    rewritten, original_ops = _load_foreach_nop_rewritten()

    assert [op["opcode_name"] for op in original_ops] == [
        "ZEND_RECV",
        "ZEND_FE_RESET_R",
        "ZEND_FE_FETCH_R",
        "ZEND_JMPZ",
        "ZEND_JMP",
        "ZEND_ECHO",
        "ZEND_JMP",
        "ZEND_NOP",
        "ZEND_JMP",
        "ZEND_FE_FREE",
        "ZEND_RETURN",
    ]
    assert original_ops[1]["jump_targets"] == [7]
    assert original_ops[2]["jump_targets"] == [7]
    assert original_ops[8]["jump_targets"] == [9]

    new_ops = rewritten["op_arrays"][FOREACH_NOP_FUNCTION_ID]["opcodes"]
    assert [op["opcode_name"] for op in new_ops] == [
        "ZEND_RECV",
        "ZEND_FE_RESET_R",
        "ZEND_FE_FETCH_R",
        "ZEND_JMPZ",
        "ZEND_ECHO",
        "ZEND_FE_FREE",
        "ZEND_RETURN",
    ]
    assert new_ops[1]["jump_targets"] == [5]
    assert new_ops[2]["jump_targets"] == [5]
    assert new_ops[3]["jump_targets"] == [2]

    php = emit_php(optimize(decompile_program(parse_dump(rewritten))))
    normalized = php.replace("\r\n", "\n")
    assert "foreach ($items as $item) {\n        if (!$item) {\n            continue;\n        }\n        echo 'x';\n    }" in normalized
    assert "while (true)" not in normalized
    assert "goto " not in normalized


def test_closure_backward_trampoline_is_scheduled_without_goto():
    rewritten, original_ops = _load_closure_rewritten()

    assert original_ops[1]["opcode_name"] == "ZEND_JMP"
    assert original_ops[1]["jump_targets"] == [33]
    assert original_ops[27]["opcode_name"] == "ZEND_JMP"
    assert original_ops[27]["jump_targets"] == [2]

    new_ops = rewritten["op_arrays"][CLOSURE_FUNCTION_ID]["opcodes"]
    assert "ZEND_JMPZ" in [op["opcode_name"] for op in new_ops]
    assert new_ops[0]["opcode_name"] == "ZEND_RECV_INIT"
    assert new_ops[1]["opcode_name"] == "ZEND_INIT_FCALL_BY_NAME"

    php = emit_php(optimize(decompile_program(parse_dump(rewritten))))
    normalized = php.replace("\r\n", "\n")
    assert "goto " not in normalized
    assert "$downloadResponsePayload = customJsonDecode($response);" in normalized
    assert "if (!empty($downloadResponsePayload['url'])) {" in normalized
    assert "Logger::log('Download URL not found in payload'" in normalized


def test_backward_forward_stub_is_not_treated_as_loop_latch():
    rewritten, original_ops = _load_backward_stub_rewritten()

    assert original_ops[4]["opcode_name"] == "ZEND_JMP"
    assert original_ops[4]["jump_targets"] == [2]

    new_ops = rewritten["op_arrays"][BACKWARD_STUB_FUNCTION_ID]["opcodes"]
    assert "ZEND_JMP" not in [op["opcode_name"] for op in new_ops]
    assert [op["opcode_name"] for op in new_ops[:4]] == [
        "ZEND_RECV",
        "ZEND_JMPZ",
        "ZEND_RETURN",
        "ZEND_RETURN",
    ]

    php = emit_php(optimize(decompile_program(parse_dump(rewritten))))
    normalized = php.replace("\r\n", "\n")
    assert (
        "function backward_stub($flag) {\n"
        "    if ($flag) {\n"
        "        return 'yes';\n"
        "    }\n"
        "    return 'no';\n"
        "}"
    ) in normalized
    assert "goto " not in normalized


def test_while_break_continue_targets_are_preserved():
    rewritten, original_ops = _load_break_rewritten()

    expected_names = [
        "ZEND_RECV",
        "ZEND_RECV",
        "ZEND_RECV",
        "ZEND_JMPZ",
        "ZEND_JMPZ",
        "ZEND_JMPZ",
        "ZEND_ECHO",
        "ZEND_JMP",
        "ZEND_JMP",
        "ZEND_RETURN",
    ]
    assert [op["opcode_name"] for op in original_ops] == expected_names

    new_ops = rewritten["op_arrays"][BREAK_FUNCTION_ID]["opcodes"]
    assert [op["opcode_name"] for op in new_ops] == expected_names
    assert new_ops[3]["jump_targets"] == [9]
    assert new_ops[4]["jump_targets"] == [3]
    assert new_ops[5]["jump_targets"] == [3]
    assert new_ops[7]["jump_targets"] == [9]
    assert new_ops[8]["jump_targets"] == [3]


def test_while_break_continue_reconstructs_loop_exits():
    rewritten, _ = _load_break_rewritten()

    php = emit_php(optimize(decompile_program(parse_dump(rewritten))))
    normalized = php.replace("\r\n", "\n")

    expected = (
        "function loop_exits($a, $b, $again) {\n"
        "    while ($again) {\n"
        "        if (!$a) {\n"
        "            continue;\n"
        "        }\n"
        "        if (!$b) {\n"
        "            continue;\n"
        "        }\n"
        "        echo 'ab';\n"
        "        break;\n"
        "    }"
    )
    assert expected in normalized
    assert "while (true)" not in normalized
    assert "goto " not in normalized


def test_entry_init_block_is_scheduled_before_conditional_body():
    rewritten, original_ops = _load_entry_init_rewritten(ENTRY_DEAD_FUNCTION_ID)

    assert original_ops[1]["opcode_name"] == "ZEND_JMP"
    assert original_ops[1]["jump_targets"] == [7]
    assert original_ops[3]["opcode_name"] == "ZEND_RETURN"
    assert original_ops[4]["jump_targets"] == [9]
    assert original_ops[6]["jump_targets"] == [9]

    new_ops = rewritten["op_arrays"][ENTRY_DEAD_FUNCTION_ID]["opcodes"]
    assert [op["opcode_name"] for op in new_ops] == [
        "ZEND_RECV",
        "ZEND_ASSIGN",
        "ZEND_JMPZ",
        "ZEND_RETURN",
        "ZEND_RETURN",
    ]
    assert "ZEND_JMP" not in [op["opcode_name"] for op in new_ops]
    assert new_ops[2]["jump_targets"] == [4]

    php = emit_php(optimize(decompile_program(parse_dump(rewritten))))
    normalized = php.replace("\r\n", "\n")
    assert (
        "function entry_dead($flag) {\n"
        "    $suffix = 'yes';\n"
        "    if ($flag) {\n"
        "        return $suffix;\n"
        "    }\n"
        "    return 'no';\n"
        "}"
    ) in normalized
    assert "goto " not in normalized
    assert "return null" not in normalized


def test_dead_blocks_after_return_are_not_emitted():
    rewritten, _ = _load_entry_init_rewritten(ENTRY_DEAD_FUNCTION_ID)
    new_ops = rewritten["op_arrays"][ENTRY_DEAD_FUNCTION_ID]["opcodes"]

    assert new_ops[-1]["opcode_name"] == "ZEND_RETURN"
    assert new_ops[-2]["opcode_name"] == "ZEND_RETURN"
    assert [op["opcode_name"] for op in new_ops].count("ZEND_RETURN") == 2
    assert new_ops[-1].get("jump_targets") == []


def test_entry_init_prefers_linear_walk_when_return_block_is_shared():
    rewritten, original_ops = _load_entry_init_rewritten(ENTRY_COMMON_FUNCTION_ID)

    assert original_ops[1]["jump_targets"] == [8]
    assert original_ops[3]["jump_targets"] == [6]
    assert original_ops[7]["jump_targets"] == [4]

    new_ops = rewritten["op_arrays"][ENTRY_COMMON_FUNCTION_ID]["opcodes"]
    assert [op["opcode_name"] for op in new_ops] == [
        "ZEND_RECV",
        "ZEND_ASSIGN",
        "ZEND_ECHO",
        "ZEND_ASSIGN",
        "ZEND_RETURN",
    ]
    assert "ZEND_JMP" not in [op["opcode_name"] for op in new_ops]

    php = emit_php(optimize(decompile_program(parse_dump(rewritten))))
    normalized = php.replace("\r\n", "\n")
    assert (
        "function entry_common($flag) {\n"
        "    $suffix = 'init';\n"
        "    echo 'body';\n"
        "    $suffix = 'label';\n"
        "    return $suffix;\n"
        "}"
    ) in normalized
    assert "goto " not in normalized
