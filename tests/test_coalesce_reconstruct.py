"""Regression: `??` must keep its left operand when the fallback is a call.

PHP emits `COALESCE <left>, ->L` with the fallback copy (`QM_ASSIGN <call
result>, <coalesce temp>`) *at* `L` itself when the coalesce sits inside a
ternary or a call argument.  Skipping `L` left the coalesce temp unresolved,
so the next `QM_ASSIGN` overwrote the `??` and the decoded source lost the
`$params[...]` operand entirely.
"""

from __future__ import annotations

import sys
from pathlib import Path

SRC = Path(__file__).resolve().parents[1] / "ioncube-php8-decompiler" / "src"
sys.path.insert(0, str(SRC))

from php_reconstructor.decompiler import decompile_program, optimize  # noqa: E402
from php_reconstructor.emitter import emit_php  # noqa: E402
from php_reconstructor.loader import parse_dump  # noqa: E402


def _cv(var: int, name: str, index: int) -> dict:
    return {"type": 8, "type_name": "IS_CV", "var": var, "cv_name": name, "cv_index": index}


def _tmp(var: int) -> dict:
    return {"type": 2, "type_name": "IS_TMP_VAR", "var": var}


def _var(var: int) -> dict:
    return {"type": 4, "type_name": "IS_VAR", "var": var}


def _unused() -> dict:
    return {"type": 0, "type_name": "IS_UNUSED"}


def _string(value: str) -> dict:
    return {
        "type": 1,
        "type_name": "IS_CONST",
        "literal": {"type": "string", "length": len(value), "printable": True, "value": value},
    }


PARAMS = _cv(48, "params", 0)
X = _cv(64, "x", 1)

OPCODES = [
    {
        "index": 0,
        "opcode_name": "ZEND_RECV",
        "op1": _unused(),
        "op2": _unused(),
        "result": PARAMS,
        "jump_targets": [],
    },
    {
        "index": 1,
        "opcode_name": "ZEND_FETCH_DIM_IS",
        "op1": PARAMS,
        "op2": _string("db_connection"),
        "result": _tmp(256),
        "jump_targets": [],
    },
    {
        "index": 2,
        "opcode_name": "ZEND_COALESCE",
        "op1": _tmp(256),
        "op2": _unused(),
        "result": _tmp(272),
        "jump_targets": [4],
    },
    {
        "index": 3,
        "opcode_name": "ZEND_CONCAT",
        "op1": _string("mysql"),
        "op2": _string("_fallback"),
        "result": _var(288),
        "jump_targets": [],
    },
    {
        "index": 4,
        "opcode_name": "ZEND_QM_ASSIGN",
        "op1": _var(288),
        "op2": _unused(),
        "result": _tmp(272),
        "jump_targets": [],
    },
    {
        "index": 5,
        "opcode_name": "ZEND_ASSIGN",
        "op1": X,
        "op2": _tmp(272),
        "result": _unused(),
        "jump_targets": [],
    },
    {
        "index": 6,
        "opcode_name": "ZEND_RETURN",
        "op1": _unused(),
        "op2": _unused(),
        "result": _unused(),
        "jump_targets": [],
    },
]

DUMP = {
    "format": "icdump-ir-v1",
    "source_file": "coalesce_fallback.json",
    "entry": "main",
    "op_arrays": {
        "function:70726f6265": {
            "kind": "function",
            "meta": {},
            "function_name": {
                "type": "string",
                "length": 5,
                "printable": True,
                "value": "probe",
            },
            "vars": {"type": "array", "value": {"0": "params", "1": "x"}},
            "arg_info": [
                {
                    "index": 0,
                    "name": "params",
                    "type_name": None,
                    "pass_by_reference": False,
                    "allow_null": False,
                    "is_variadic": False,
                    "has_default": False,
                }
            ],
            "num_args": 1,
            "required_num_args": 1,
            "fn_flags_decoded": {},
            "literals": [],
            "try_catch": [],
            "opcodes": OPCODES,
        },
        "main": {
            "kind": "main",
            "meta": {},
            "function_name": {"type": "null", "value": None},
            "vars": {"type": "array", "value": {}},
            "arg_info": [],
            "num_args": 0,
            "required_num_args": 0,
            "fn_flags_decoded": {},
            "literals": [],
            "try_catch": [],
            "opcodes": [
                {
                    "index": 0,
                    "opcode_name": "ZEND_RETURN",
                    "op1": {
                        "type": 1,
                        "type_name": "IS_CONST",
                        "literal": {"type": "integer", "value": 1},
                    },
                    "op2": _unused(),
                    "result": _unused(),
                    "jump_targets": [],
                }
            ],
        },
    },
    "function_index": {},
    "closure_index": {},
    "class_index": {},
}


def _emit() -> str:
    return emit_php(optimize(decompile_program(parse_dump(DUMP)))).replace("\r\n", "\n")


def test_fallback_copy_at_jump_target_keeps_left_operand():
    php = _emit()

    assert "$params['db_connection'] ?? 'mysql' . '_fallback'" in php


def test_fallback_copy_is_not_emitted_as_a_separate_statement():
    php = _emit()

    assert "$x = 'mysql' . '_fallback';" not in php
    assert "$tmp" not in php
