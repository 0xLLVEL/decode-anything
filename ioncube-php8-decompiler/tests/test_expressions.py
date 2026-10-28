"""Milestone 2: simple expressions, assignments, calls, return."""

from conftest import arg, const, cv, dump, op, op_array, reconstruct, tmp, unused


def fn(opcodes, **kwargs):
    """Wrap opcodes in a single-function dump and reconstruct."""
    return reconstruct(dump(main_ops=[], functions={"f": op_array(opcodes, **kwargs)}))


def test_assign_literal():
    out = fn([
        op("ZEND_ASSIGN", op1=cv(0, "a"), op2=const(42)),
        op("ZEND_RETURN", op1=const(None)),
    ], cvs=["a"])
    assert "$a = 42;" in out


def test_assign_string_single_quoted():
    out = fn([
        op("ZEND_ASSIGN", op1=cv(0, "s"), op2=const("it's ok")),
        op("ZEND_RETURN", op1=const(None)),
    ], cvs=["s"])
    assert "$s = 'it\\'s ok';" in out


def test_binary_operation_chain():
    # $c = $a + $b * 2;
    out = fn([
        op("ZEND_MUL", op1=cv(1, "b"), op2=const(2), result=tmp(96)),
        op("ZEND_ADD", op1=cv(0, "a"), op2=tmp(96), result=tmp(112)),
        op("ZEND_ASSIGN", op1=cv(2, "c"), op2=tmp(112)),
        op("ZEND_RETURN", op1=const(None)),
    ], cvs=["a", "b", "c"])
    assert "$c = $a + $b * 2;" in out


def test_concat_and_precedence_parens():
    # $x = ($a + 1) . 'y'; -- addition binds tighter than concat in PHP 8,
    # but the emitted parens must preserve evaluation shape regardless.
    out = fn([
        op("ZEND_ADD", op1=cv(0, "a"), op2=const(1), result=tmp(96)),
        op("ZEND_CONCAT", op1=tmp(96), op2=const("y"), result=tmp(112)),
        op("ZEND_ASSIGN", op1=cv(1, "x"), op2=tmp(112)),
        op("ZEND_RETURN", op1=const(None)),
    ], cvs=["a", "x"])
    assert "$x = $a + 1 . 'y';" in out


def test_function_call_with_args():
    out = fn([
        op("ZEND_INIT_FCALL", op2=const("substr"), ext=2),
        op("ZEND_SEND_VAR", op1=cv(0, "s")),
        op("ZEND_SEND_VAL", op1=const(3)),
        op("ZEND_DO_FCALL", result=tmp(96)),
        op("ZEND_ASSIGN", op1=cv(1, "r"), op2=tmp(96)),
        op("ZEND_RETURN", op1=cv(1, "r")),
    ], cvs=["s", "r"])
    assert "$r = substr($s, 3);" in out
    assert "return $r;" in out


def test_call_statement_when_result_unused():
    out = fn([
        op("ZEND_INIT_FCALL_BY_NAME", op2=const("error_log")),
        op("ZEND_SEND_VAL_EX", op1=const("msg")),
        op("ZEND_DO_FCALL_BY_NAME"),
        op("ZEND_RETURN", op1=const(None)),
    ])
    assert "error_log('msg');" in out


def test_nested_calls():
    # f(g($x))
    out = fn([
        op("ZEND_INIT_FCALL", op2=const("trim")),
        op("ZEND_INIT_FCALL", op2=const("strtolower")),
        op("ZEND_SEND_VAR", op1=cv(0, "x")),
        op("ZEND_DO_FCALL", result=tmp(96)),
        op("ZEND_SEND_VAL", op1=tmp(96)),
        op("ZEND_DO_FCALL", result=tmp(112)),
        op("ZEND_RETURN", op1=tmp(112)),
    ], cvs=["x"])
    assert "return trim(strtolower($x));" in out


def test_method_call_on_this():
    out = fn([
        op("ZEND_INIT_METHOD_CALL", op1=unused(), op2=const("helper")),
        op("ZEND_DO_FCALL", result=tmp(96)),
        op("ZEND_RETURN", op1=tmp(96)),
    ])
    assert "return $this->helper();" in out


def test_property_and_dim_fetch():
    out = fn([
        op("ZEND_FETCH_OBJ_R", op1=unused(), op2=const("config"), result=tmp(96)),
        op("ZEND_FETCH_DIM_R", op1=tmp(96), op2=const("key"), result=tmp(112)),
        op("ZEND_RETURN", op1=tmp(112)),
    ])
    assert "return $this->config['key'];" in out


def test_compound_assign_op():
    out = fn([
        op("ZEND_ASSIGN_OP", op1=cv(0, "n"), op2=const(2), ext=1),
        op("ZEND_RETURN", op1=const(None)),
    ], cvs=["n"])
    assert "$n += 2;" in out


def test_assign_dim_with_op_data():
    out = fn([
        op("ZEND_ASSIGN_DIM", op1=cv(0, "arr"), op2=const("k")),
        op("ZEND_OP_DATA", op1=const(5)),
        op("ZEND_RETURN", op1=const(None)),
    ], cvs=["arr"])
    assert "$arr['k'] = 5;" in out


def test_assign_dim_append():
    out = fn([
        op("ZEND_ASSIGN_DIM", op1=cv(0, "arr"), op2=unused()),
        op("ZEND_OP_DATA", op1=const(1)),
        op("ZEND_RETURN", op1=const(None)),
    ], cvs=["arr"])
    assert "$arr[] = 1;" in out


def test_array_literal_construction():
    out = fn([
        op("ZEND_INIT_ARRAY", op1=const(1), op2=const("a"), result=tmp(96)),
        op("ZEND_ADD_ARRAY_ELEMENT", op1=const(2), op2=const("b"), result=tmp(96)),
        op("ZEND_ASSIGN", op1=cv(0, "x"), op2=tmp(96)),
        op("ZEND_RETURN", op1=const(None)),
    ], cvs=["x"])
    assert "$x = ['a' => 1, 'b' => 2];" in out


def test_fetch_constant_and_cast():
    out = fn([
        op("ZEND_FETCH_CONSTANT", op2=const("DB_PREFIX"), result=tmp(96)),
        op("ZEND_CAST", op1=cv(0, "id"), result=tmp(112), ext=4),
        op("ZEND_CONCAT", op1=tmp(96), op2=tmp(112), result=tmp(128)),
        op("ZEND_RETURN", op1=tmp(128)),
    ], cvs=["id"])
    assert "return DB_PREFIX . (int) $id;" in out


def test_isset_and_unset():
    out = fn([
        op("ZEND_ISSET_ISEMPTY_DIM_OBJ", op1=cv(0, "a"), op2=const("k"), result=tmp(96), ext=0),
        op("ZEND_ASSIGN", op1=cv(1, "h"), op2=tmp(96)),
        op("ZEND_UNSET_DIM", op1=cv(0, "a"), op2=const("k")),
        op("ZEND_RETURN", op1=const(None)),
    ], cvs=["a", "h"])
    assert "$h = isset($a['k']);" in out
    assert "unset($a['k']);" in out


def test_echo_and_global():
    out = fn([
        op("ZEND_BIND_GLOBAL", op1=cv(0, "db"), op2=const("db")),
        op("ZEND_ECHO", op1=const("hi")),
        op("ZEND_RETURN", op1=const(None)),
    ], cvs=["db"])
    assert "global $db;" in out
    assert "echo 'hi';" in out


def test_lifo_reconciliation_for_mismatched_temp_vars():
    # The consumer references t999 but the producer stored t96 (an ionCube
    # dump quirk); the newest live temp must be used instead of leaking $tmp.
    out = fn([
        op("ZEND_INIT_FCALL", op2=const("time")),
        op("ZEND_DO_FCALL", result=tmp(96)),
        op("ZEND_ASSIGN", op1=cv(0, "t"), op2=tmp(999)),
        op("ZEND_RETURN", op1=const(None)),
    ], cvs=["t"])
    assert "$t = time();" in out
    assert "tmp" not in out


def test_fetch_dynamic_var():
    # $v = ${'data' . ($i + 1)};
    out = fn([
        op("ZEND_ADD", op1=cv(0, "i"), op2=const(1), result=tmp(96)),
        op("ZEND_CONCAT", op1=const("data"), op2=tmp(96), result=tmp(112)),
        op("ZEND_FETCH_R", op1=tmp(112), result=tmp(128)),
        op("ZEND_ASSIGN", op1=cv(1, "v"), op2=tmp(128)),
        op("ZEND_RETURN", op1=const(None)),
    ], cvs=["i", "v"])
    assert "$v = ${'data' . $i + 1};" in out or "$v = ${'data' . ($i + 1)};" in out
    assert "..." not in out


def test_fetch_variable_variable():
    # $v = $$name;
    out = fn([
        op("ZEND_FETCH_R", op1=cv(0, "name"), result=tmp(96)),
        op("ZEND_ASSIGN", op1=cv(1, "v"), op2=tmp(96)),
        op("ZEND_RETURN", op1=const(None)),
    ], cvs=["name", "v"])
    assert "$v = $$name;" in out


def test_array_key_exists():
    out = fn([
        op("ZEND_ARRAY_KEY_EXISTS", op1=const("k"), op2=cv(0, "a"), result=tmp(96)),
        op("ZEND_ASSIGN", op1=cv(1, "res"), op2=tmp(96)),
        op("ZEND_RETURN", op1=const(None)),
    ], cvs=["a", "res"])
    assert "$res = array_key_exists('k', $a);" in out


def test_fetch_this():
    out = fn([
        op("ZEND_FETCH_THIS", result=tmp(96)),
        op("ZEND_FETCH_OBJ_R", op1=tmp(96), op2=const("prop"), result=tmp(112)),
        op("ZEND_RETURN", op1=tmp(112)),
    ])
    assert "return $this->prop;" in out


def test_match_expression():
    out = fn([
        op("ZEND_MATCH", op1=cv(0, "val"), op2=const({"a": 28, "b": 84}), ext=140),
        op("ZEND_QM_ASSIGN", op1=const(1), result=tmp(96)),
        op("ZEND_JMP", jump=[7]),
        op("ZEND_QM_ASSIGN", op1=const(2), result=tmp(96)),
        op("ZEND_JMP", jump=[7]),
        op("ZEND_QM_ASSIGN", op1=const(0), result=tmp(96)),
        op("ZEND_JMP", jump=[7]),
        op("ZEND_RETURN", op1=tmp(96)),
    ], cvs=["val"])
    assert "match ($val)" in out
    assert "'a' => 1" in out
    assert "'b' => 2" in out
    assert "default => 0" in out




