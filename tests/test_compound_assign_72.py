"""PHP 7.0-7.3 give each compound assignment its own opcode.

`ZEND_ASSIGN_CONCAT`, `ZEND_ASSIGN_BW_OR`, ... were unhandled, so the decoder
emitted an opcode comment (stripped later) and the statement vanished.  Inside
an if/else that turned both branches into empty bodies.
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


def _const(value) -> dict:
    if isinstance(value, str):
        literal = {"type": "string", "length": len(value), "printable": True, "value": value}
    else:
        literal = {"type": "integer", "value": value}
    return {"type": 1, "type_name": "IS_CONST", "literal": literal}


def _unused() -> dict:
    return {"type": 0, "type_name": "IS_UNUSED"}


SQL = _cv(48, "sql", 0)
FLAGS = _cv(64, "flags", 1)

OPCODES = [
    {
        "index": 0,
        "opcode_name": "ZEND_ASSIGN_CONCAT",
        "op1": SQL,
        "op2": _const(" ORDER BY name"),
        "result": _unused(),
        "jump_targets": [],
    },
    {
        "index": 1,
        "opcode_name": "ZEND_ASSIGN_BW_OR",
        "op1": FLAGS,
        "op2": _const(4),
        "result": _unused(),
        "jump_targets": [],
    },
    {
        "index": 2,
        "opcode_name": "ZEND_RETURN",
        "op1": _unused(),
        "op2": _unused(),
        "result": _unused(),
        "jump_targets": [],
    },
]

DUMP = {
    "format": "icdump-ir-v1",
    "source_file": "compound_assign.json",
    "entry": "main",
    "op_arrays": {
        "main": {
            "kind": "main",
            "meta": {},
            "function_name": {"type": "null", "value": None},
            "vars": {"type": "array", "value": {"0": "sql", "1": "flags"}},
            "arg_info": [],
            "num_args": 0,
            "required_num_args": 0,
            "fn_flags_decoded": {},
            "literals": [],
            "try_catch": [],
            "opcodes": OPCODES,
        },
    },
    "function_index": {},
    "closure_index": {},
    "class_index": {},
}


def test_compound_assignment_keeps_its_operator():
    code = emit_php(optimize(decompile_program(parse_dump(DUMP))))

    assert "$sql .= ' ORDER BY name';" in code
    assert "$flags |= 4;" in code
