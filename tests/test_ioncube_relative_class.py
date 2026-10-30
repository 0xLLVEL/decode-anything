"""Regression tests for self/parent/static resolution in ionCube 8.4 opcodes.

The loader reads the relative class from ``op1.num`` (zend_fetch_class_type).
``extended_value`` carries unrelated call flags and must not override it.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1] / "ioncube-php8-decompiler" / "src"))

from php_reconstructor.decompiler.optimize import optimize
from php_reconstructor.decompiler.program import decompile_program
from php_reconstructor.emitter.php_emitter import emit_php
from php_reconstructor.loader import parse_dump

SELF = 0x201
PARENT = 0x202
STATIC = 0x203


def _const(index, value):
    return {
        "type": 1,
        "type_name": "IS_CONST",
        "constant": index,
        "var": index,
        "num": index,
        "opline_num": index,
        "literal": value,
    }


def _unused(value):
    return {
        "type": 0,
        "type_name": "IS_UNUSED",
        "constant": value,
        "var": value,
        "num": value,
        "opline_num": value,
    }


def _tmp(key):
    return {
        "type": 2,
        "type_name": "IS_TMP_VAR",
        "constant": key,
        "var": key,
        "num": key,
        "opline_num": key,
    }


def _emit_static_call(op1_value, extended_value, method="foo"):
    dump = {
        "format": "icdump-ir-v1",
        "source_file": "relative.php",
        "entry": "main",
        "op_arrays": {
            "main": {
                "kind": "main",
                "literals": [
                    {
                        "index": 0,
                        "type": "string",
                        "length": len(method),
                        "printable": True,
                        "value": method,
                    }
                ],
                "opcodes": [
                    {
                        "index": 0,
                        "line": 1,
                        "opcode_name": "ZEND_INIT_STATIC_METHOD_CALL",
                        "extended_value": extended_value,
                        "op1": _unused(op1_value),
                        "op2": _const(
                            0,
                            {
                                "type": "string",
                                "length": len(method),
                                "printable": True,
                                "value": method,
                            },
                        ),
                        "result": _unused(0),
                    },
                    {
                        "index": 1,
                        "line": 1,
                        "opcode_name": "ZEND_DO_FCALL",
                        "op1": _tmp(16),
                        "result": _tmp(24),
                    },
                    {
                        "index": 2,
                        "line": 1,
                        "opcode_name": "ZEND_RETURN",
                        "op1": _tmp(24),
                    },
                ],
            }
        },
    }
    return emit_php(optimize(decompile_program(parse_dump(dump))))


def test_unused_self_operand_wins_over_extended_value():
    code = _emit_static_call(SELF, extended_value=2)

    assert "return self::foo();" in code
    assert "parent::foo()" not in code


def test_unused_parent_operand_resolves_to_parent():
    code = _emit_static_call(PARENT, extended_value=2)

    assert "return parent::foo();" in code


def test_unused_static_operand_resolves_to_static():
    code = _emit_static_call(STATIC, extended_value=2)

    assert "return static::foo();" in code


def test_extended_value_is_the_fallback_when_operand_is_missing():
    code = _emit_static_call(0, extended_value=1)

    assert "return self::foo();" in code
