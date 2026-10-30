"""Regression tests for the ionCube ``__DIR__`` magic-constant recovery.

ionCube stores ``__DIR__`` as interned-string ref ``-2``.  The loader's pointer
table has a null entry for that slot because the loader substitutes the value
at runtime, so a static decode must not treat it as a null literal.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1] / "ioncube-php8-decompiler" / "src"))

from engines.ioncube.adapter import _convert_literals, _convert_operand
from engines.ioncube.body import SerializedLiteral, resolve_interned_literal_strings
from php_reconstructor.decompiler.optimize import optimize
from php_reconstructor.decompiler.program import decompile_program
from php_reconstructor.emitter.php_emitter import emit_php
from php_reconstructor.loader import parse_dump


class _Resolver:
    def __init__(self):
        self.calls = []

    def decode_ref(self, signed_offset, expected_length=None):
        self.calls.append(signed_offset)
        return "_GET" if signed_offset == -8 else None


def _literal(offset, length=15):
    return SerializedLiteral(
        index=0,
        type=6,
        type_name="IS_STRING",
        raw_type_info=262,
        raw_fields=(0, 0, 0),
        string_offset_raw=offset & 0xFFFFFFFF,
        string_length=length,
    )


def test_dir_ref_is_a_magic_constant_not_a_loader_string():
    literal = _literal(-2)
    resolver = _Resolver()

    resolve_interned_literal_strings([literal], resolver)

    assert literal.magic_constant == "__DIR__"
    assert literal.value is None
    assert literal.unresolved is None
    assert resolver.calls == []


def test_regular_interned_refs_still_use_the_loader_table():
    literal = _literal(-8, length=4)
    resolver = _Resolver()

    resolve_interned_literal_strings([literal], resolver)

    assert literal.magic_constant is None
    assert literal.value == "_GET"
    assert resolver.calls == [-8]


def test_adapter_keeps_the_magic_marker_on_the_literal_and_operand():
    converted = _convert_literals(
        [
            {"index": 0, "type": "string", "value": None, "magic_constant": "__DIR__"},
            {"index": 1, "type": "string", "value": "/../config/app.php"},
        ]
    )

    assert converted[0] == {"index": 0, "type": "magic", "value": "__DIR__"}
    assert converted[1]["value"] == "/../config/app.php"

    operand = _convert_operand(
        {
            "type": 1,
            "type_name": "IS_CONST",
            "constant": 0,
            "literal_index": 0,
            "literal": {"type": "null", "value": None},
        },
        [None, "/../config/app.php"],
        {0: "__DIR__"},
    )

    assert operand["magic_constant"] == "__DIR__"


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


def _tmp(key):
    return {
        "type": 2,
        "type_name": "IS_TMP_VAR",
        "constant": key,
        "var": key,
        "num": key,
        "opline_num": key,
    }


def test_dir_constant_reaches_the_emitted_source():
    dump = {
        "format": "icdump-ir-v1",
        "source_file": "dir.php",
        "entry": "main",
        "op_arrays": {
            "main": {
                "kind": "main",
                "literals": [
                    {"index": 0, "type": "magic", "value": "__DIR__"},
                    {
                        "index": 1,
                        "type": "string",
                        "length": 18,
                        "printable": True,
                        "value": "/../config/app.php",
                    },
                ],
                "opcodes": [
                    {
                        "index": 0,
                        "line": 1,
                        "opcode_name": "ZEND_FAST_CONCAT",
                        "op1": {**_const(0, {"type": "null", "value": None}), "magic_constant": "__DIR__"},
                        "op2": _const(
                            1,
                            {
                                "type": "string",
                                "length": 18,
                                "printable": True,
                                "value": "/../config/app.php",
                            },
                        ),
                        "result": _tmp(16),
                    },
                    {
                        "index": 1,
                        "line": 1,
                        "opcode_name": "ZEND_RETURN",
                        "op1": _tmp(16),
                    },
                ],
            }
        },
    }

    code = emit_php(optimize(decompile_program(parse_dump(dump))))

    assert "return __DIR__ . '/../config/app.php';" in code
    assert "null . " not in code
