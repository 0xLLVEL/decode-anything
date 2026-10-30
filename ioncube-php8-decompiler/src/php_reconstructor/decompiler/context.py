"""Decompilation context: shared mutable state while walking one op_array.

The Zend VM is a stack/temp machine: most opcodes produce a value in a
TMP/VAR slot that exactly one later opcode consumes.  We mirror that with
``temps`` -- a map from slot key to the AST expression that computes it.
Consuming an operand *pops* its entry, so anything left over at the end is
a decode anomaly (reported as a warning, surfaced as ``$tmpN``).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from .. import ast as php
from ..opcode import OpArray, Opcode, Operand
from ..utils.php_values import PhpBytes

if TYPE_CHECKING:
    from ..opcode import Program


@dataclass(slots=True)
class CallFrame:
    """A pending call between INIT_*CALL/NEW and its DO_FCALL."""

    kind: str  # func | method | static | new | dynamic | unknown
    name: Any = None          # str or Expr
    target: php.Expr | None = None     # object for method calls
    class_name: Any = None    # str or Expr for static calls / new
    args: list[php.Expr] = field(default_factory=list)
    new_result_key: int | None = None  # ZEND_NEW stores the object here


@dataclass(slots=True)
class LoopInfo:
    """Targets that mean break/continue while decompiling a loop body."""

    break_targets: set[int]
    continue_targets: set[int]


class DecompileContext:
    def __init__(self, op_array: OpArray, program: "Program | None" = None) -> None:
        self.op_array = op_array
        self.program = program
        self.ops = op_array.opcodes
        self.temps: dict[int, php.Expr] = {}
        self.call_stack: list[CallFrame] = []
        self.ropes: dict[int, list[php.Expr]] = {}
        self.silence_depth = 0
        self.silence_snapshots: list[set[int]] = []
        self.param_defaults: dict[int, php.Expr] = {}  # 1-based arg num -> default
        self.uses: list[str] = []                      # closure `use` variables
        self.lexical_names: set[str] = set()           # names imported via `use`
        self.static_decls: list[php.StaticVarStmt] = []
        self.loop_stack: list[LoopInfo] = []
        self.consumed_closures: set[str] = set()
        self.warnings: list[str] = []
        self.goto_targets: set[int] = set()    # opcode indexes needing a label
        self.labels_emitted: set[int] = set()  # labels already placed
        self._orphan_key = -1  # synthetic temp keys for results with var=null
        # Statement sinks: a stack of lists of (op_index, stmt).  Structured
        # regions (loop/if bodies) push a fresh sink, decompile into it, then
        # pop it to collect the body.
        self._sinks: list[list[tuple[int, php.Stmt]]] = [[]]

    # -- statement sinks ---------------------------------------------------

    def emit(self, op_index: int, stmt: php.Stmt) -> None:
        if self.silence_depth > 0:
            stmt = _apply_silence(stmt)
        self._sinks[-1].append((op_index, stmt))

    def push_sink(self) -> None:
        self._sinks.append([])

    def pop_sink(self) -> list[php.Stmt]:
        return [stmt for _, stmt in self._sinks.pop()]

    def pop_sink_tagged(self) -> list[tuple[int, php.Stmt]]:
        return self._sinks.pop()

    def current_sink(self) -> list[tuple[int, php.Stmt]]:
        return self._sinks[-1]

    def statements(self) -> list[php.Stmt]:
        return [stmt for _, stmt in self._sinks[0]]

    # -- operand resolution ------------------------------------------------

    def resolve(self, operand: Operand, op: Opcode | None = None) -> php.Expr:
        """Turn an operand into the expression that computes it (consuming)."""
        if operand.is_const:
            if operand.magic_constant:
                return php.ConstFetch(name=operand.magic_constant)
            return literal_to_expr(operand.const_value())
        if operand.is_cv:
            return php.Variable(self.cv_name(operand))
        if operand.is_temporary:
            key = operand.temp_key
            if key is not None and key in self.temps:
                return self.temps.pop(key)
            # ionCube dumps occasionally rewrite operand var numbers on
            # semantically-resolved opcodes, so the consumer's slot does not
            # match the producer's.  Zend temps live in near-stack order:
            # the value being consumed is almost always the most recently
            # produced live temp, so reconcile LIFO instead of leaking $tmpN.
            if self.temps:
                newest_key = next(reversed(self.temps))
                self.warn(
                    f"op {op.index if op else '?'}: temp t{key} missing; "
                    f"reconciled with newest live temp t{newest_key}"
                )
                return self.temps.pop(newest_key)
            self.warn(
                f"op {op.index if op else '?'}: temp t{key} consumed before being produced"
            )
            return php.TempVar(key or 0)
        self.warn(f"op {op.index if op else '?'}: resolving IS_UNUSED operand")
        return php.Literal(None)

    def peek(self, operand: Operand) -> php.Expr | None:
        key = operand.temp_key
        if key is not None:
            return self.temps.get(key)
        return None

    def store(self, operand: Operand, expr: php.Expr, op: Opcode | None = None) -> None:
        key = operand.temp_key
        if key is not None:
            self.temps[key] = expr
        elif operand.is_temporary:
            # Semantically-resolved ionCube opcodes sometimes lose the result
            # var number.  Park the value under a synthetic key so LIFO
            # reconciliation in resolve() can still hand it to its consumer.
            self.temps[self._orphan_key] = expr
            self._orphan_key -= 1
        elif not operand.is_unused:
            self.warn(f"op {op.index if op else '?'}: cannot store result")

    def cv_name(self, operand: Operand) -> str:
        if operand.cv_name:
            return operand.cv_name
        if operand.cv_index is not None and operand.cv_index < len(self.op_array.vars):
            return self.op_array.vars[operand.cv_index]
        if operand.var is not None:
            # CV slots start after the fixed execute_data header (3 slots of 16).
            index = operand.var // 16 - 3
            if 0 <= index < len(self.op_array.vars):
                return self.op_array.vars[index]
            return f"_cv{max(index, 0)}"
        return "_cv"

    def this_or(self, operand: Operand, op: Opcode | None = None) -> php.Expr:
        """Object operand: IS_UNUSED conventionally means ``$this``."""
        if operand.is_unused:
            return php.Variable("this")
        return self.resolve(operand, op)

    # -- misc ----------------------------------------------------------------

    def warn(self, message: str) -> None:
        self.warnings.append(f"{self.op_array.id}: {message}")


def literal_to_expr(value: Any) -> php.Expr:
    """Convert an unwrapped PHP literal (from safe_value) into an AST node."""
    if isinstance(value, dict):
        ref_name = value.get("__constant_ref__")
        if isinstance(ref_name, str) and ref_name:
            return php.ConstFetch(name=ref_name)
        items = []
        keys = list(value.keys())
        is_list = all(
            isinstance(k, int) or (isinstance(k, str) and k.isdigit()) for k in keys
        ) and [int(k) for k in keys] == list(range(len(keys)))
        for key, item in value.items():
            key_expr = None
            if not is_list:
                key_expr = php.Literal(int(key) if isinstance(key, str) and _is_int(key) else key)
            items.append(php.ArrayItem(value=literal_to_expr(item), key=key_expr))
        return php.ArrayLiteral(items)
    if isinstance(value, (PhpBytes, bytes)):
        return php.Literal(PhpBytes(value))
    return php.Literal(value)


def _is_int(text: str) -> bool:
    try:
        int(text)
        return True
    except ValueError:
        return False


def _apply_silence(stmt: php.Stmt) -> php.Stmt:
    """Wrap a statement's top-level expression in ``@`` while silencing."""
    if isinstance(stmt, php.ExprStmt) and not isinstance(stmt.expr, php.ErrorSuppress):
        if isinstance(stmt.expr, php.Assign):
            assign = stmt.expr
            if not isinstance(assign.value, php.ErrorSuppress):
                assign.value = php.ErrorSuppress(assign.value)
            return stmt
        stmt.expr = php.ErrorSuppress(stmt.expr)
    return stmt


def has_side_effects(expr: php.Expr) -> bool:
    """Conservative: does evaluating this expression do anything observable?"""
    if isinstance(expr, (php.FuncCall, php.MethodCall, php.StaticCall, php.New,
                         php.Assign, php.IncDec, php.IncludeExpr, php.ExitExpr,
                         php.ErrorSuppress, php.RawExpr)):
        return True
    if isinstance(expr, php.BinaryOp):
        return has_side_effects(expr.left) or has_side_effects(expr.right)
    if isinstance(expr, (php.UnaryOp, php.Cast)):
        return has_side_effects(expr.operand)
    if isinstance(expr, php.Ternary):
        return (
            has_side_effects(expr.cond)
            or (expr.if_true is not None and has_side_effects(expr.if_true))
            or has_side_effects(expr.if_false)
        )
    if isinstance(expr, php.DimFetch):
        return has_side_effects(expr.target) or (
            expr.index is not None and has_side_effects(expr.index)
        )
    if isinstance(expr, php.PropertyFetch):
        return has_side_effects(expr.target)
    if isinstance(expr, php.ArrayLiteral):
        return any(has_side_effects(item.value) for item in expr.items)
    return False
