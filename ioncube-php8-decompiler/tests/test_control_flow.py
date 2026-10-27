"""Milestone 3: control-flow reconstruction."""

from conftest import const, cv, dump, op, op_array, reconstruct, tmp, unused


def fn(opcodes, **kwargs):
    return reconstruct(dump(main_ops=[], functions={"f": op_array(opcodes, **kwargs)}))


def test_simple_if():
    out = fn([
        op("ZEND_JMPZ", op1=cv(0, "c"), jump=[2]),
        op("ZEND_ECHO", op1=const("yes")),
        op("ZEND_RETURN", op1=const(None)),
    ], cvs=["c"])
    assert "if ($c) {" in out
    assert "echo 'yes';" in out


def test_if_else():
    out = fn([
        op("ZEND_JMPZ", op1=cv(0, "c"), jump=[3]),
        op("ZEND_ECHO", op1=const("yes")),
        op("ZEND_JMP", jump=[4]),
        op("ZEND_ECHO", op1=const("no")),
        op("ZEND_RETURN", op1=const(None)),
    ], cvs=["c"])
    assert "if ($c) {" in out
    assert "} else {" in out
    assert "echo 'no';" in out


def test_if_with_comparison_condition():
    out = fn([
        op("ZEND_IS_SMALLER", op1=cv(0, "n"), op2=const(10), result=tmp(96)),
        op("ZEND_JMPZ", op1=tmp(96), jump=[3]),
        op("ZEND_ECHO", op1=const("small")),
        op("ZEND_RETURN", op1=const(None)),
    ], cvs=["n"])
    assert "if ($n < 10) {" in out


def test_jmpnz_negates_condition():
    out = fn([
        op("ZEND_JMPNZ", op1=cv(0, "c"), jump=[2]),
        op("ZEND_ECHO", op1=const("falsy")),
        op("ZEND_RETURN", op1=const(None)),
    ], cvs=["c"])
    assert "if (!$c) {" in out


def test_while_top_tested():
    # 0: cond ; 1: JMPZ -> 4 ; 2: body ; 3: JMP -> 0 ; 4: return
    out = fn([
        op("ZEND_IS_SMALLER", op1=cv(0, "i"), op2=const(10), result=tmp(96)),
        op("ZEND_JMPZ", op1=tmp(96), jump=[4]),
        op("ZEND_PRE_INC", op1=cv(0, "i")),
        op("ZEND_JMP", jump=[0]),
        op("ZEND_RETURN", op1=const(None)),
    ], cvs=["i"])
    assert "while ($i < 10) {" in out
    assert "++$i;" in out


def test_while_bottom_tested():
    # 0: JMP -> 2 ; 1: body ; 2: cond ; 3: JMPNZ -> 1 ; 4: return
    out = fn([
        op("ZEND_JMP", jump=[2]),
        op("ZEND_PRE_INC", op1=cv(0, "i")),
        op("ZEND_IS_SMALLER", op1=cv(0, "i"), op2=const(10), result=tmp(96)),
        op("ZEND_JMPNZ", op1=tmp(96), jump=[1]),
        op("ZEND_RETURN", op1=const(None)),
    ], cvs=["i"])
    assert "while ($i < 10) {" in out
    assert "++$i;" in out
    assert "[opcode" not in out


def test_bottom_tested_while_with_side_effect_condition():
    # while ($row = next_row()) { use($row); }
    out = fn([
        op("ZEND_JMP", jump=[4]),
        op("ZEND_INIT_FCALL", op2=const("use_row")),
        op("ZEND_SEND_VAR", op1=cv(0, "row")),
        op("ZEND_DO_FCALL"),
        op("ZEND_INIT_FCALL", op2=const("next_row")),
        op("ZEND_DO_FCALL", result=tmp(96)),
        op("ZEND_ASSIGN", op1=cv(0, "row"), op2=tmp(96), result=tmp(112)),
        op("ZEND_JMPNZ", op1=tmp(112), jump=[1]),
        op("ZEND_RETURN", op1=const(None)),
    ], cvs=["row"])
    # Priming read before the loop, re-read at the end of the body.
    assert out.count("$row = next_row();") == 2
    assert "while ($row) {" in out
    assert "use_row($row);" in out


def test_foreach_value_only():
    out = fn([
        op("ZEND_FE_RESET_R", op1=cv(0, "items"), result=tmp(96), jump=[4]),
        op("ZEND_FE_FETCH_R", op1=tmp(96), op2=cv(1, "item"), jump=[4]),
        op("ZEND_ECHO", op1=cv(1, "item")),
        op("ZEND_JMP", jump=[1]),
        op("ZEND_FE_FREE", op1=tmp(96)),
        op("ZEND_RETURN", op1=const(None)),
    ], cvs=["items", "item"])
    assert "foreach ($items as $item) {" in out
    assert "echo $item;" in out


def test_foreach_with_key_in_cv():
    out = fn([
        op("ZEND_FE_RESET_R", op1=cv(0, "map"), result=tmp(96), jump=[4]),
        op("ZEND_FE_FETCH_R", op1=tmp(96), op2=cv(2, "v"), result=cv(1, "k"), jump=[4]),
        op("ZEND_ECHO", op1=cv(1, "k")),
        op("ZEND_JMP", jump=[1]),
        op("ZEND_FE_FREE", op1=tmp(96)),
        op("ZEND_RETURN", op1=const(None)),
    ], cvs=["map", "k", "v"])
    assert "foreach ($map as $k => $v) {" in out


def test_foreach_with_key_in_temp_plus_assign():
    # Older encoder shape: key delivered in a temp, first body op assigns it.
    out = fn([
        op("ZEND_FE_RESET_R", op1=cv(0, "map"), result=tmp(96), jump=[5]),
        op("ZEND_FE_FETCH_R", op1=tmp(96), op2=cv(2, "v"), result=tmp(112), jump=[5]),
        op("ZEND_ASSIGN", op1=cv(1, "k"), op2=tmp(112)),
        op("ZEND_ECHO", op1=cv(1, "k")),
        op("ZEND_JMP", jump=[1]),
        op("ZEND_FE_FREE", op1=tmp(96)),
        op("ZEND_RETURN", op1=const(None)),
    ], cvs=["map", "k", "v"])
    assert "foreach ($map as $k => $v) {" in out
    assert "tmp" not in out


def test_ternary():
    out = fn([
        op("ZEND_JMPZ", op1=cv(0, "c"), jump=[3]),
        op("ZEND_QM_ASSIGN", op1=const("yes"), result=tmp(96)),
        op("ZEND_JMP", jump=[4]),
        op("ZEND_QM_ASSIGN", op1=const("no"), result=tmp(96)),
        op("ZEND_ASSIGN", op1=cv(1, "x"), op2=tmp(96)),
        op("ZEND_RETURN", op1=const(None)),
    ], cvs=["c", "x"])
    assert "$x = $c ? 'yes' : 'no';" in out


def test_short_circuit_and():
    out = fn([
        op("ZEND_JMPZ_EX", op1=cv(0, "a"), result=tmp(96), jump=[2]),
        op("ZEND_BOOL", op1=cv(1, "b"), result=tmp(96)),
        op("ZEND_JMPZ", op1=tmp(96), jump=[4]),
        op("ZEND_ECHO", op1=const("both")),
        op("ZEND_RETURN", op1=const(None)),
    ], cvs=["a", "b"])
    assert "if ($a && $b) {" in out


def test_short_circuit_or():
    out = fn([
        op("ZEND_JMPNZ_EX", op1=cv(0, "a"), result=tmp(96), jump=[2]),
        op("ZEND_BOOL", op1=cv(1, "b"), result=tmp(96)),
        op("ZEND_JMPZ", op1=tmp(96), jump=[4]),
        op("ZEND_ECHO", op1=const("either")),
        op("ZEND_RETURN", op1=const(None)),
    ], cvs=["a", "b"])
    assert "if ($a || $b) {" in out


def test_break_inside_while():
    # while ($i < 10) { if ($stop) break; ++$i; }
    out = fn([
        op("ZEND_IS_SMALLER", op1=cv(0, "i"), op2=const(10), result=tmp(96)),
        op("ZEND_JMPZ", op1=tmp(96), jump=[6]),
        op("ZEND_JMPZ", op1=cv(1, "stop"), jump=[4]),
        op("ZEND_JMP", jump=[6]),
        op("ZEND_PRE_INC", op1=cv(0, "i")),
        op("ZEND_JMP", jump=[0]),
        op("ZEND_RETURN", op1=const(None)),
    ], cvs=["i", "stop"])
    assert "while ($i < 10) {" in out
    assert "break;" in out


def test_try_catch():
    out = reconstruct(dump(main_ops=[], functions={"f": op_array(
        [
            op("ZEND_INIT_FCALL", op2=const("risky")),
            op("ZEND_DO_FCALL"),
            op("ZEND_JMP", jump=[5]),
            op("ZEND_CATCH", op1=const("Exception"), result=cv(0, "e"), ext=1),
            op("ZEND_ECHO", op1=const("caught")),
            op("ZEND_RETURN", op1=const(None)),
        ],
        cvs=["e"],
        try_catch=[{"try_op": 0, "catch_op": 3, "finally_op": None, "finally_end": None}],
    )}))
    assert "try {" in out
    assert "risky();" in out
    assert "} catch (Exception $e) {" in out
    assert "echo 'caught';" in out


def test_switch_string_fallthrough():
    # switch (strtoupper($x)) { case 'P': $n *= 2; case 'K': $n *= 2; }
    out = fn([
        op("ZEND_INIT_FCALL_BY_NAME", op2=const("strtoupper")),
        op("ZEND_SEND_VAR_EX", op1=cv(0, "x")),
        op("ZEND_DO_FCALL_BY_NAME", result=tmp(80)),
        op("ZEND_SWITCH_STRING", op1=tmp(80), op2=const({"P": 99, "K": 99}), jump=[]),
        op("ZEND_CASE", op1=tmp(80), op2=const("P"), result=tmp(96)),
        op("ZEND_JMPNZ", op1=tmp(96), jump=[8]),
        op("ZEND_CASE", op1=tmp(80), op2=const("K"), result=tmp(96)),
        op("ZEND_JMPNZ", op1=tmp(96), jump=[9]),
        op("ZEND_ASSIGN_OP", op1=cv(1, "n"), op2=const(2), ext=3),  # 8: case 'P'
        op("ZEND_ASSIGN_OP", op1=cv(1, "n"), op2=const(2), ext=3),  # 9: case 'K'
        op("ZEND_FREE", op1=tmp(80), ext=2),                        # 10: switch end
        op("ZEND_RETURN", op1=cv(1, "n")),
    ], cvs=["x", "n"])
    assert "switch (strtoupper($x)) {" in out
    assert "case 'P':" in out
    assert "case 'K':" in out
    assert "$n *= 2;" in out
    assert "[opcode" not in out


def test_switch_string_uses_byte_offset_table_to_repair_shifted_targets():
    # The loader left each CASE branch one opcode late, but the switch table
    # still maps to body offsets using a consistent, inferable opcode stride.
    out = fn([
        op("ZEND_INIT_FCALL_BY_NAME", op2=const("strtoupper")),
        op("ZEND_SEND_VAR_EX", op1=cv(0, "x")),
        op("ZEND_DO_FCALL_BY_NAME", result=tmp(80)),
        op(
            "ZEND_SWITCH_STRING",
            op1=tmp(80),
            op2=const({"P": 140, "K": 168}),
            jump=[],
        ),
        op("ZEND_CASE", op1=tmp(80), op2=const("P"), result=tmp(96)),
        op("ZEND_JMPNZ", op1=tmp(96), jump=[9]),
        op("ZEND_CASE", op1=tmp(80), op2=const("K"), result=tmp(96)),
        op("ZEND_JMPNZ", op1=tmp(96), jump=[10]),
        op("ZEND_ASSIGN_OP", op1=cv(1, "n"), op2=const(2), ext=3),
        op("ZEND_ASSIGN_OP", op1=cv(1, "n"), op2=const(2), ext=3),
        op("ZEND_FREE", op1=tmp(80), ext=2),
        op("ZEND_RETURN", op1=cv(1, "n")),
    ], cvs=["x", "n"])
    assert "case 'P':\n            $n *= 2;" in out
    assert "case 'K':\n            $n *= 2;" in out
    assert out.count("$n *= 2;") == 2


def test_switch_with_break_and_default():
    # switch ($x) { case 1: $r = 'a'; break; default: $r = 'z'; }
    # Subject loaded into a temp (as PHP does for switch(expr)), freed at end.
    out = fn([
        op("ZEND_QM_ASSIGN", op1=cv(0, "x"), result=tmp(80)),        # 0
        op("ZEND_SWITCH_LONG", op1=tmp(80), op2=const({"1": 99})),   # 1
        op("ZEND_CASE", op1=tmp(80), op2=const(1), result=tmp(96)),  # 2
        op("ZEND_JMPNZ", op1=tmp(96), jump=[5]),                     # 3
        op("ZEND_JMP", jump=[7]),                                    # 4: default
        op("ZEND_ASSIGN", op1=cv(1, "r"), op2=const("a")),           # 5: case 1
        op("ZEND_JMP", jump=[8]),                                    # 6: break
        op("ZEND_ASSIGN", op1=cv(1, "r"), op2=const("z")),           # 7: default
        op("ZEND_FREE", op1=tmp(80), ext=2),                         # 8: switch end
        op("ZEND_RETURN", op1=cv(1, "r")),                           # 9
    ], cvs=["x", "r"])
    assert "switch ($x) {" in out
    assert "case 1:" in out
    assert "break;" in out
    assert "default:" in out
    assert "$r = 'z';" in out


def test_unknown_opcode_becomes_comment():
    out = fn([
        op("ZEND_TOTALLY_UNKNOWN", op1=cv(0, "x")),
        op("ZEND_RETURN", op1=const(None)),
    ], cvs=["x"])
    assert "/* [opcode 0] ZEND_TOTALLY_UNKNOWN" in out
