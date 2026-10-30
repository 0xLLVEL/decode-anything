"""Runtime opcode-dump bridge for ionCube PHP 7.x bodies."""

from __future__ import annotations

import pytest

from engines.ioncube.runtime_dump import find_runtime, to_icdump


def _safe(value):
    return {"type": "string", "value": value, "printable": True}


def _cv(name, index):
    return {"type": 16, "type_name": "IS_CV", "num": 32 + index * 16,
            "cv_name": name, "cv_index": index}


def _const(index):
    return {"type": 1, "type_name": "IS_CONST", "num": index, "constant": index}


def _unused(n=0):
    return {"type": 8, "type_name": "IS_UNUSED", "num": n}


def _op(index, name, op1=None, op2=None, result=None, jumps=(), extended=0):
    return {
        "index": index,
        "opcode_name": name,
        "opcode": 1,
        "line": None,
        "extended_value": extended,
        "jump_targets": list(jumps),
        "op1": op1 or _unused(),
        "op2": op2 or _unused(),
        "result": result or _unused(),
    }


SAMPLE_IR = {
    "format": "ic72dump-ir-v3",
    "op_arrays": {
        "main": {
            "id": "main",
            "kind": "main",
            "function_name": None,
            "fn_flags": 0,
            "line_start": 1,
            "line_end": 4,
            "last_var": 0,
            "T": 0,
            "vars": [],
            "arg_info": [],
            "literals": [],
            "opcodes": [_op(0, "ZEND_RETURN")],
        },
        "function:64656d6f": {
            "id": "function:64656d6f",
            "kind": "function",
            "function_name": _safe("demo"),
            "fn_flags": 0x2000,
            "line_start": 5,
            "line_end": 9,
            "last_var": 2,
            "T": 1,
            "vars": [_safe("params"), _safe("out")],
            "arg_info": [
                {
                    "index": 0,
                    "name": "params",
                    "type_name": "string",
                    "class_name": None,
                    "type_code": 64,
                    "pass_by_reference": False,
                    "allow_null": True,
                    "is_variadic": False,
                    "has_default": False,
                }
            ],
            "return_type_info": {
                "type_name": "array",
                "class_name": None,
                "type_code": 128,
                "allow_null": False,
            },
            "doc_comment": _safe("demo doc"),
            "literals": [_safe("hello")],
            "opcodes": [
                _op(0, "ZEND_RECV", _unused(1), result=_cv("params", 0)),
                _op(1, "ZEND_ASSIGN", _cv("out", 1), _const(0)),
                _op(2, "ZEND_JMPZ", _cv("out", 1), _unused(4), _unused(), jumps=(4,)),
                _op(3, "ZEND_RETURN", _cv("out", 1)),
                _op(4, "ZEND_RETURN", _const(0)),
            ],
        },
    },
    "function_index": {"64656d6f": "function:64656d6f"},
    "class_index": {},
}


def test_operand_kinds_are_translated_to_ic_encoding():
    icdump = to_icdump(SAMPLE_IR, "demo.php")
    fn = icdump["op_arrays"]["function:64656d6f"]

    assign = fn["opcodes"][1]
    assert assign["op1"]["type_name"] == "IS_CV"
    assert assign["op1"]["cv_name"] == "out"
    assert assign["op1"]["cv_index"] == 1
    assert assign["op2"]["type_name"] == "IS_CONST"
    assert assign["op2"]["type"] == 1
    assert assign["op2"]["literal"]["value"] == "hello"

    recv = fn["opcodes"][0]
    assert recv["op1"]["type_name"] == "IS_UNUSED"
    assert recv["result"]["cv_name"] == "params"


def test_jump_operand_becomes_a_target():
    icdump = to_icdump(SAMPLE_IR, "demo.php")
    jmpz = icdump["op_arrays"]["function:64656d6f"]["opcodes"][2]

    assert jmpz["jump_targets"] == [4]
    assert jmpz["op2"]["type_name"] == "IS_UNUSED"
    assert jmpz["op2"]["num"] == 4


def test_signature_and_metadata_survive():
    icdump = to_icdump(SAMPLE_IR, "demo.php")
    fn = icdump["op_arrays"]["function:64656d6f"]

    assert fn["function_name"]["value"] == "demo"
    assert fn["arg_info"][0]["name"] == "params"
    assert fn["arg_info"][0]["type_name"] == "string"
    assert fn["arg_info"][0]["allow_null"] is True
    assert fn["return_type_info"]["type_name"] == "array"
    assert fn["scope"]["value"] is None
    assert fn["doc_comment"]["value"] == "demo doc"
    assert fn["meta"]["source"]["value"] == "runtime_opcode_dump"
    assert icdump["function_index"]["64656d6f"] == "function:64656d6f"


def test_strict_types_flag_from_main_fn_flags():
    ir = {"op_arrays": {"main": dict(SAMPLE_IR["op_arrays"]["main"], fn_flags=0x80000000)}}
    icdump = to_icdump(ir, "demo.php")
    assert icdump["op_arrays"]["main"]["strict_types"] is True


@pytest.mark.skipif(find_runtime(72) is None, reason="no PHP 7.2 opcode-dump runtime installed")
def test_runtime_roundtrip_keeps_cv_names(tmp_path):
    from engines.ioncube.runtime_dump import dump_opcodes

    # The runtime bundle ships encoded contacts.php; dump it and check a known CV.
    runtime = find_runtime(72)
    sample = runtime / "contacts.php"
    if not sample.is_file():
        pytest.skip("runtime bundle has no contacts.php sample")

    ir = dump_opcodes(sample, 72)
    icdump = to_icdump(ir, str(sample))
    names = [
        name.get("value") if isinstance(name, dict) else name
        for oa in icdump["op_arrays"].values()
        for name in (oa["vars"].get("value") or [])
    ]
    assert "data" in names
    assert any(oa["kind"] == "main" for oa in icdump["op_arrays"].values())
