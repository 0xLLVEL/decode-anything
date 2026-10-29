"""Handlers for echo/return/exit/throw, silence, ropes, includes, globals,
type checks and closures."""

from __future__ import annotations

from ... import ast as php
from ...decompiler.context import DecompileContext
from ...opcode import Opcode
from ...opcode.constants import INCLUDE_KINDS, TYPE_CHECK_FUNCS
from . import opcode_handler


@opcode_handler("ZEND_ECHO")
def handle_echo(ctx: DecompileContext, op: Opcode) -> None:
    ctx.emit(op.index, php.EchoStmt(exprs=[ctx.resolve(op.op1, op)]))


@opcode_handler("ZEND_RETURN", "ZEND_RETURN_BY_REF")
def handle_return(ctx: DecompileContext, op: Opcode) -> None:
    if op.op1.is_unused:
        ctx.emit(op.index, php.ReturnStmt(value=None))
        return
    value = ctx.resolve(op.op1, op)
    if isinstance(value, php.Literal) and value.value is None:
        is_void = ctx.op_array.return_type in ("void", "never")
        is_last = op.index == len(ctx.op_array.opcodes) - 1
        is_implicit = op.extended_value == -1 or is_last
        if is_void or is_implicit:
            ctx.emit(op.index, php.ReturnStmt(value=None))
            return
        ctx.emit(op.index, php.ReturnStmt(value=php.Literal(value=None)))
        return
    ctx.emit(op.index, php.ReturnStmt(value=value))


@opcode_handler("ZEND_EXIT")
def handle_exit(ctx: DecompileContext, op: Opcode) -> None:
    arg = None if op.op1.is_unused else ctx.resolve(op.op1, op)
    ctx.emit(op.index, php.ExprStmt(php.ExitExpr(operand=arg)))


@opcode_handler("ZEND_THROW")
def handle_throw(ctx: DecompileContext, op: Opcode) -> None:
    ctx.emit(op.index, php.ThrowStmt(expr=ctx.resolve(op.op1, op)))


@opcode_handler("ZEND_BEGIN_SILENCE")
def handle_begin_silence(ctx: DecompileContext, op: Opcode) -> None:
    # No temp stored: the silence marker is bookkeeping, not a value, and a
    # placeholder would pollute LIFO temp reconciliation.
    ctx.silence_depth += 1
    ctx.silence_snapshots.append(set(ctx.temps))


@opcode_handler("ZEND_END_SILENCE")
def handle_end_silence(ctx: DecompileContext, op: Opcode) -> None:
    ctx.silence_depth = max(0, ctx.silence_depth - 1)
    before = ctx.silence_snapshots.pop() if ctx.silence_snapshots else set()
    key = op.op1.temp_key
    if key is not None:
        ctx.temps.pop(key, None)
    # The silenced expression usually lives in the newest temp (e.g.
    # `$x = @curl_getinfo(...)`); wrap it so the `@` is not lost -- but only
    # if that temp was actually produced inside the silenced window.
    if ctx.temps:
        newest_key = next(reversed(ctx.temps))
        value = ctx.temps[newest_key]
        if newest_key not in before and not isinstance(value, php.ErrorSuppress):
            ctx.temps[newest_key] = php.ErrorSuppress(operand=value)


@opcode_handler("ZEND_ROPE_INIT")
def handle_rope_init(ctx: DecompileContext, op: Opcode) -> None:
    key = op.result.temp_key or 0
    ctx.ropes[key] = [ctx.resolve(op.op2, op)]


@opcode_handler("ZEND_ROPE_ADD")
def handle_rope_add(ctx: DecompileContext, op: Opcode) -> None:
    key = op.op1.temp_key or 0
    ctx.ropes.setdefault(key, []).append(ctx.resolve(op.op2, op))
    if op.result.temp_key is not None and op.result.temp_key != key:
        ctx.ropes[op.result.temp_key] = ctx.ropes.pop(key)


@opcode_handler("ZEND_ROPE_END")
def handle_rope_end(ctx: DecompileContext, op: Opcode) -> None:
    key = op.op1.temp_key or 0
    pieces = ctx.ropes.pop(key, [])
    pieces.append(ctx.resolve(op.op2, op))
    expr: php.Expr = pieces[0]
    for piece in pieces[1:]:
        expr = php.BinaryOp(op=".", left=expr, right=piece)
    ctx.store(op.result, expr, op)


@opcode_handler("ZEND_INCLUDE_OR_EVAL")
def handle_include(ctx: DecompileContext, op: Opcode) -> None:
    kind = INCLUDE_KINDS.get(op.extended_value or 0, "include")
    expr = php.IncludeExpr(kind=kind, operand=ctx.resolve(op.op1, op))
    if op.result.is_unused:
        ctx.emit(op.index, php.ExprStmt(expr))
    else:
        ctx.store(op.result, expr, op)


@opcode_handler("ZEND_BIND_GLOBAL")
def handle_bind_global(ctx: DecompileContext, op: Opcode) -> None:
    ctx.emit(op.index, php.GlobalStmt(names=[ctx.cv_name(op.op1)]))


@opcode_handler("ZEND_BIND_STATIC")
def handle_bind_static(ctx: DecompileContext, op: Opcode) -> None:
    name = ctx.cv_name(op.op1)
    # Inside a closure, by-value `use ($x)` lexicals are also bound with
    # BIND_STATIC (they share the static_variables table). Those are rendered
    # in the closure's `use (...)` clause, not as `static $x;`.
    if name in ctx.lexical_names:
        return
    default = None
    statics = ctx.op_array.static_variables or {}
    if name in statics:
        from ..context import literal_to_expr

        default = literal_to_expr(statics[name])
    ctx.emit(op.index, php.StaticVarStmt(name=name, default=default))


@opcode_handler("ZEND_BIND_LEXICAL")
def handle_bind_lexical(ctx: DecompileContext, op: Opcode) -> None:
    # `use (...)` bindings are emitted in the parent right after the
    # DECLARE_LAMBDA. handle_lambda already consumed them by look-ahead, so
    # this is a no-op here (and must NOT consume the closure temp in op1, which
    # the following SEND_VAL still needs).
    return None


@opcode_handler("ZEND_TYPE_CHECK")
def handle_type_check(ctx: DecompileContext, op: Opcode) -> None:
    operand = ctx.resolve(op.op1, op)
    mask = (op.extended_value or 0) & 0x3FE
    # Single-bool masks come from `=== false` / `=== true` comparisons.
    if mask == 1 << 2:
        ctx.store(op.result, php.BinaryOp(op="===", left=operand, right=php.Literal(False)), op)
        return
    if mask == 1 << 3:
        ctx.store(op.result, php.BinaryOp(op="===", left=operand, right=php.Literal(True)), op)
        return
    # The whole type universe (0x3FE) minus one bit is the strict negation
    # `!== null/false/true` — PHP lowers e.g. `$x !== false` to a TYPE_CHECK
    # that matches every type except IS_FALSE.
    NEQ = {0x3FE & ~(1 << 1): None, 0x3FE & ~(1 << 2): False, 0x3FE & ~(1 << 3): True}
    if mask in NEQ:
        ctx.store(op.result, php.BinaryOp(op="!==", left=operand, right=php.Literal(NEQ[mask])), op)
        return
    func = TYPE_CHECK_FUNCS.get(mask)
    if func:
        ctx.store(op.result, php.FuncCall(name=func, args=[operand]), op)
        return
    ctx.warn(f"op {op.index}: TYPE_CHECK with unmapped mask {op.extended_value}")
    ctx.store(
        op.result,
        php.BinaryOp(op="!==", left=php.FuncCall(name="gettype", args=[operand]),
                     right=php.Literal("")),
        op,
    )


@opcode_handler("ZEND_DEFINED")
def handle_defined(ctx: DecompileContext, op: Opcode) -> None:
    name = op.op1.const_value()
    ctx.store(
        op.result,
        php.FuncCall(name="defined", args=[php.Literal(name if isinstance(name, str) else "?")]),
        op,
    )


@opcode_handler("ZEND_DECLARE_CLASS", "ZEND_DECLARE_CLASS_DELAYED",
                "ZEND_DECLARE_INHERITED_CLASS_DELAYED",
                "ZEND_DECLARE_CONST", "ZEND_DECLARE_ANON_CLASS")
def handle_declare(ctx: DecompileContext, op: Opcode) -> None:
    # Declarations are reconstructed from function/class tables, not opcodes.
    if not op.result.is_unused and op.result.temp_key is not None:
        name = op.op1.const_value() if op.op1.is_const else None
        ctx.store(op.result, php.ConstFetch(name=name if isinstance(name, str) else "?"), op)


@opcode_handler("ZEND_DECLARE_FUNCTION")
def handle_declare_function(ctx: DecompileContext, op: Opcode) -> None:
    oa = _find_declared_function(ctx, op)
    if oa is None:
        ctx.warn(f"op {op.index}: function declaration for {op.op1.const_value()} not found in dump")
        return
    from ..program import decompile_function  # local import: avoids cycle

    decl, sub_ctx = decompile_function(oa, ctx.program)
    if oa.function_name:
        decl.name = oa.function_name
    ctx.consumed_closures.add(oa.id)
    ctx.consumed_closures |= sub_ctx.consumed_closures
    ctx.emit(op.index, decl)


def _find_declared_function(ctx: DecompileContext, op: Opcode):
    if ctx.program is None:
        return None
    name = op.op1.const_value()
    name_str = str(name).lower() if name is not None else None

    candidates = [
        oa for oa in ctx.program.op_arrays.values()
        if oa.id not in ctx.consumed_closures and oa.id != ctx.op_array.id
    ]

    # 1. Match by lowercased function_name, table_key, or hex id
    if name_str:
        for oa in candidates:
            oa_fn = (oa.function_name or "").lower()
            table_key = str(oa.meta.get("function_table_key") or "").lower()
            if oa_fn == name_str or table_key == name_str:
                return oa
            if oa.id.startswith(f"function:{name_str.encode().hex()}"):
                return oa

    # 2. Match by index in op2
    idx = op.op2.constant if op.op2.constant is not None else op.op2.num
    if idx is not None and 0 <= idx < len(candidates):
        return candidates[idx]

    return None


@opcode_handler("ZEND_DECLARE_LAMBDA_FUNCTION")
def handle_lambda(ctx: DecompileContext, op: Opcode) -> None:
    closure = _find_closure(ctx, op)
    use_names = _collect_lexical_uses(ctx, op)
    if closure is None:
        ctx.warn(f"op {op.index}: closure body not found in dump")
        use_clause = f" use ({', '.join('$' + n for n in use_names)})" if use_names else ""
        ctx.store(
            op.result,
            php.RawExpr(f"function (){use_clause} {{ /* closure body unavailable */ }}"),
            op,
        )
        return
    from ..program import decompile_closure_expr  # local import: avoids cycle

    ctx.consumed_closures.add(closure.id)
    ctx.store(
        op.result,
        decompile_closure_expr(closure, ctx.program, use_names, parent_consumed=ctx.consumed_closures),
        op,
    )


def _collect_lexical_uses(ctx: DecompileContext, op: Opcode) -> list[str]:
    """Closure `use (...)` variables: the BIND_LEXICAL opcodes that follow the
    DECLARE_LAMBDA and target its result temp, in source order."""
    result_key = op.result.temp_key
    names: list[str] = []
    index = op.index + 1
    while index < len(ctx.ops):
        nxt = ctx.ops[index]
        if nxt.name != "ZEND_BIND_LEXICAL":
            break
        if result_key is not None and nxt.op1.temp_key not in (None, result_key):
            break
        if nxt.op2.is_cv:
            names.append(ctx.cv_name(nxt.op2))
        index += 1
    return names


def _find_closure(ctx: DecompileContext, op: Opcode):
    if ctx.program is None:
        return None
    candidates = [oa for oa in ctx.program.op_arrays.values() if oa.kind == "closure"]
    for oa in candidates:
        if oa.meta.get("opcode_index") == op.index and oa.meta.get("parent") in (None, ctx.op_array.id):
            return oa
    if op.op1.constant is not None:
        for oa in candidates:
            if oa.meta.get("literal_index") == op.op1.constant:
                return oa
    unconsumed = [
        oa for oa in candidates
        if oa.id not in ctx.consumed_closures and oa.id != ctx.op_array.id
    ]
    parent_matching = [oa for oa in unconsumed if oa.meta.get("parent") == ctx.op_array.id]
    if parent_matching:
        return parent_matching[0]
    return unconsumed[0] if unconsumed else None


@opcode_handler("ZEND_STRLEN_FAST", "ZEND_COPY_TMP")
def handle_copy_tmp(ctx: DecompileContext, op: Opcode) -> None:
    ctx.store(op.result, ctx.resolve(op.op1, op), op)


@opcode_handler("ZEND_MAKE_REF")
def handle_make_ref(ctx: DecompileContext, op: Opcode) -> None:
    ctx.store(op.result, ctx.resolve(op.op1, op), op)


@opcode_handler("ZEND_GET_CLASS")
def handle_get_class(ctx: DecompileContext, op: Opcode) -> None:
    args = [] if op.op1.is_unused else [ctx.resolve(op.op1, op)]
    ctx.store(op.result, php.FuncCall(name="get_class", args=args), op)


@opcode_handler("ZEND_GET_TYPE")
def handle_get_type(ctx: DecompileContext, op: Opcode) -> None:
    ctx.store(op.result, php.FuncCall(name="gettype", args=[ctx.resolve(op.op1, op)]), op)
