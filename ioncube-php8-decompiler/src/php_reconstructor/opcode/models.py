"""Normalized opcode model: stable internal representation of a dump.

Everything downstream (IR, decompiler, AST) consumes only these classes,
never raw JSON dicts.  The model is intentionally tolerant: missing keys
become ``None`` so partially-decoded dumps still load.

Operand caveat (important): the dump serializes *all* operand fields for
every operand, so an ``IS_UNUSED`` operand still carries garbage in
``var``/``num``/``opline_num``.  Always check :attr:`Operand.kind` before
reading positional fields.
"""

from __future__ import annotations

import enum
from dataclasses import dataclass, field
from typing import Any

from ..utils import unwrap_safe_value


class OperandKind(enum.Enum):
    UNUSED = "IS_UNUSED"
    CONST = "IS_CONST"
    TMP = "IS_TMP_VAR"
    VAR = "IS_VAR"
    CV = "IS_CV"
    UNKNOWN = "?"

    @classmethod
    def from_type_name(cls, type_name: object) -> "OperandKind":
        if isinstance(type_name, str):
            for member in cls:
                if member.value == type_name:
                    return member
        return cls.UNKNOWN

    @classmethod
    def from_type_mask(cls, type_value: object) -> "OperandKind":
        """Fallback: derive the kind from the numeric zend type mask.

        ionCube-decoded opcodes sometimes carry extra flag bits (e.g. 18 =
        16 | IS_TMP_VAR) with no resolved type_name.
        """
        if not isinstance(type_value, int):
            return cls.UNKNOWN
        if type_value == 0:
            return cls.UNUSED
        if type_value & 8:
            return cls.CV
        if type_value & 2:
            return cls.TMP
        if type_value & 4:
            return cls.VAR
        if type_value & 1:
            return cls.CONST
        return cls.UNKNOWN


@dataclass(frozen=True, slots=True)
class Operand:
    kind: OperandKind = OperandKind.UNUSED
    var: int | None = None
    num: int | None = None
    opline_num: int | None = None
    cv_name: str | None = None
    cv_index: int | None = None
    constant: int | None = None
    has_literal: bool = False
    literal: Any = None
    resolved_literal: Any = None
    magic_constant: str | None = None

    @property
    def is_unused(self) -> bool:
        return self.kind is OperandKind.UNUSED

    @property
    def is_const(self) -> bool:
        return self.kind is OperandKind.CONST

    @property
    def is_cv(self) -> bool:
        return self.kind is OperandKind.CV

    @property
    def is_temporary(self) -> bool:
        return self.kind in (OperandKind.TMP, OperandKind.VAR)

    @property
    def temp_key(self) -> int | None:
        """Key identifying this TMP/VAR slot inside one op_array."""
        if self.is_temporary and self.var is not None:
            return int(self.var)
        return None

    def const_value(self) -> Any:
        """Best literal value: preserve casing from raw literal if same text."""
        if self.resolved_literal is not None:
            if isinstance(self.literal, str) and isinstance(self.resolved_literal, str):
                if self.literal.lower() == self.resolved_literal.lower():
                    return self.literal
            return self.resolved_literal
        return self.literal

    @classmethod
    def from_json(cls, raw: object) -> "Operand":
        if not isinstance(raw, dict):
            return cls()
        kind = OperandKind.from_type_name(raw.get("type_name"))
        if kind is OperandKind.UNKNOWN:
            kind = OperandKind.from_type_mask(raw.get("type"))
        has_literal = "literal" in raw
        return cls(
            kind=kind,
            var=_opt_int(raw.get("var")),
            num=_opt_int(raw.get("num")),
            opline_num=_opt_int(raw.get("opline_num")),
            cv_name=raw.get("cv_name") if isinstance(raw.get("cv_name"), str) else None,
            cv_index=_opt_int(raw.get("cv_index")),
            constant=_opt_int(raw.get("constant")),
            has_literal=has_literal,
            literal=unwrap_safe_value(raw.get("literal")) if has_literal else None,
            resolved_literal=unwrap_safe_value(raw.get("resolved_literal"))
            if "resolved_literal" in raw
            else None,
            magic_constant=raw.get("magic_constant")
            if isinstance(raw.get("magic_constant"), str)
            else None,
        )


@dataclass(slots=True)
class Opcode:
    index: int
    name: str
    number: int | None = None
    line: int | None = None
    extended_value: int | None = None
    op1: Operand = field(default_factory=Operand)
    op2: Operand = field(default_factory=Operand)
    result: Operand = field(default_factory=Operand)
    jump_targets: tuple[int, ...] = ()
    call_name: str | None = None
    fe_fetch_done_opline: int | None = None
    decode_failed: bool = False
    raw: dict[str, Any] = field(default_factory=dict, repr=False)

    @property
    def short_name(self) -> str:
        return self.name.removeprefix("ZEND_")

    @classmethod
    def from_json(cls, raw: object, index: int) -> "Opcode":
        if not isinstance(raw, dict):
            return cls(index=index, name="<invalid>", decode_failed=True)
        name = raw.get("opcode_name")
        if not isinstance(name, str) or not name:
            name = f"#{raw.get('opcode', '?')}"
        targets = raw.get("jump_targets")
        return cls(
            index=_opt_int(raw.get("index"), index) or index,
            name=name,
            number=_opt_int(raw.get("opcode")),
            line=_opt_int(raw.get("line")),
            extended_value=_opt_int(raw.get("extended_value")),
            op1=Operand.from_json(raw.get("op1")),
            op2=Operand.from_json(raw.get("op2")),
            result=Operand.from_json(raw.get("result")),
            jump_targets=tuple(int(t) for t in targets) if isinstance(targets, list) else (),
            call_name=raw.get("call_name") if isinstance(raw.get("call_name"), str) else None,
            fe_fetch_done_opline=_opt_int(raw.get("fe_fetch_done_opline")),
            decode_failed=bool(raw.get("decode_failed")),
            raw=raw,
        )


@dataclass(slots=True)
class ArgInfo:
    index: int
    name: str | None = None
    type_name: str | None = None
    pass_by_reference: bool = False
    allow_null: bool = False
    is_variadic: bool = False
    has_default: bool | None = None

    @classmethod
    def from_json(cls, raw: object, index: int) -> "ArgInfo":
        if not isinstance(raw, dict):
            return cls(index=index)
        return cls(
            index=_opt_int(raw.get("index"), index) or index,
            name=raw.get("name") if isinstance(raw.get("name"), str) else None,
            type_name=raw.get("type_name") if isinstance(raw.get("type_name"), str) else None,
            pass_by_reference=bool(raw.get("pass_by_reference")),
            allow_null=bool(raw.get("allow_null")),
            is_variadic=bool(raw.get("is_variadic")),
            has_default=raw.get("has_default") if isinstance(raw.get("has_default"), bool) else None,
        )


@dataclass(slots=True)
class TryCatchEntry:
    try_op: int | None = None
    catch_op: int | None = None
    finally_op: int | None = None
    finally_end: int | None = None


@dataclass(slots=True)
class OpArray:
    id: str
    kind: str  # main | function | closure | method
    function_name: str | None = None
    class_id: str | None = None
    line_start: int | None = None
    line_end: int | None = None
    fn_flags: int | None = None
    fn_flags_decoded: dict[str, Any] = field(default_factory=dict)
    num_args: int | None = None
    required_num_args: int | None = None
    args: list[ArgInfo] = field(default_factory=list)
    return_type: str | None = None
    return_allow_null: bool = False
    doc_comment: str | None = None
    vars: list[str] = field(default_factory=list)
    static_variables: dict[str, Any] | None = None
    try_catch: list[TryCatchEntry] = field(default_factory=list)
    literals: list[Any] = field(default_factory=list)
    opcodes: list[Opcode] = field(default_factory=list)
    meta: dict[str, Any] = field(default_factory=dict)

    @property
    def is_static(self) -> bool:
        return bool(self.fn_flags_decoded.get("is_static"))

    @property
    def visibility(self) -> str | None:
        vis = self.fn_flags_decoded.get("visibility")
        return vis if vis in ("public", "protected", "private") else None

    @property
    def returns_reference(self) -> bool:
        return bool(self.fn_flags_decoded.get("returns_reference"))

    @classmethod
    def from_json(cls, oa_id: str, raw: dict[str, Any]) -> "OpArray":
        fn_name = unwrap_safe_value(raw.get("function_name"))
        meta = raw.get("meta") if isinstance(raw.get("meta"), dict) else {}
        ret_info = raw.get("return_type_info")
        ret_type = None
        ret_nullable = False
        if isinstance(ret_info, dict):
            ret_type = ret_info.get("type_name") if isinstance(ret_info.get("type_name"), str) else None
            ret_nullable = bool(ret_info.get("allow_null"))

        vars_value = unwrap_safe_value(raw.get("vars"))
        var_names: list[str] = []
        if isinstance(vars_value, dict):
            var_names = [v for v in vars_value.values() if isinstance(v, str)]
        elif isinstance(vars_value, list):
            var_names = [v for v in vars_value if isinstance(v, str)]

        statics = unwrap_safe_value(raw.get("static_variables"))

        try_catch = []
        for entry in raw.get("try_catch") or []:
            if isinstance(entry, dict):
                try_catch.append(
                    TryCatchEntry(
                        try_op=_opt_int(entry.get("try_op")),
                        catch_op=_opt_int(entry.get("catch_op")),
                        finally_op=_opt_int(entry.get("finally_op")),
                        finally_end=_opt_int(entry.get("finally_end")),
                    )
                )

        raw_ops = raw.get("opcodes") if isinstance(raw.get("opcodes"), list) else []
        raw_args = raw.get("arg_info") if isinstance(raw.get("arg_info"), list) else []
        raw_literals = raw.get("literals") if isinstance(raw.get("literals"), list) else []

        return cls(
            id=oa_id,
            kind=raw.get("kind") if isinstance(raw.get("kind"), str) else "function",
            function_name=fn_name if isinstance(fn_name, str) else None,
            class_id=meta.get("class") if isinstance(meta.get("class"), str) else None,
            line_start=_opt_int(raw.get("line_start")),
            line_end=_opt_int(raw.get("line_end")),
            fn_flags=_opt_int(raw.get("fn_flags")),
            fn_flags_decoded=raw.get("fn_flags_decoded") or {},
            num_args=_opt_int(raw.get("num_args")),
            required_num_args=_opt_int(raw.get("required_num_args")),
            args=[ArgInfo.from_json(a, i) for i, a in enumerate(raw_args)],
            return_type=ret_type,
            return_allow_null=ret_nullable,
            doc_comment=_opt_str(unwrap_safe_value(raw.get("doc_comment"))),
            vars=var_names,
            static_variables=statics if isinstance(statics, dict) else None,
            try_catch=try_catch,
            literals=[unwrap_safe_value(lit) for lit in raw_literals],
            opcodes=[Opcode.from_json(op, i) for i, op in enumerate(raw_ops)],
            meta=meta,
        )


@dataclass(slots=True)
class PhpProperty:
    name: str
    visibility: str = "public"
    is_static: bool = False
    is_readonly: bool = False
    type_name: str | None = None
    allow_null: bool = False
    has_default: bool = False
    default: Any = None
    doc_comment: str | None = None


@dataclass(slots=True)
class PhpClassInfo:
    id: str
    name: str
    parent: str | None = None
    interfaces: list[str] = field(default_factory=list)
    is_abstract: bool = False
    is_final: bool = False
    is_interface: bool = False
    constants: dict[str, Any] = field(default_factory=dict)
    properties: list[PhpProperty] = field(default_factory=list)
    methods: dict[str, str] = field(default_factory=dict)  # method name -> op_array id
    doc_comment: str | None = None


@dataclass(slots=True)
class Program:
    """A fully loaded dump: every op_array plus the class/function indexes."""

    source_file: str | None = None
    dump_format: str | None = None
    entry: str | None = None
    op_arrays: dict[str, OpArray] = field(default_factory=dict)
    function_index: dict[str, str] = field(default_factory=dict)  # hex key -> op_array id
    closure_index: dict[str, str] = field(default_factory=dict)
    classes: dict[str, PhpClassInfo] = field(default_factory=dict)

    @property
    def main(self) -> OpArray | None:
        if self.entry and self.entry in self.op_arrays:
            return self.op_arrays[self.entry]
        return self.op_arrays.get("main")

    def functions(self) -> list[OpArray]:
        return [oa for oa in self.op_arrays.values() if oa.kind == "function"]

    def closures(self) -> list[OpArray]:
        return [oa for oa in self.op_arrays.values() if oa.kind == "closure"]


def _opt_int(value: object, default: int | None = None) -> int | None:
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, (int, float)):
        return int(value)
    if isinstance(value, str):
        try:
            return int(value, 0)
        except ValueError:
            return default
    return default


def _opt_str(value: object) -> str | None:
    return value if isinstance(value, str) else None
