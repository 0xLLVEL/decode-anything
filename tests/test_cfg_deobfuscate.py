"""Regression tests for CFG deobfuscation."""

from dump_plain_file_static import (
    _drop_self_target_conditionals,
    deobfuscate_cfg,
)


def _op(index, name, jump_targets=()):
    return {
        "index": index,
        "opcode_name": name,
        "jump_targets": list(jump_targets),
    }


def test_linear_cfg_is_not_reordered():
    ops = [
        _op(0, "ZEND_RECV"),
        _op(1, "ZEND_JMPZ", [4]),
        _op(2, "ZEND_QM_ASSIGN"),
        _op(3, "ZEND_RETURN"),
        _op(4, "ZEND_QM_ASSIGN"),
        _op(5, "ZEND_RETURN"),
    ]
    entry = {"opcodes": ops}

    assert deobfuscate_cfg(entry) is entry
    assert [op["index"] for op in entry["opcodes"]] == list(range(len(ops)))


def test_conditional_break_and_continue_jumps_are_preserved():
    for jump_target, label in ((5, "forward break"), (0, "backward continue")):
        ops = [
            _op(0, "ZEND_JMPZ", [5]),
            _op(1, "ZEND_JMPZ", [3]),
            _op(2, "ZEND_JMP", [jump_target]),
            _op(3, "ZEND_NOP"),
            _op(4, "ZEND_JMP", [0]),
            _op(5, "ZEND_RETURN"),
        ]
        entry = {"opcodes": ops}

        result = deobfuscate_cfg(entry)

        assert result is entry, label
        assert [op["opcode_name"] for op in result["opcodes"]] == [
            "ZEND_JMPZ",
            "ZEND_JMPZ",
            "ZEND_JMP",
            "ZEND_NOP",
            "ZEND_JMP",
            "ZEND_RETURN",
        ], label
        assert result["opcodes"][2]["jump_targets"] == [jump_target], label


def test_conditional_with_converging_jump_chains_is_left_intact():
    ops = [
        _op(0, "ZEND_JMPZ", [3]),
        _op(1, "ZEND_JMP", [5]),
        _op(2, "ZEND_NOP"),
        _op(3, "ZEND_JMP", [5]),
        _op(4, "ZEND_NOP"),
        _op(5, "ZEND_RETURN"),
    ]
    entry = {"opcodes": ops}

    result = deobfuscate_cfg(entry)

    assert result is entry
    assert [op["opcode_name"] for op in result["opcodes"]] == [
        "ZEND_JMPZ",
        "ZEND_JMP",
        "ZEND_NOP",
        "ZEND_JMP",
        "ZEND_NOP",
        "ZEND_RETURN",
    ]


def test_match_op_array_is_never_reordered():
    ops = [
        _op(0, "ZEND_RECV"),
        _op(1, "ZEND_MATCH"),
        _op(2, "ZEND_MUL"),
        _op(3, "ZEND_QM_ASSIGN"),
        _op(4, "ZEND_JMP", [7]),
        _op(5, "ZEND_MUL"),
        _op(6, "ZEND_QM_ASSIGN"),
        _op(7, "ZEND_RETURN"),
    ]
    entry = {"opcodes": ops}

    assert deobfuscate_cfg(entry) is entry
    assert [op["opcode_name"] for op in entry["opcodes"]] == [
        "ZEND_RECV",
        "ZEND_MATCH",
        "ZEND_MUL",
        "ZEND_QM_ASSIGN",
        "ZEND_JMP",
        "ZEND_MUL",
        "ZEND_QM_ASSIGN",
        "ZEND_RETURN",
    ]


def test_unconditional_cfg_is_emitted_in_execution_order():
    ops = [
        _op(0, "ZEND_JMP", [3]),
        _op(1, "ZEND_NOP"),
        _op(2, "ZEND_RETURN"),
        _op(3, "ZEND_NOP"),
        _op(4, "ZEND_RETURN"),
    ]

    result = deobfuscate_cfg({"opcodes": ops})

    assert [op["opcode_name"] for op in result["opcodes"]] == [
        "ZEND_NOP",
        "ZEND_RETURN",
    ]
    assert [op["index"] for op in result["opcodes"]] == [0, 1]


def test_self_target_conditional_is_dropped_but_loop_guard_is_kept():
    plain = [
        _op(0, "ZEND_RECV"),
        _op(1, "ZEND_JMPZ", [2]),
        _op(2, "ZEND_RETURN"),
    ]
    assert [op["opcode_name"] for op in _drop_self_target_conditionals(plain)] == [
        "ZEND_RECV",
        "ZEND_RETURN",
    ]

    loop = [
        _op(0, "ZEND_JMPZ", [1]),
        _op(1, "ZEND_JMP", [0]),
    ]
    assert [op["opcode_name"] for op in _drop_self_target_conditionals(loop)] == [
        "ZEND_JMPZ",
        "ZEND_JMP",
    ]
