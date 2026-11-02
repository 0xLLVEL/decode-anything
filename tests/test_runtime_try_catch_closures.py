"""The 7.x runtime dump carries try/catch tables and lambdas; the bridge must keep them.

No 7.2 sample on this machine contains a `try` or a closure, so the dump below is
shaped exactly like `ic72dump-ir-v3` (the extension emits `try_catch` per op_array
and `closures` with the nested lambda op_array) and driven through the same
`to_icdump` → `parse_dump` → `decompile_program` → `emit_php` path the decoder uses.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "ioncube-php8-decompiler" / "src"))

from engines.ioncube.runtime_dump import to_icdump  # noqa: E402
from php_reconstructor.decompiler import decompile_program, optimize  # noqa: E402
from php_reconstructor.emitter import emit_php  # noqa: E402
from php_reconstructor.loader import parse_dump  # noqa: E402


def _cv(name: str, index: int) -> dict:
    return {"type": 16, "type_name": "IS_CV", "num": 32 + index * 16,
            "cv_name": name, "cv_index": index}


def _tmp(num: int) -> dict:
    return {"type": 2, "type_name": "IS_TMP_VAR", "num": num}


def _unused(num: int = 0) -> dict:
    return {"type": 8, "type_name": "IS_UNUSED", "num": num}


def _const(index: int) -> dict:
    return {"type": 1, "type_name": "IS_CONST", "num": index, "constant": index}


def _op(index: int, name: str, op1=None, op2=None, result=None, jumps=()) -> dict:
    return {
        "index": index, "line": 0, "opcode": 1, "opcode_name": name,
        "handler": 1, "extended_value": 0,
        "op1": op1 or _unused(), "op2": op2 or _unused(), "result": result or _unused(),
        "jump_targets": list(jumps),
    }


def _literal(index: int, value: str) -> dict:
    return {"index": index, "type": "string", "length": len(value), "printable": True,
            "value": value, "preview": value, "hex": value.encode().hex(),
            "base64": "", "sha1": ""}


def _op_array(opcodes, variables, literals, **extra) -> dict:
    entry = {
        "id": "x", "kind": "function", "meta": {},
        "function_name": {"type": "null", "value": None},
        "fn_flags": 0, "line_start": 1, "line_end": 1,
        "last_var": len(variables), "T": 8, "vars": variables,
        "arg_info": [], "literals": literals, "opcodes": opcodes,
        "try_catch": [], "closures": [], "closure_report": {},
    }
    entry.update(extra)
    return entry


LAMBDA = _op_array(
    [_op(0, "ZEND_RETURN", _const(0))],
    [],
    [_literal(0, "hi")],
)

MAIN = _op_array(
    [
        _op(0, "ZEND_DECLARE_LAMBDA_FUNCTION", _const(0), result=_tmp(256)),
        _op(1, "ZEND_ASSIGN", _cv("f", 0), _tmp(256)),
        _op(2, "ZEND_ASSIGN", _cv("x", 1), _const(1)),
        _op(3, "ZEND_JMP", _unused(6), jumps=(6,)),
        _op(4, "ZEND_CATCH", _const(2), result=_cv("e", 2)),
        _op(5, "ZEND_ASSIGN", _cv("y", 3), _const(3)),
        _op(6, "ZEND_RETURN", _cv("x", 1)),
    ],
    ["f", "x", "e", "y"],
    [_literal(0, "{closure}%00lambda"), _literal(1, "risky"),
     _literal(2, "Exception"), _literal(3, "caught")],
    id="main", kind="main", T=4,
    try_catch=[{"try_op": 2, "catch_op": 4, "finally_op": None, "finally_end": None}],
    closures=[{
        "opcode_index": 0, "opcode": 153,
        "literal_index": 0,
        "lambda_id": {"type": "string", "value": "{closure}%00lambda", "printable": True},
        "lambda_id_hex": "636c6f73757265",
        "op_array": LAMBDA,
    }],
)

DUMP = {
    "format": "ic72dump-ir-v3",
    "source_file": "try_catch.php",
    "entry": "main",
    "op_arrays": {"main": MAIN},
    "function_index": {},
    "closure_index": [],
    "class_index": {},
}


def _decode(dump: dict) -> tuple[str, dict]:
    icdump = to_icdump(dump, "try_catch.php")
    code = emit_php(optimize(decompile_program(parse_dump(icdump))))
    return code, icdump


def test_try_catch_table_reaches_the_ir():
    _, icdump = _decode(DUMP)

    assert icdump["op_arrays"]["main"]["try_catch"] == [
        {"try_op": 2, "catch_op": 4, "finally_op": None, "finally_end": None}
    ]


def test_try_catch_is_reconstructed_from_the_table():
    code, _ = _decode(DUMP)

    assert "try {" in code
    assert "} catch (Exception $e) {" in code
    assert "$x = 'risky';" in code
    assert "$y = 'caught';" in code


FINALLY_FUNCTION = _op_array(
    [
        _op(0, "ZEND_ASSIGN", _cv("x", 0), _const(0)),
        _op(1, "ZEND_FAST_CALL", _unused(3), result=_tmp(96), jumps=(3,)),
        _op(2, "ZEND_JMP", _unused(5), jumps=(5,)),
        _op(3, "ZEND_ASSIGN", _cv("y", 1), _const(1)),
        _op(4, "ZEND_FAST_RET", _tmp(96)),
        _op(5, "ZEND_RETURN", _cv("x", 0)),
    ],
    ["x", "y"],
    [_literal(0, "a"), _literal(1, "b")],
    try_catch=[{"try_op": 0, "catch_op": None, "finally_op": 3, "finally_end": 4}],
)

FINALLY_DUMP = {
    "format": "ic72dump-ir-v3",
    "source_file": "finally.php",
    "entry": "main",
    "op_arrays": {
        "main": _op_array([], [], [], id="main", kind="main"),
        "function:66696e616c6c79": FINALLY_FUNCTION,
    },
    "function_index": {"66696e616c6c79": "function:66696e616c6c79"},
    "closure_index": [],
    "class_index": {},
}


def test_finally_guard_becomes_a_finally_block():
    code, _ = _decode(FINALLY_DUMP)

    assert "} finally {" in code
    assert "$x = 'a';" in code
    assert "$y = 'b';" in code
    assert "FAST_CALL" not in code


def test_72_catch_variable_lives_in_op2():
    caught = _op_array(
        [
            _op(0, "ZEND_ASSIGN", _cv("x", 0), _const(0)),
            _op(1, "ZEND_JMP", _unused(5), jumps=(5,)),
            _op(2, "ZEND_CATCH", _const(1), _cv("e", 2)),
            _op(3, "ZEND_ASSIGN", _cv("y", 1), _const(2)),
            _op(4, "ZEND_RETURN", _cv("y", 1)),
            _op(5, "ZEND_RETURN", _cv("x", 0)),
        ],
        ["x", "y", "e"],
        [_literal(0, "a"), _literal(1, "Exception"), _literal(2, "b")],
        try_catch=[{"try_op": 0, "catch_op": 2, "finally_op": None, "finally_end": None}],
    )
    code, _ = _decode({
        "format": "ic72dump-ir-v3",
        "source_file": "catch.php",
        "entry": "main",
        "op_arrays": {
            "main": _op_array([], [], [], id="main", kind="main"),
            "function:6361746368": caught,
        },
        "function_index": {"6361746368": "function:6361746368"},
        "closure_index": [],
        "class_index": {},
    })

    assert "} catch (Exception $e) {" in code
    assert "$y = 'b';" in code


def test_flat_72_operands_keep_their_variables_and_literals():
    flat_closure = _op_array(
        [
            {
                "opcode": 1, "opcode_name": "ZEND_ADD", "lineno": 3,
                "extended_value": 0, "handler": 1,
                "op1_type": 16, "op1_type_name": "IS_CV", "op1.cv_name": "a",
                "op1.constant": 48, "op1.num": 48,
                "op2_type": 1, "op2_type_name": "IS_CONST", "op2.constant": 1,
                "op2.num": 1,
                "result_type": 2, "result_type_name": "IS_TMP_VAR",
                "result.num": 80, "result.constant": 80,
            },
            {
                "opcode": 62, "opcode_name": "ZEND_RETURN", "lineno": 3,
                "extended_value": 0, "handler": 1,
                "op1_type": 2, "op1_type_name": "IS_TMP_VAR", "op1.num": 80,
                "op2_type": 8, "op2_type_name": "IS_UNUSED", "op2.num": 0,
                "result_type": 8, "result_type_name": "IS_UNUSED", "result.num": 0,
            },
        ],
        ["a"],
        [{"value": "x"}, {"value": 1}],
    )
    dump = {
        "format": "ic72dump-ir-v3",
        "source_file": "flat.php",
        "entry": "main",
        "op_arrays": {
            "main": _op_array(
                [_op(0, "ZEND_DECLARE_LAMBDA_FUNCTION", _const(0), result=_tmp(256))],
                [],
                [_literal(0, "{closure}")],
                id="main", kind="main",
                closures=[{
                    "opcode_index": 0, "literal_index": 0,
                    "lambda_id_hex": "666c6174",
                    "op_array": flat_closure,
                }],
            ),
        },
        "function_index": {},
        "closure_index": [],
        "class_index": {},
    }

    code, icdump = _decode(dump)

    closure_id = icdump["closure_index"]["666c6174"]
    ops = icdump["op_arrays"][closure_id]["opcodes"]
    assert ops[0]["op1"]["type_name"] == "IS_CV"
    assert ops[0]["op1"]["cv_name"] == "a"
    assert ops[0]["op2"]["literal"]
    assert ops[1]["op1"]["type_name"] == "IS_TMP_VAR"


def test_lambda_op_array_is_linked_as_a_closure():
    code, icdump = _decode(DUMP)

    closure_id = icdump["closure_index"]["636c6f73757265"]
    assert icdump["op_arrays"][closure_id]["kind"] == "closure"
    assert icdump["op_arrays"][closure_id]["meta"]["parent"] == "main"
    assert icdump["op_arrays"][closure_id]["meta"]["opcode_index"] == 0
    assert icdump["summary"]["closure_count"] == 1
    assert "function ()" in code
    assert "return 'hi';" in code
