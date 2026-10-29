"""Convert a static ionCube-loader method dump to icdump-ir-v1 JSON.

The static dumper keeps RE-oriented details such as encoded words, loader
offsets and opcode XOR metadata. This adapter emits a stable, consumer-neutral
IR shape; it does not infer source code and does not use candidate PHP text.
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
from pathlib import Path
from typing import Any


def safe_value(value: Any) -> dict[str, Any]:
    if value is None:
        return {"type": "null", "value": None}
    if isinstance(value, bool):
        return {"type": "bool", "value": value}
    if isinstance(value, int):
        return {"type": "int", "value": value}
    if isinstance(value, float):
        return {"type": "float", "value": value}
    if isinstance(value, str):
        return safe_string(value)
    if isinstance(value, list):
        return {"type": "array", "value": [safe_value(item) for item in value]}
    if isinstance(value, dict):
        return {
            "type": "array",
            "value": {str(key): safe_value(item) for key, item in value.items()},
        }
    return safe_string(str(value))


def safe_string(value: str) -> dict[str, Any]:
    data = value.encode("utf-8")
    printable = all(byte in (9, 10, 13) or 32 <= byte < 127 for byte in data)
    return {
        "type": "string",
        "length": len(data),
        "printable": printable,
        "value": value if printable else None,
        "preview": value[:160] if printable else None,
        "hex": data.hex(),
        "base64": base64.b64encode(data).decode("ascii"),
        "sha1": hashlib.sha1(data).hexdigest(),
    }


def build_op_array_entry(
    raw: dict[str, Any],
    source_file: str | None = None,
    kind: str = "function",
) -> tuple[str, dict[str, Any]]:
    """Build one icdump-ir-v1 op_array entry from a raw static-dump dict.

    Returns ``(op_array_id, op_array_dict)``.

    *kind* is ``"function"`` (default) or ``"main"``.
    For ``"main"``, ``op_array_id`` is always ``"main"`` and the
    ``"method"`` field in *raw* is ignored.  Opcodes and literals are still
    read from *raw* so the main script body is populated correctly.
    """
    method_raw: str = raw.get("method") or ""
    record: dict = raw.get("dynamic_method_record") if isinstance(raw.get("dynamic_method_record"), dict) else {}
    if not record:
        record = raw.get("method_record") if isinstance(raw.get("method_record"), dict) else {}
    metadata: dict = raw.get("metadata") if isinstance(raw.get("metadata"), dict) else {}

    if kind == "main":
        op_array_id = "main"
        table_name = ""
        table_hex = ""
        fn_name_val: dict = safe_value(None)
    else:
        if not method_raw:
            raise ValueError("raw['method'] must be a non-empty string for kind='function'")
        raw_table_name = raw.get("table_name")
        table_name = (
            raw_table_name
            if isinstance(raw_table_name, str) and raw_table_name
            else record.get("table_name")
            if isinstance(record.get("table_name"), str)
            else method_raw.lower()
        )
        table_hex = table_name.encode("utf-8").hex()
        op_array_id = f"function:{table_hex}"
        fn_name_val = safe_string(method_raw)

    variables = [str(n) for n in metadata.get("variables", []) if isinstance(n, str)]
    num_args = _opt_int(metadata.get("num_args"), 0) or 0
    required_num_args = _opt_int(metadata.get("required_num_args"), num_args) or 0

    # arg_type_info layout (ZEND_ACC_HAS_RETURN_TYPE = 0x2000): when a return
    # type is present it occupies arg_type_info[0] and parameters start at [1];
    # otherwise parameters start at [0].
    fn_flags_val   = _opt_int(metadata.get("fn_flags"), 0) or 0
    arg_type_info  = metadata.get("arg_type_info", [])
    has_return     = bool(fn_flags_val & 0x2000)
    arg_offset     = 1 if has_return else 0
    return_type_info = None
    if has_return and isinstance(arg_type_info, list) and arg_type_info:
        rt = arg_type_info[0] if isinstance(arg_type_info[0], dict) else {}
        rt_code = _opt_int(rt.get("type_code"), 0) or 0
        rt_name, rt_null = _zend_type_name(rt_code)
        rt_class = rt.get("class_name")
        if rt_class:
            rt_name = rt_class
        if rt_name:
            return_type_info = {
                "type_name": rt_name, "allow_null": rt_null, "type_code": rt_code,
            }

    literals_raw = raw.get("literals", [])
    opcodes = _convert_opcodes(raw.get("opcodes", []), literals_raw)
    live_range = _calc_live_ranges(opcodes)

    op_array: dict[str, Any] = {
        "id": op_array_id,
        "kind": kind,
        "meta": {
            "function_table_key": safe_string(table_name) if table_name else safe_value(None),
            "function_table_key_hex": table_hex,
            "source": safe_string("loader_static"),
            "static_dump_status": raw.get("status", {}),
            "ioncube_try_catch_raw": raw.get("try_catch_raw", []),
        },
        "function_name": fn_name_val,
        "filename": safe_value(source_file),
        "scope": safe_value(None),
        "line_start": _opt_int(metadata.get("line_start"), 0) or 0,
        "line_end": _opt_int(metadata.get("line_end"), 0) or 0,
        "fn_flags": _opt_int(metadata.get("fn_flags"), 0) or 0,
        "fn_flags_decoded": _fn_flags_decoded(_opt_int(metadata.get("fn_flags"), 0) or 0),
        "num_args": num_args,
        "required_num_args": required_num_args,
        "arg_info": _arg_info(
            variables,
            num_args,
            required_num_args,
            arg_type_info,
            type_offset=arg_offset,
        ),
        "return_type_info": return_type_info,
        "doc_comment": safe_value(None),
        "vars": safe_value(variables),
        "vars_raw": safe_value(variables) if variables else safe_value(None),
        "last_var": _opt_int(metadata.get("last_var"), len(variables)) or len(variables),
        "T": _opt_int(raw.get("temp_variable_count"), _infer_temp_count(raw.get("opcodes", []))) or 0,
        "static_variables": safe_value(None),
        "try_catch": [dict(tc) for tc in raw.get("try_catch_raw", []) if isinstance(tc, dict)],
        "live_range": live_range,
        "literals": _convert_literals(literals_raw),
        "opcodes": opcodes,
        "cfg": {"blocks": [], "edges": []},
        "analysis": {
            "opcode_stats": [],
            "literal_xrefs": [],
            "sites": {
                "calls": [],
                "include_eval": [],
                "lambda_declarations": [],
                "assignments": [],
                "returns": [],
            },
        },
        "closure_report": {
            "declared_lambdas": 0,
            "dumped_closure_op_arrays": 0,
            "missing": 0,
            "num_dynamic_func_defs": 0,
            "materialized_closures": 0,
        },
    }
    return op_array_id, op_array


def build_icdump(raw: dict[str, Any], source_file: str | None = None) -> dict[str, Any]:
    """Build a complete icdump-ir-v1 document for a single function."""
    method = _require_str(raw.get("method"), "method")
    fn_id, fn_op_array = build_op_array_entry(raw, source_file, kind="function")
    table_hex = fn_op_array["meta"]["function_table_key_hex"]
    return {
        "format": "icdump-ir-v1",
        "source_file": source_file or f"loader-static:{method}",
        "summary": {
            "op_array_count": 2,
            "function_count": 1,
            "closure_count": 0,
            "class_count": 0,
        },
        "entry": "main",
        "op_arrays": {
            "main": _empty_main_op_array(source_file),
            fn_id: fn_op_array,
        },
        "function_index": {table_hex: fn_id},
        "closure_index": {},
        "class_index": {},
        "ioncube_api_calls": safe_value([]),
    }


def _empty_main_op_array(source_file: str | None) -> dict[str, Any]:
    return {
        "id": "main",
        "kind": "main",
        "meta": [],
        "function_name": safe_value(None),
        "filename": safe_value(source_file),
        "scope": safe_value(None),
        "line_start": 0,
        "line_end": 0,
        "fn_flags": 0,
        "fn_flags_decoded": _fn_flags_decoded(0),
        "num_args": 0,
        "required_num_args": 0,
        "arg_info": [],
        "return_type_info": None,
        "doc_comment": safe_value(None),
        "vars": safe_value([]),
        "vars_raw": safe_value(None),
        "last_var": 0,
        "T": 0,
        "static_variables": safe_value(None),
        "try_catch": [],
        "live_range": [],
        "literals": [],
        "opcodes": [],
        "cfg": {"blocks": [], "edges": []},
        "analysis": {
            "opcode_stats": [],
            "literal_xrefs": [],
            "sites": {
                "calls": [],
                "include_eval": [],
                "lambda_declarations": [],
                "assignments": [],
                "returns": [],
            },
        },
        "closure_report": {
            "declared_lambdas": 0,
            "dumped_closure_op_arrays": 0,
            "missing": 0,
            "num_dynamic_func_defs": 0,
            "materialized_closures": 0,
        },
    }


def _fn_flags_decoded(flags: int) -> dict[str, Any]:
    visibility = "none"
    if flags & 0x01:
        visibility = "public"
    elif flags & 0x02:
        visibility = "protected"
    elif flags & 0x04:
        visibility = "private"
    return {
        "visibility": visibility,
        "is_static": bool(flags & 0x10),
        "is_abstract": bool(flags & 0x40),
        "is_final": bool(flags & 0x20),
        "is_ctor": bool(flags & 0x2000),
        "is_dtor": bool(flags & 0x4000),
        "is_deprecated": bool(flags & 0x40000),
        "is_closure": bool(flags & 0x100000),
        "is_generator": bool(flags & 0x800000),
        "is_variadic": bool(flags & 0x1000000),
        "returns_reference": bool(flags & 0x4000000),
        "has_return_type": bool(flags & 0x40000000),
    }


# Zend type masks: MAY_BE_<T> = 1 << IS_<T>. Decode the builtin-type bits of a
# serialized zend_type into a PHP type name. MAY_BE_NULL becomes a separate
# nullable flag (the emitter renders it as a leading "?").
_ZEND_TYPE_BITS = [
    (1 << 4,  "int"),
    (1 << 5,  "float"),
    (1 << 6,  "string"),
    (1 << 7,  "array"),
    (1 << 8,  "object"),
    (1 << 9,  "resource"),
    (1 << 12, "callable"),
    (1 << 13, "iterable"),
    (1 << 14, "void"),
    (1 << 16, "mixed"),
    (1 << 17, "never"),
    (1 << 18, "static"),
]


def _zend_type_name(mask: int) -> "tuple[str | None, bool]":
    """Return ``(type_name, allow_null)`` for a serialized zend_type mask."""
    if not mask:
        return None, False
    allow_null = bool(mask & (1 << 1))                       # MAY_BE_NULL
    names: list[str] = []
    if mask & ((1 << 2) | (1 << 3)):                         # MAY_BE_FALSE/TRUE
        names.append("bool")
    for bit, name in _ZEND_TYPE_BITS:
        if mask & bit:
            names.append(name)
    if not names:                                            # class type (name not captured)
        return None, allow_null
    name_set = set(names)
    if "mixed" in name_set or name_set >= {"bool", "int", "float", "string", "array", "object"}:
        return "mixed", False
    if "void" in name_set:
        return "void", False
    if "never" in name_set:
        return "never", False
    return "|".join(names), allow_null


def _arg_info(
    variables: list[str],
    num_args: int,
    required_num_args: int,
    arg_type_info: Any,
    type_offset: int = 0,
) -> list[dict[str, Any]]:
    args = []
    for index in range(num_args):
        ti_index = type_offset + index
        type_info = arg_type_info[ti_index] if isinstance(arg_type_info, list) and ti_index < len(arg_type_info) else {}
        name = None
        if index < len(variables) and variables[index]:
            name = variables[index]
        elif isinstance(type_info, dict) and type_info.get("arg_name"):
            name = type_info["arg_name"]
        else:
            name = f"arg{index + 1}"
        type_code = _opt_int(type_info.get("type_code"), 0) if isinstance(type_info, dict) else 0
        class_name = type_info.get("class_name") if isinstance(type_info, dict) else None
        type_name, allow_null = _zend_type_name(type_code or 0)
        if class_name:                       # class type hint overrides the builtin mask
            type_name = class_name
        args.append(
            {
                "index": index,
                "name": name,
                "type_name": type_name,
                "class_name": class_name,
                "type_code": type_code or 0,
                "pass_by_reference": False,
                "allow_null": allow_null,
                "is_variadic": False,
                "has_default": index >= required_num_args,
            }
        )
    return args


def _convert_literals(raw_literals: Any) -> list[dict[str, Any]]:
    if not isinstance(raw_literals, list):
        return []
    converted = []
    for index, literal in enumerate(raw_literals):
        value = literal.get("value") if isinstance(literal, dict) else None
        out = {"index": index}
        out.update(safe_value(value))
        converted.append(out)
    return converted


def _convert_opcodes(raw_opcodes: Any, raw_literals: Any) -> list[dict[str, Any]]:
    if not isinstance(raw_opcodes, list):
        return []
    literal_values = _literal_values(raw_literals)
    converted = []
    for fallback_index, op in enumerate(raw_opcodes):
        if not isinstance(op, dict):
            continue
        op1 = _convert_operand(op.get("op1"), literal_values)
        op2 = _convert_operand(op.get("op2"), literal_values)
        result = _convert_operand(op.get("result"), literal_values)
        jump_targets = _jump_targets(op)
        opcode_name = op.get("opcode_name") if isinstance(op.get("opcode_name"), str) else None
        extended_value = _signed_u32(_opt_int(op.get("extended_value"), 0) or 0)
        out = {
            "index": _opt_int(op.get("index"), fallback_index) or fallback_index,
            "line": _opt_int(op.get("lineno"), 0) or 0,
            "lineno_raw": None,
            "opcode": _opt_int(op.get("opcode")),
            "opcode_name": opcode_name,
            "handler": _opt_int(op.get("handler_word")),
            "extended_value": extended_value,
            "extended_value_decoded": _decode_extended_value(opcode_name, extended_value),
            "op1": op1,
            "op2": op2,
            "result": result,
            "jump_targets": jump_targets,
            "is_call": opcode_name in {
                "ZEND_INIT_FCALL",
                "ZEND_INIT_FCALL_BY_NAME",
                "ZEND_DO_FCALL",
                "ZEND_DO_FCALL_BY_NAME",
            },
            "is_include_or_eval": opcode_name == "ZEND_INCLUDE_OR_EVAL",
            "is_lambda_declare": opcode_name == "ZEND_DECLARE_LAMBDA_FUNCTION",
            "opcode_raw": _opt_int(
                op.get("opcode_raw_byte"),
                _opt_int(op.get("encoded_word"), 0) & 0xFF,
            ),
            "opcode_xor_decoded": _opt_int(op.get("opcode")),
            "resolved_opcode_source": _resolved_opcode_source(op),
            "ic_meta_flags": 36039,
            "ic_operand_flags": 0,
        }
        if opcode_name in {"ZEND_FE_FETCH_R", "ZEND_FE_FETCH_RW"}:
            done_opline = _opt_int(op.get("extended_jump_target"))
            if done_opline is not None:
                out["fe_fetch_done_opline"] = done_opline
        converted.append(out)
    return converted


def _literal_values(raw_literals: Any) -> list[Any]:
    if not isinstance(raw_literals, list):
        return []
    values = []
    for literal in raw_literals:
        if isinstance(literal, dict):
            values.append(literal.get("value"))
        else:
            values.append(None)
    return values


def _convert_operand(raw_operand: Any, literal_values: list[Any]) -> dict[str, Any]:
    if not isinstance(raw_operand, dict):
        return _empty_operand()

    jump_target = _opt_int(raw_operand.get("jump_target"))
    serialized = _opt_int(raw_operand.get("serialized_value"), 0) or 0
    zend_value = _opt_int(raw_operand.get("zend_value"), serialized) or 0
    value = jump_target if jump_target is not None else zend_value
    operand_type = _opt_int(raw_operand.get("type"), 0) or 0
    out: dict[str, Any] = {
        "type": operand_type,
        "type_name": (
            raw_operand.get("type_name")
            if operand_type in {0, 1, 2, 4, 8}
            and isinstance(raw_operand.get("type_name"), str)
            else None
        ),
        "constant": value,
        "var": value,
        "num": value,
        "opline_num": value,
        "cv_name": None,
    }
    literal_index = _opt_int(raw_operand.get("literal_index"))
    variable_index = _opt_int(raw_operand.get("variable_index"))

    base_type = operand_type & 0x0F
    if base_type == 1 and literal_index is not None:
        out["constant"] = literal_index
        if 0 <= literal_index < len(literal_values):
            out["literal"] = safe_value(literal_values[literal_index])
    elif base_type == 8:
        if variable_index is not None:
            out["cv_index"] = variable_index
        variable_name = raw_operand.get("variable_name")
        if isinstance(variable_name, str):
            out["cv_name"] = variable_name

    return out


def _empty_operand() -> dict[str, Any]:
    return {
        "type": 0,
        "type_name": "IS_UNUSED",
        "constant": 0,
        "var": 0,
        "num": 0,
        "opline_num": 0,
        "cv_name": None,
    }


def _jump_targets(op: dict[str, Any]) -> list[int]:
    targets = []
    for key in ("op1", "op2", "result"):
        operand = op.get(key)
        if not isinstance(operand, dict):
            continue
        target = _opt_int(operand.get("jump_target"))
        if target is not None and target not in targets:
            targets.append(target)
    target = _opt_int(op.get("extended_jump_target"))
    if target is not None and target not in targets:
        targets.append(target)
    return targets


def _resolved_opcode_source(op: dict[str, Any]) -> str:
    if op.get("opcode_name") == "ZEND_OP_DATA":
        return "zend_op_data_pseudo"
    source = op.get("opcode_source")
    if source in {"handler_lane", "opcode_raw", "opcode_raw_direct_handler"}:
        return "zend_vm_handler"
    return "ioncube_loader_handler"


def _call_name(opcode_name: Any, op2: dict[str, Any]) -> str | None:
    if opcode_name not in {"ZEND_INIT_FCALL", "ZEND_INIT_FCALL_BY_NAME", "ZEND_INIT_NS_FCALL_BY_NAME"}:
        return None
    literal = op2.get("literal")
    if isinstance(literal, dict) and literal.get("type") == "string" and isinstance(literal.get("value"), str):
        return literal["value"]
    return None


def _decode_extended_value(opcode_name: Any, value: int) -> Any:
    if opcode_name == "ZEND_INCLUDE_OR_EVAL":
        return {
            1: "eval",
            2: "include",
            4: "include_once",
            8: "require",
            16: "require_once",
        }.get(value, f"unknown({value})")
    if opcode_name == "ZEND_CAST":
        return {
            1: "null",
            2: "false",
            3: "bool",
            4: "int",
            5: "float",
            6: "string",
            7: "array",
            8: "object",
            13: "bool",
        }.get(value, f"unknown({value})")
    if opcode_name == "ZEND_CATCH":
        return {"is_last_catch": bool(value)}
    if opcode_name in {
        "ZEND_FETCH_R",
        "ZEND_FETCH_W",
        "ZEND_FETCH_RW",
        "ZEND_FETCH_FUNC_ARG",
        "ZEND_FETCH_UNSET",
        "ZEND_FETCH_IS",
    }:
        unsigned = value & 0xFFFFFFFF
        fetch_type = unsigned & 0x70000000
        type_name = {
            0: "global",
            0x10000000: "local",
            0x40000000: "global_lock",
        }.get(fetch_type, f"unknown(0x{fetch_type:x})")
        return {"fetch_type": type_name, "arg": unsigned & 0x000FFFFF}
    return None


def resolve_function_calls(op_arrays: dict[str, dict[str, Any]]) -> None:
    """Attach the function-table spelling used by the runtime IR."""

    function_names: dict[str, str] = {}
    for op_array in op_arrays.values():
        if op_array.get("kind") != "function":
            continue
        table_key = op_array.get("meta", {}).get("function_table_key", {}).get("value")
        function_name = op_array.get("function_name", {}).get("value")
        if isinstance(table_key, str) and isinstance(function_name, str):
            function_names[table_key.lower()] = function_name

    init_opcodes = {
        "ZEND_INIT_FCALL",
        "ZEND_INIT_FCALL_BY_NAME",
        "ZEND_INIT_NS_FCALL_BY_NAME",
    }
    for op_array in op_arrays.values():
        for op in op_array.get("opcodes", []):
            if op.get("opcode_name") not in init_opcodes:
                continue
            op2 = op.get("op2")
            literal = op2.get("literal") if isinstance(op2, dict) else None
            value = literal.get("value") if isinstance(literal, dict) else None
            if not isinstance(value, str):
                continue
            lowered = value.lower()
            if lowered.startswith(("curl_", "mysqli_", "openssl_")):
                continue
            is_user_function = lowered in function_names
            resolved = function_names.get(lowered, value)
            op2["resolved_literal"] = safe_string(resolved)
            op2["resolved_literal_source"] = "function_table"
            op["resolved_function_name"] = resolved
            op["resolved_function_type"] = 2 if is_user_function else 1
            op["resolved_function_name_source"] = "function_table"
            op["call_name"] = resolved


def _normalize_temp_keys(opcodes: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Repair obvious ionCube temp-key drift for downstream IR consumers.

    Static ionCube operands can carry a rewritten temp slot while the opcode
    stream still has a single live producer.  In that narrow case, normalize
    the consumer key to the live producer key.  The raw static JSON remains
    untouched; this only affects the icdump adapter layer.
    """

    live: dict[int, int] = {}
    rewrites: list[dict[str, Any]] = []
    for op in opcodes:
        for operand_name in ("op1", "op2"):
            operand = op.get(operand_name)
            if not isinstance(operand, dict):
                continue
            key = _temp_key(operand)
            if key is None:
                continue
            if key in live:
                live.pop(key)
                continue
            if len(live) != 1:
                continue
            replacement, producer_index = next(reversed(live.items()))
            operand["var"] = replacement
            live.pop(replacement)
            rewrites.append(
                {
                    "opcode_index": op.get("index"),
                    "operand": operand_name,
                    "from": key,
                    "to": replacement,
                    "producer_index": producer_index,
                    "reason": "single_live_temp",
                }
            )

        result = op.get("result")
        if isinstance(result, dict):
            key = _temp_key(result)
            if key is not None:
                live[key] = _opt_int(op.get("index"), 0) or 0
    return rewrites


def _temp_key(operand: dict[str, Any]) -> int | None:
    if (_opt_int(operand.get("type"), 0) or 0) & 0x0F not in {2, 4}:
        return None
    return _opt_int(operand.get("var"))


def _calc_live_ranges(opcodes: list[dict[str, Any]]) -> list[dict[str, int]]:
    last_use: dict[int, int] = {}
    ranges: list[dict[str, int]] = []
    for opnum in range(len(opcodes) - 1, -1, -1):
        op = opcodes[opnum]
        opcode_name = op.get("opcode_name")
        result = op.get("result")
        if (
            isinstance(result, dict)
            and _is_temp_operand(result)
            and not _is_fake_def(opcode_name)
        ):
            var = _opt_int(result.get("var"))
            if var is not None and var in last_use:
                use = last_use[var]
                if opnum + 1 != use:
                    entry = _emit_live_range(opcodes, opnum, use, var)
                    if entry is not None:
                        ranges.append(entry)
                last_use.pop(var, None)

        op1 = op.get("op1")
        if isinstance(op1, dict) and _is_temp_operand(op1):
            var = _opt_int(op1.get("var"))
            if var is not None:
                if opcode_name in {"ZEND_FE_RESET_R", "ZEND_FE_RESET_RW"}:
                    last_use[var] = opnum
                elif var not in last_use and not _keeps_op1_alive(opcode_name):
                    last_use[var] = opnum - 1 if opcode_name == "ZEND_OP_DATA" else opnum

        op2 = op.get("op2")
        if isinstance(op2, dict) and _is_temp_operand(op2):
            var = _opt_int(op2.get("var"))
            if var is None:
                continue
            if opcode_name in {"ZEND_FE_FETCH_R", "ZEND_FE_FETCH_RW"}:
                if var in last_use:
                    use = last_use[var]
                    if opnum + 1 != use:
                        entry = _emit_live_range(opcodes, opnum, use, var)
                        if entry is not None:
                            ranges.append(entry)
                    last_use.pop(var, None)
            elif var not in last_use:
                last_use[var] = opnum - 1 if opcode_name == "ZEND_OP_DATA" else opnum

    ranges.reverse()
    if any(ranges[i]["start"] > ranges[i + 1]["start"] for i in range(len(ranges) - 1)):
        ranges.sort(key=lambda item: item["start"])
    return ranges


def _emit_live_range(
    opcodes: list[dict[str, Any]],
    start: int,
    end: int,
    var: int,
) -> dict[str, int] | None:
    opcode_name = opcodes[start].get("opcode_name")
    if opcode_name in {
        "ZEND_JMPZ_EX",
        "ZEND_JMPNZ_EX",
        "ZEND_BOOL",
        "ZEND_BOOL_NOT",
        "ZEND_FETCH_CLASS",
        "ZEND_DECLARE_ANON_CLASS",
        "ZEND_FAST_CALL",
    }:
        return None

    kind = 0
    if opcode_name == "ZEND_BEGIN_SILENCE":
        kind = 2
        start += 1
    elif opcode_name == "ZEND_ROPE_INIT":
        kind = 3
    elif opcode_name in {"ZEND_FE_RESET_R", "ZEND_FE_RESET_RW"}:
        kind = 1
        start += 1
    elif opcode_name == "ZEND_NEW":
        kind = 4
        start += 1
    else:
        start += 1

    if start >= end:
        return None
    return {"var": var | kind, "start": start, "end": end}


def _is_fake_def(opcode_name: Any) -> bool:
    return opcode_name in {
        "ZEND_ROPE_ADD",
        "ZEND_ADD_ARRAY_ELEMENT",
        "ZEND_ADD_ARRAY_UNPACK",
    }


def _keeps_op1_alive(opcode_name: Any) -> bool:
    return opcode_name in {
        "ZEND_CASE",
        "ZEND_CASE_STRICT",
        "ZEND_SWITCH_LONG",
        "ZEND_SWITCH_STRING",
        "ZEND_MATCH",
        "ZEND_FETCH_LIST_R",
        "ZEND_COPY_TMP",
    }


def _is_temp_operand(operand: dict[str, Any]) -> bool:
    return ((_opt_int(operand.get("type"), 0) or 0) & 0x0F) in {2, 4}


def _infer_temp_count(raw_opcodes: Any) -> int:
    if not isinstance(raw_opcodes, list):
        return 0
    max_temp = -1
    for op in raw_opcodes:
        if not isinstance(op, dict):
            continue
        for key in ("op1", "op2", "result"):
            operand = op.get(key)
            if not isinstance(operand, dict):
                continue
            if operand.get("type_name") in {"IS_TMP_VAR", "IS_VAR"}:
                index = _opt_int(operand.get("variable_index"))
                if index is not None:
                    max_temp = max(max_temp, index)
    return max_temp + 4 if max_temp >= 0 else 0


def _require_str(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value:
        raise ValueError(f"missing string field: {field}")
    return value


def _opt_int(value: Any, default: int | None = None) -> int | None:
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    if isinstance(value, str):
        try:
            return int(value, 0)
        except ValueError:
            return default
    return default


def _signed_u32(value: int) -> int:
    value &= 0xFFFFFFFF
    return value - 0x100000000 if value & 0x80000000 else value


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path, help="static loader JSON, e.g. addToCart_loader_static.json")
    parser.add_argument("-o", "--output", type=Path, help="output icdump-ir-v1 JSON")
    parser.add_argument("--source-file", help="source filename to embed in the normalized dump")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    raw = json.loads(args.input.read_text(encoding="utf-8"))
    output = args.output or args.input.with_suffix(".icdump.json")
    normalized = build_icdump(raw, args.source_file)
    output.write_text(json.dumps(normalized, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"wrote {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
