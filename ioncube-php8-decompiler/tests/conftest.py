"""Shared fixture builders: construct synthetic icdump-ir-v1 dumps tersely.

These mirror the real dump shape (safe_value wrappers, operand fields) so
tests exercise the same code paths as production dumps.
"""

from __future__ import annotations

from typing import Any

import pytest

from php_reconstructor.decompiler import decompile_program, optimize
from php_reconstructor.emitter import emit_php
from php_reconstructor.loader import parse_dump

# -- safe_value builders -------------------------------------------------------


def sv(value: Any) -> dict[str, Any]:
    """Wrap a Python value the way values.php safe_value() does."""
    if value is None:
        return {"type": "null", "value": None}
    if isinstance(value, bool):
        return {"type": "bool", "value": value}
    if isinstance(value, int):
        return {"type": "integer", "value": value}
    if isinstance(value, float):
        return {"type": "double", "value": value}
    if isinstance(value, str):
        return {"type": "string", "length": len(value), "printable": True, "value": value}
    if isinstance(value, dict):
        return {"type": "array", "value": {k: sv(v) for k, v in value.items()}}
    if isinstance(value, list):
        return {"type": "array", "value": {i: sv(v) for i, v in enumerate(value)}}
    raise TypeError(f"cannot wrap {type(value)}")


# -- operand builders ----------------------------------------------------------


def unused() -> dict[str, Any]:
    return {"type": 0, "type_name": "IS_UNUSED"}


def const(value: Any) -> dict[str, Any]:
    return {"type": 1, "type_name": "IS_CONST", "literal": sv(value)}


def cv(index: int, name: str) -> dict[str, Any]:
    return {
        "type": 8,
        "type_name": "IS_CV",
        "var": (3 + index) * 16,
        "cv_name": name,
        "cv_index": index,
    }


def tmp(var: int) -> dict[str, Any]:
    return {"type": 2, "type_name": "IS_TMP_VAR", "var": var}


# -- opcode / op_array / dump builders -----------------------------------------


def op(
    name: str,
    op1: dict[str, Any] | None = None,
    op2: dict[str, Any] | None = None,
    result: dict[str, Any] | None = None,
    ext: int | None = None,
    jump: list[int] | None = None,
    **extra: Any,
) -> dict[str, Any]:
    entry: dict[str, Any] = {
        "opcode_name": name,
        "op1": op1 or unused(),
        "op2": op2 or unused(),
        "result": result or unused(),
        "jump_targets": jump or [],
    }
    if ext is not None:
        entry["extended_value"] = ext
    entry.update(extra)
    return entry


def op_array(
    opcodes: list[dict[str, Any]],
    *,
    kind: str = "function",
    name: str | None = None,
    cvs: list[str] | None = None,
    arg_info: list[dict[str, Any]] | None = None,
    num_args: int = 0,
    required_num_args: int = 0,
    fn_flags_decoded: dict[str, Any] | None = None,
    meta: dict[str, Any] | None = None,
    try_catch: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    for index, entry in enumerate(opcodes):
        entry.setdefault("index", index)
    return {
        "kind": kind,
        "meta": meta or {},
        "function_name": sv(name),
        "vars": sv(cvs or []),
        "arg_info": arg_info or [],
        "num_args": num_args,
        "required_num_args": required_num_args,
        "fn_flags_decoded": fn_flags_decoded or {},
        "literals": [],
        "try_catch": try_catch or [],
        "opcodes": opcodes,
    }


def arg(index: int, name: str, *, type_name: str | None = None, by_ref: bool = False,
        has_default: bool = False, variadic: bool = False) -> dict[str, Any]:
    return {
        "index": index,
        "name": name,
        "type_name": type_name,
        "pass_by_reference": by_ref,
        "allow_null": False,
        "is_variadic": variadic,
        "has_default": has_default,
    }


def dump(
    main_ops: list[dict[str, Any]] | None = None,
    functions: dict[str, dict[str, Any]] | None = None,
    op_arrays: dict[str, dict[str, Any]] | None = None,
    class_index: dict[str, dict[str, Any]] | None = None,
) -> dict[str, Any]:
    arrays: dict[str, Any] = {}
    if main_ops is not None:
        arrays["main"] = op_array(main_ops, kind="main")
    if functions:
        for fn_name, fn_oa in functions.items():
            fn_oa["kind"] = "function"
            if fn_oa.get("function_name", {}).get("value") is None:
                fn_oa["function_name"] = sv(fn_name)
            arrays[f"function:{fn_name.encode().hex()}"] = fn_oa
    if op_arrays:
        arrays.update(op_arrays)
    return {
        "format": "icdump-ir-v1",
        "source_file": "test.php",
        "entry": "main",
        "op_arrays": arrays,
        "function_index": {},
        "closure_index": {},
        "class_index": class_index or {},
    }


def reconstruct(dump_dict: dict[str, Any]) -> str:
    """Full pipeline: raw dict -> Program -> AST -> optimized -> PHP text."""
    program = parse_dump(dump_dict)
    return emit_php(optimize(decompile_program(program)))


@pytest.fixture
def pipeline():
    return reconstruct
