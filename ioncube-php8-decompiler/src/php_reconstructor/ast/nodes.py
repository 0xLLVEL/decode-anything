"""PHP AST node definitions.

A deliberately small, decompiler-oriented AST: enough to express the PHP
constructs we can recover from opcodes, plus :class:`OpcodeComment` as a
safe fallback for anything we cannot.

Every node supports ``to_dict()`` for ``--dump-ast``.
"""

from __future__ import annotations

from dataclasses import dataclass, field, fields, is_dataclass
from typing import Any

from ..utils.php_values import PhpBytes


class Node:
    """Base class for all AST nodes."""

    def to_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = {"node": type(self).__name__}
        assert is_dataclass(self)
        for f in fields(self):
            result[f.name] = _dictify(getattr(self, f.name))
        return result


def _dictify(value: Any) -> Any:
    if isinstance(value, Node):
        return value.to_dict()
    if isinstance(value, (list, tuple)):
        return [_dictify(v) for v in value]
    if isinstance(value, PhpBytes):
        return {"php_bytes_hex": value.hex()}
    return value


class Expr(Node):
    pass


class Stmt(Node):
    pass


# --------------------------------------------------------------------------
# Expressions
# --------------------------------------------------------------------------

@dataclass
class Literal(Expr):
    """Scalar literal: int, float, str, bool, None or PhpBytes."""
    value: Any = None


@dataclass
class ArrayItem(Node):
    value: Expr = field(default_factory=Literal)
    key: Expr | None = None
    by_ref: bool = False


@dataclass
class ArrayLiteral(Expr):
    items: list[ArrayItem] = field(default_factory=list)


@dataclass
class Variable(Expr):
    name: Any = ""  # str or Expr for dynamic variable names ($$var, ${$expr})


@dataclass
class TempVar(Expr):
    """Internal temporary that survived expression inlining ($tmpN)."""
    key: int = 0

    @property
    def name(self) -> str:
        return f"tmp{self.key}"


@dataclass
class ConstFetch(Expr):
    name: str = ""


@dataclass
class ClassConstFetch(Expr):
    class_name: str = ""
    const_name: str = ""


@dataclass
class PropertyFetch(Expr):
    target: Expr = field(default_factory=Variable)
    name: Any = ""  # str or Expr for dynamic fetches
    nullsafe: bool = False


@dataclass
class StaticPropertyFetch(Expr):
    class_name: str = ""
    name: str = ""


@dataclass
class DimFetch(Expr):
    target: Expr = field(default_factory=Variable)
    index: Expr | None = None  # None -> append [] (only valid as assign target)


@dataclass
class BinaryOp(Expr):
    op: str = "+"
    left: Expr = field(default_factory=Literal)
    right: Expr = field(default_factory=Literal)


@dataclass
class UnaryOp(Expr):
    op: str = "!"
    operand: Expr = field(default_factory=Literal)


@dataclass
class Cast(Expr):
    type: str = "int"
    operand: Expr = field(default_factory=Literal)


@dataclass
class Assign(Expr):
    target: Expr = field(default_factory=Variable)
    value: Expr = field(default_factory=Literal)
    op: str | None = None     # compound assignment operator ('.', '+', ...)
    by_ref: bool = False


@dataclass
class IncDec(Expr):
    target: Expr = field(default_factory=Variable)
    op: str = "++"
    is_prefix: bool = True


@dataclass
class FuncCall(Expr):
    name: Any = ""  # str or Expr for dynamic calls
    args: list[Expr] = field(default_factory=list)


@dataclass
class MethodCall(Expr):
    target: Expr = field(default_factory=Variable)
    name: Any = ""
    args: list[Expr] = field(default_factory=list)
    nullsafe: bool = False


@dataclass
class StaticCall(Expr):
    class_name: Any = ""
    name: Any = ""
    args: list[Expr] = field(default_factory=list)


@dataclass
class New(Expr):
    class_name: Any = ""
    args: list[Expr] = field(default_factory=list)


@dataclass
class Ternary(Expr):
    cond: Expr = field(default_factory=Literal)
    if_true: Expr | None = None  # None -> short ternary (?:)
    if_false: Expr = field(default_factory=Literal)


@dataclass
class Isset(Expr):
    exprs: list[Expr] = field(default_factory=list)


@dataclass
class EmptyExpr(Expr):
    operand: Expr = field(default_factory=Literal)


@dataclass
class InstanceOf(Expr):
    operand: Expr = field(default_factory=Literal)
    class_name: Any = ""


@dataclass
class ErrorSuppress(Expr):
    operand: Expr = field(default_factory=Literal)


@dataclass
class IncludeExpr(Expr):
    kind: str = "include"  # include | include_once | require | require_once | eval
    operand: Expr = field(default_factory=Literal)


@dataclass
class ExitExpr(Expr):
    operand: Expr | None = None


@dataclass
class ClosureExpr(Expr):
    params: list["Param"] = field(default_factory=list)
    uses: list[str] = field(default_factory=list)
    body: list[Stmt] = field(default_factory=list)
    is_static: bool = False


@dataclass
class MatchArm(Node):
    conds: list[Expr] | None = None  # None -> default arm
    body: Expr = field(default_factory=Literal)


@dataclass
class MatchExpr(Expr):
    subject: Expr = field(default_factory=Variable)
    arms: list[MatchArm] = field(default_factory=list)


@dataclass
class RawExpr(Expr):
    """Escape hatch: raw PHP snippet (used by fallbacks only)."""
    code: str = ""


# --------------------------------------------------------------------------
# Statements
# --------------------------------------------------------------------------

@dataclass
class ExprStmt(Stmt):
    expr: Expr = field(default_factory=Literal)


@dataclass
class EchoStmt(Stmt):
    exprs: list[Expr] = field(default_factory=list)


@dataclass
class ReturnStmt(Stmt):
    value: Expr | None = None


@dataclass
class IfStmt(Stmt):
    cond: Expr = field(default_factory=Literal)
    then: list[Stmt] = field(default_factory=list)
    elifs: list[tuple[Expr, list[Stmt]]] = field(default_factory=list)
    orelse: list[Stmt] = field(default_factory=list)


@dataclass
class WhileStmt(Stmt):
    cond: Expr = field(default_factory=Literal)
    body: list[Stmt] = field(default_factory=list)


@dataclass
class DoWhileStmt(Stmt):
    body: list[Stmt] = field(default_factory=list)
    cond: Expr = field(default_factory=Literal)


@dataclass
class ForeachStmt(Stmt):
    iterable: Expr = field(default_factory=Variable)
    value_var: Expr = field(default_factory=Variable)
    key_var: Expr | None = None
    by_ref: bool = False
    body: list[Stmt] = field(default_factory=list)


@dataclass
class SwitchCase(Node):
    test: Expr | None = None  # None -> `default:`
    body: list[Stmt] = field(default_factory=list)


@dataclass
class SwitchStmt(Stmt):
    subject: Expr = field(default_factory=Literal)
    cases: list[SwitchCase] = field(default_factory=list)


@dataclass
class BreakStmt(Stmt):
    level: int = 1


@dataclass
class ContinueStmt(Stmt):
    level: int = 1


@dataclass
class GlobalStmt(Stmt):
    names: list[str] = field(default_factory=list)


@dataclass
class StaticVarStmt(Stmt):
    name: str = ""
    default: Expr | None = None


@dataclass
class UnsetStmt(Stmt):
    exprs: list[Expr] = field(default_factory=list)


@dataclass
class ThrowStmt(Stmt):
    expr: Expr = field(default_factory=Literal)


@dataclass
class CatchClause(Node):
    class_names: list[str] = field(default_factory=list)
    var_name: str | None = None
    body: list[Stmt] = field(default_factory=list)


@dataclass
class TryStmt(Stmt):
    body: list[Stmt] = field(default_factory=list)
    catches: list[CatchClause] = field(default_factory=list)
    finally_body: list[Stmt] | None = None


@dataclass
class CommentStmt(Stmt):
    text: str = ""


@dataclass
class OpcodeComment(Stmt):
    """Fallback for opcodes we cannot reconstruct -- keeps output valid PHP."""
    opcode_index: int = 0
    opcode_name: str = ""
    detail: str = ""


@dataclass
class GotoStmt(Stmt):
    """`goto <label>;` -- emitted for forward jumps that are not structurable."""
    label: str = ""


@dataclass
class LabelStmt(Stmt):
    """`<label>:` -- a jump target referenced by one or more GotoStmt."""
    label: str = ""


# --------------------------------------------------------------------------
# Declarations
# --------------------------------------------------------------------------

@dataclass
class Param(Node):
    name: str = ""
    type: str | None = None
    nullable: bool = False
    by_ref: bool = False
    variadic: bool = False
    default: Expr | None = None


@dataclass
class FunctionDecl(Stmt):
    name: str = ""
    params: list[Param] = field(default_factory=list)
    body: list[Stmt] = field(default_factory=list)
    return_type: str | None = None
    return_nullable: bool = False
    by_ref: bool = False
    doc_comment: str | None = None


@dataclass
class MethodDecl(Node):
    name: str = ""
    params: list[Param] = field(default_factory=list)
    body: list[Stmt] = field(default_factory=list)
    visibility: str = "public"
    is_static: bool = False
    is_abstract: bool = False
    is_final: bool = False
    return_type: str | None = None
    return_nullable: bool = False
    by_ref: bool = False
    doc_comment: str | None = None


@dataclass
class PropertyDecl(Node):
    name: str = ""
    visibility: str = "public"
    is_static: bool = False
    is_readonly: bool = False
    type: str | None = None
    is_nullable: bool = False
    default: Expr | None = None
    doc_comment: str | None = None


@dataclass
class ClassConstDecl(Node):
    name: str = ""
    value: Expr = field(default_factory=Literal)


@dataclass
class ClassDecl(Stmt):
    name: str = ""
    parent: str | None = None
    interfaces: list[str] = field(default_factory=list)
    is_abstract: bool = False
    is_final: bool = False
    is_interface: bool = False
    constants: list[ClassConstDecl] = field(default_factory=list)
    properties: list[PropertyDecl] = field(default_factory=list)
    methods: list[MethodDecl] = field(default_factory=list)
    doc_comment: str | None = None


@dataclass
class PhpFile(Node):
    statements: list[Stmt] = field(default_factory=list)
    header_comment: str | None = None
