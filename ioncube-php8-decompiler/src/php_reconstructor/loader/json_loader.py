"""Load an icdump-ir-v1 JSON dump into the normalized :class:`Program` model."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ..opcode import OpArray, PhpClassInfo, PhpProperty, Program
from ..utils import unwrap_safe_value

SUPPORTED_FORMATS = {"icdump-ir-v1"}


class DumpFormatError(ValueError):
    """Raised when the input JSON is not a recognizable opcode dump."""


def load_dump(path: str | Path) -> Program:
    with open(path, encoding="utf-8") as handle:
        try:
            data = json.load(handle)
        except json.JSONDecodeError as exc:
            raise DumpFormatError(f"{path}: not valid JSON ({exc})") from exc
    return parse_dump(data, source=str(path))


def parse_dump(data: Any, source: str = "<memory>") -> Program:
    if not isinstance(data, dict):
        raise DumpFormatError(f"{source}: top-level JSON value must be an object")
    dump_format = data.get("format")
    if "op_arrays" not in data:
        raise DumpFormatError(
            f"{source}: missing 'op_arrays' key"
            + (f" (format={dump_format!r})" if dump_format else "")
        )

    program = Program(
        source_file=data.get("source_file") if isinstance(data.get("source_file"), str) else None,
        dump_format=dump_format if isinstance(dump_format, str) else None,
        entry=data.get("entry") if isinstance(data.get("entry"), str) else None,
    )

    op_arrays = data.get("op_arrays")
    if isinstance(op_arrays, dict):
        for oa_id, raw in op_arrays.items():
            if isinstance(raw, dict):
                program.op_arrays[str(oa_id)] = OpArray.from_json(str(oa_id), raw)

    for index_key, target in (("function_index", program.function_index),
                              ("closure_index", program.closure_index)):
        raw_index = data.get(index_key)
        if isinstance(raw_index, dict):
            for key, oa_id in raw_index.items():
                if isinstance(oa_id, str):
                    target[str(key)] = oa_id

    class_index = data.get("class_index")
    if isinstance(class_index, dict):
        for class_id, raw in class_index.items():
            if isinstance(raw, dict):
                program.classes[str(class_id)] = _parse_class(str(class_id), raw)

    return program


def _parse_class(class_id: str, raw: dict[str, Any]) -> PhpClassInfo:
    name = unwrap_safe_value(raw.get("name"))
    parent = unwrap_safe_value(raw.get("parent"))
    flags = raw.get("ce_flags_decoded") or {}

    info = PhpClassInfo(
        id=class_id,
        name=name if isinstance(name, str) else class_id,
        parent=parent if isinstance(parent, str) else None,
        interfaces=[i for i in (raw.get("interfaces") or []) if isinstance(i, str)],
        is_abstract=bool(flags.get("is_abstract") or flags.get("is_explicit_abstract")),
        is_final=bool(flags.get("is_final")),
        is_interface=bool(flags.get("is_interface")),
        doc_comment=_doc_comment(raw.get("doc_comment")),
    )

    constants = raw.get("constants_table")
    if isinstance(constants, dict):
        for const_name, const_raw in constants.items():
            if isinstance(const_raw, dict) and "value" in const_raw:
                info.constants[str(const_name)] = unwrap_safe_value(const_raw["value"])
            else:
                info.constants[str(const_name)] = unwrap_safe_value(const_raw)

    properties = raw.get("properties_merged")
    if not isinstance(properties, dict):
        properties = raw.get("properties_info") if isinstance(raw.get("properties_info"), dict) else {}
    for prop_name, prop_raw in properties.items():
        if not isinstance(prop_raw, dict):
            continue
        prop_flags = prop_raw.get("flags_decoded") or {}
        visibility = prop_flags.get("visibility")
        info.properties.append(
            PhpProperty(
                name=str(prop_name),
                visibility=visibility if visibility in ("public", "protected", "private") else "public",
                is_static=bool(prop_raw.get("is_static") or prop_flags.get("is_static")),
                has_default=bool(prop_raw.get("has_default_value")),
                default=unwrap_safe_value(prop_raw.get("default_value")),
                doc_comment=_doc_comment(prop_raw.get("doc_comment")),
            )
        )

    methods = raw.get("methods")
    if isinstance(methods, dict):
        for method_name, oa_id in methods.items():
            if isinstance(oa_id, str):
                info.methods[str(method_name)] = oa_id

    return info


def _doc_comment(raw: Any) -> str | None:
    value = unwrap_safe_value(raw)
    return value if isinstance(value, str) else None
