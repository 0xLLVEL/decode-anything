"""Decode ionCube PHP 7.x bodies through the loader's in-memory op arrays.

A PHP 7.x ionCube body is not a serialized ``zend_op_array``: the loader builds
the op_array at load time and keeps the opcode stream XOR-encoded in memory
keyed by the request timestamp.  Re-implementing that from the blob alone means
reproducing the loader's in-memory encoding step for every build.

The loader itself already does the work.  ``php_opcodedump.dll`` calls the
loader's decode entry points, restores ``op_array->opcodes``/``last_var``, and
walks the result into the ``ic72dump-ir-v3`` JSON.  This module runs that
runtime on the target file and converts the dump into our ``icdump-ir-v1`` IR,
so the rest of the pipeline (structuring, emission, lint repair) is shared with
the 8.x static path.

Runtime bundles are not vendored: point ``IONCUBE_OPCODEDUMP_HOME`` at a
directory holding ``ic72dump-opcodes`` / ``ic74dump-opcodes`` style checkouts,
or keep them under ``loader/opcodedump`` or ``scratch/refs``.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any

from .adapter import build_op_array_entry, safe_value

# php_version → runtime bundle directory name
RUNTIME_BUNDLES = {
    71: "ic71dump-opcodes",
    72: "ic72dump-opcodes",
    73: "ic73dump-opcodes",
    74: "ic74dump-opcodes",
}

_PROJECT_ROOT = Path(__file__).resolve().parents[2]

_SEARCH_ROOTS = (
    _PROJECT_ROOT / "loader" / "opcodedump",
    _PROJECT_ROOT / "scratch" / "refs",
)


class RuntimeDumpError(RuntimeError):
    """Raised when the opcode-dump runtime is missing or produced no dump."""


def _candidate_roots(php_version: int) -> list[Path]:
    bundle = RUNTIME_BUNDLES.get(php_version)
    if bundle is None:
        return []
    roots: list[Path] = []
    env_home = os.environ.get("IONCUBE_OPCODEDUMP_HOME")
    if env_home:
        home = Path(env_home)
        roots.extend((home / bundle, home / str(php_version), home))
    roots.extend(root / bundle for root in _SEARCH_ROOTS)
    return roots


def find_runtime(php_version: int) -> Path | None:
    """Return the runtime bundle root for *php_version*, or None."""
    for root in _candidate_roots(php_version):
        if (
            (root / "runtime" / "php.exe").is_file()
            and (root / "runtime" / "php.ini").is_file()
            and (root / "opcodedump.php").is_file()
        ):
            return root
    return None


def available_versions() -> list[int]:
    return sorted(v for v in RUNTIME_BUNDLES if find_runtime(v) is not None)


def dump_opcodes(source: str | Path, php_version: int, *, timeout: int = 300) -> dict[str, Any]:
    """Run the bundled runtime on *source* and return the ``ic72dump-ir-v3`` dump."""
    root = find_runtime(php_version)
    if root is None:
        raise RuntimeDumpError(
            f"no opcode-dump runtime for PHP {php_version}; set IONCUBE_OPCODEDUMP_HOME"
        )

    source = Path(source).resolve()
    php = root / "runtime" / "php.exe"
    with tempfile.TemporaryDirectory(prefix="icdump-") as tmp:
        work = Path(tmp) / source.name
        shutil.copyfile(source, work)
        try:
            proc = subprocess.run(
                [str(php), "-c", str(root / "runtime" / "php.ini"),
                 str(root / "opcodedump.php"), str(work)],
                cwd=str(root / "runtime"),
                capture_output=True,
                text=True,
                errors="replace",
                timeout=timeout,
            )
        except subprocess.TimeoutExpired as exc:
            raise RuntimeDumpError(f"opcode dump timed out after {timeout}s") from exc

        dump_path = work.with_name(work.stem + ".opcodes.json")
        if not dump_path.is_file():
            tail = (proc.stderr or proc.stdout or "").strip().splitlines()[-5:]
            raise RuntimeDumpError(
                "opcode dump produced no JSON (exit %d): %s"
                % (proc.returncode, " | ".join(tail) or "no output")
            )
        return json.loads(dump_path.read_text(encoding="utf-8"))


def _plain(value: Any) -> Any:
    """Strip nested ``safe_value`` envelopes back to plain Python values."""
    if isinstance(value, dict):
        if set(value) >= {"type", "value"} and not value.get("value") and value.get("hex"):
            if value.get("type") == "string" and value.get("value") is None:
                return bytes.fromhex(str(value["hex"]))
        if set(value) >= {"type", "value"}:
            return _plain(value.get("value"))
        return {str(key): _plain(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_plain(item) for item in value]
    return value


_ZEND_TO_IC_TYPE = {
    "IS_CONST": 1,
    "IS_TMP_VAR": 2,
    "IS_VAR": 4,
    "IS_UNUSED": 0,
    "IS_CV": 8,
}
_IC_TYPE_NAMES = {0: "IS_UNUSED", 1: "IS_CONST", 2: "IS_TMP_VAR", 4: "IS_VAR", 8: "IS_CV"}


def _ic_operand_type(zend_type: int) -> int:
    """Map a zend operand kind (IS_CV = 16) onto our encoding (IS_CV = 8)."""
    if zend_type & 16:
        return 8
    if zend_type & 8:
        return 0
    if zend_type & 4:
        return 4
    if zend_type & 2:
        return 2
    if zend_type & 1:
        return 1
    return 0


def _raw_operand(operand: Any, jump_targets: set[int]) -> dict[str, Any]:
    if not isinstance(operand, dict):
        return {}
    operand_type = _ic_operand_type(operand.get("type") or 0)
    raw: dict[str, Any] = {
        "type": operand_type,
        "type_name": _IC_TYPE_NAMES[operand_type],
        "serialized_value": operand.get("num") or 0,
    }
    if operand_type == 1:
        raw["literal_index"] = operand.get("constant") or 0
        return raw
    if operand_type == 8:
        if operand.get("cv_index") is not None:
            raw["variable_index"] = operand["cv_index"]
        if isinstance(operand.get("cv_name"), str):
            raw["variable_name"] = operand["cv_name"]
    value = operand.get("num")
    if isinstance(value, int) and value in jump_targets:
        raw["jump_target"] = value
    return raw


def _raw_opcode(op: dict[str, Any], fallback_index: int) -> dict[str, Any]:
    jump_targets = {int(t) for t in (op.get("jump_targets") or []) if isinstance(t, int)}
    return {
        "index": op.get("index", fallback_index),
        "lineno": op.get("line") or 0,
        "opcode": op.get("opcode"),
        "opcode_name": op.get("opcode_name"),
        "extended_value": op.get("extended_value") or 0,
        "op1": _raw_operand(op.get("op1"), jump_targets),
        "op2": _raw_operand(op.get("op2"), jump_targets),
        "result": _raw_operand(op.get("result"), jump_targets),
    }


def _linked_arguments(op_array: dict[str, Any]) -> list[dict[str, Any]]:
    args = []
    for index, arg in enumerate(op_array.get("arg_info") or []):
        if not isinstance(arg, dict):
            continue
        args.append(
            {
                "index": index,
                "name": arg.get("name") or f"arg{index + 1}",
                "type_name": arg.get("type_name"),
                "class_name": arg.get("class_name"),
                "type_code": arg.get("type_code") or 0,
                "pass_by_reference": bool(arg.get("pass_by_reference")),
                "allow_null": bool(arg.get("allow_null")),
                "is_variadic": bool(arg.get("is_variadic")),
                "has_default": bool(arg.get("has_default")),
            }
        )
    return args


def _op_array_entry(
    op_array: dict[str, Any],
    *,
    source_file: str,
    kind: str,
    fallback_name: str,
) -> tuple[str, dict[str, Any]]:
    name = op_array.get("function_name")
    if not isinstance(name, str) or not name:
        name = fallback_name
    fn_flags = op_array.get("fn_flags") or 0
    raw = {
        "method": name,
        "table_name": name,
        "metadata": {
            "variables": [v for v in _plain(op_array.get("vars") or []) if isinstance(v, str)],
            "num_args": op_array.get("num_args") or 0,
            "required_num_args": op_array.get("required_num_args") or 0,
            "fn_flags": fn_flags,
            "line_start": op_array.get("line_start") or 0,
            "line_end": op_array.get("line_end") or 0,
            "last_var": op_array.get("last_var") or 0,
        },
        "literals": [{"value": _plain(lit)} for lit in (op_array.get("literals") or [])],
        "opcodes": [
            _raw_opcode(op, index)
            for index, op in enumerate(op_array.get("opcodes") or [])
        ],
        "temp_variable_count": op_array.get("T") or 0,
        "try_catch_raw": [],
        "status": {"source": "runtime_opcode_dump"},
    }
    op_id, entry = build_op_array_entry(raw, source_file, kind=kind)

    entry["arg_info"] = _linked_arguments(op_array)
    entry["num_args"] = op_array.get("num_args") or len(entry["arg_info"])
    entry["required_num_args"] = op_array.get("required_num_args") or 0
    return_type = op_array.get("return_type_info")
    if isinstance(return_type, dict) and return_type.get("type_name"):
        entry["return_type_info"] = {
            "type_name": return_type.get("class_name") or return_type.get("type_name"),
            "allow_null": bool(return_type.get("allow_null")),
            "type_code": return_type.get("type_code") or 0,
        }
    entry["scope"] = safe_value(_plain(op_array.get("scope")))
    entry["doc_comment"] = safe_value(_plain(op_array.get("doc_comment")))
    entry["static_variables"] = safe_value(_plain(op_array.get("static_variables")))
    entry["meta"]["source"] = safe_value("runtime_opcode_dump")
    if kind == "main":
        entry["strict_types"] = bool(fn_flags & 0x80000000)
    entry["live_range"] = [
        {k: int(r[k]) for k in ("tmp_var_start", "tmp_var_end") if isinstance(r.get(k), int)}
        for r in (op_array.get("live_range") or [])
        if isinstance(r, dict)
    ]
    return op_id, entry


def _class_entry(class_id: str, raw: dict[str, Any]) -> dict[str, Any]:
    name = _plain(raw.get("name"))
    parent = _plain(raw.get("parent"))
    flags = raw.get("ce_flags_decoded") or {}
    properties: dict[str, Any] = {}
    merged = raw.get("properties_merged")
    source_props = merged if isinstance(merged, dict) else {
        p.get("name"): p for p in (raw.get("properties_info") or []) if isinstance(p, dict)
    }
    for prop_name, prop in source_props.items():
        if not isinstance(prop, dict) or not prop_name:
            continue
        prop_flags = prop.get("flags_decoded") or {}
        entry = {
            "flags_decoded": {
                "visibility": prop_flags.get("visibility", "public"),
                "is_static": bool(prop_flags.get("is_static")),
            },
            "is_static": bool(prop.get("is_static") or prop_flags.get("is_static")),
            "has_default_value": bool(prop.get("has_default_value")),
        }
        if isinstance(prop.get("default_value"), dict) or prop.get("default_value") is not None:
            entry["default_value"] = safe_value(_plain(prop.get("default_value")))
        properties[str(prop_name)] = entry

    constants: dict[str, Any] = {}
    const_source = raw.get("constants_table") or {}
    if isinstance(const_source, dict):
        for const_name, const in const_source.items():
            value = const.get("value") if isinstance(const, dict) else const
            constants[str(const_name)] = {"value": safe_value(_plain(value))}

    return {
        "id": class_id,
        "name": name,
        "parent": parent,
        "interfaces": [i for i in (_plain(raw.get("interfaces")) or []) if isinstance(i, str)],
        "methods": {str(k): v for k, v in (raw.get("methods") or {}).items() if isinstance(v, str)},
        "ce_flags_decoded": {
            "is_interface": bool(flags.get("is_interface")),
            "is_trait": bool(flags.get("is_trait")),
            "is_abstract": bool(flags.get("is_abstract") or flags.get("is_explicit_abstract")),
            "is_final": bool(flags.get("is_final")),
            "is_anon": bool(flags.get("is_anon")),
        },
        "doc_comment": _plain(raw.get("doc_comment")),
        "properties_info": properties,
        "constants_table": constants,
    }


def to_icdump(runtime_ir: dict[str, Any], source_file: str) -> dict[str, Any]:
    """Convert an ``ic72dump-ir-v3`` document to ``icdump-ir-v1``."""
    op_arrays: dict[str, dict[str, Any]] = {}
    function_index: dict[str, str] = {}
    class_index: dict[str, dict[str, Any]] = {}

    for op_id, raw in (runtime_ir.get("op_arrays") or {}).items():
        if not isinstance(raw, dict):
            continue
        kind = raw.get("kind")
        if kind == "main" or op_id == "main":
            _, entry = _op_array_entry(raw, source_file=source_file, kind="main", fallback_name="main")
            op_arrays["main"] = entry
            continue
        fallback = op_id.rsplit(":", 1)[-1]
        try:
            fallback = bytes.fromhex(fallback).decode("utf-8")
        except ValueError:
            pass
        _, entry = _op_array_entry(
            raw, source_file=source_file, kind="function", fallback_name=fallback
        )
        op_arrays[op_id] = entry

    for name_hex, op_id in (runtime_ir.get("function_index") or {}).items():
        if op_id in op_arrays:
            function_index[str(name_hex)] = op_id
            name = _plain((runtime_ir["op_arrays"][op_id] or {}).get("function_name"))
            if isinstance(name, str):
                function_index[name.encode("utf-8").hex()] = op_id

    for class_id, raw in (runtime_ir.get("class_index") or {}).items():
        if isinstance(raw, dict):
            class_index[str(class_id)] = _class_entry(str(class_id), raw)

    return {
        "format": "icdump-ir-v1",
        "source_file": source_file,
        "summary": {
            "op_array_count": len(op_arrays),
            "function_count": len(function_index),
            "closure_count": 0,
            "class_count": len(class_index),
            "decompile_status": {
                "status": "runtime",
                "encoder": "ionCube",
                "source": "runtime_opcode_dump",
            },
        },
        "entry": "main",
        "op_arrays": op_arrays,
        "function_index": function_index,
        "closure_index": {},
        "class_index": class_index,
        "ioncube_api_calls": safe_value([]),
    }


def runtime_icdump(
    source: str | Path,
    php_version: int,
    *,
    timeout: int = 300,
) -> dict[str, Any] | None:
    """Full runtime path: dump *source* and normalize it. None if no runtime."""
    if find_runtime(php_version) is None:
        return None
    return to_icdump(dump_opcodes(source, php_version, timeout=timeout), str(source))
