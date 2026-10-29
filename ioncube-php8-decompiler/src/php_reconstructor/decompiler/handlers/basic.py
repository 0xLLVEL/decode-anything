"""Handlers for assignments, arithmetic, comparisons and unary operators."""

from __future__ import annotations

from ... import ast as php
from ...decompiler.context import DecompileContext, has_side_effects
from ...opcode import Opcode
from ...opcode.constants import ASSIGN_OP_BINOPS, BINARY_OPS, CAST_TYPES
from . import opcode_handler


def _emit_assign(ctx: DecompileContext, op: Opcode, assign: php.Assign) -> None:
    ctx.emit(op.index, php.ExprStmt(assign))
    if not op.result.is_unused:
        # Chained assignment ($a = $b = ...): later consumers read the target.
        ctx.store(op.result, _copy_target(assign.target), op)


def _copy_target(target: php.Expr) -> php.Expr:
    if isinstance(target, php.Variable):
        return php.Variable(target.name)
    return target


@opcode_handler("ZEND_ASSIGN")
def handle_assign(ctx: DecompileContext, op: Opcode) -> None:
    target = ctx.resolve(op.op1, op)
    value = ctx.resolve(op.op2, op)
    _emit_assign(ctx, op, php.Assign(target=target, value=value))


@opcode_handler("ZEND_ASSIGN_REF")
def handle_assign_ref(ctx: DecompileContext, op: Opcode) -> None:
    value = ctx.resolve(op.op2, op)
    target = ctx.resolve(op.op1, op)
    _emit_assign(ctx, op, php.Assign(target=target, value=value, by_ref=True))


@opcode_handler("ZEND_ASSIGN_OP")
def handle_assign_op(ctx: DecompileContext, op: Opcode) -> None:
    operator = ASSIGN_OP_BINOPS.get(op.extended_value or 0)
    value = ctx.resolve(op.op2, op)
    target = ctx.resolve(op.op1, op)
    if operator is None:
        ctx.warn(f"op {op.index}: unknown ASSIGN_OP ext={op.extended_value}")
        operator = "+"
    _emit_assign(ctx, op, php.Assign(target=target, value=value, op=operator))


@opcode_handler("ZEND_ASSIGN_DIM")
def handle_assign_dim(ctx: DecompileContext, op: Opcode) -> int:
    index = None if op.op2.is_unused else ctx.resolve(op.op2, op)
    container = ctx.resolve(op.op1, op)
    value, consumed = _op_data_value(ctx, op)
    target = php.DimFetch(target=container, index=index)
    _emit_assign(ctx, op, php.Assign(target=target, value=value))
    return consumed


@opcode_handler("ZEND_ASSIGN_DIM_OP")
def handle_assign_dim_op(ctx: DecompileContext, op: Opcode) -> int:
    operator = ASSIGN_OP_BINOPS.get(op.extended_value or 0, "+")
    index = None if op.op2.is_unused else ctx.resolve(op.op2, op)
    container = ctx.resolve(op.op1, op)
    value, consumed = _op_data_value(ctx, op)
    target = php.DimFetch(target=container, index=index)
    _emit_assign(ctx, op, php.Assign(target=target, value=value, op=operator))
    return consumed


@opcode_handler("ZEND_ASSIGN_OBJ")
def handle_assign_obj(ctx: DecompileContext, op: Opcode) -> int:
    prop = _prop_name(ctx, op)
    obj = ctx.this_or(op.op1, op)
    value, consumed = _op_data_value(ctx, op)
    target = php.PropertyFetch(target=obj, name=prop)
    _emit_assign(ctx, op, php.Assign(target=target, value=value))
    return consumed


@opcode_handler("ZEND_ASSIGN_OBJ_OP")
def handle_assign_obj_op(ctx: DecompileContext, op: Opcode) -> int:
    operator = ASSIGN_OP_BINOPS.get(op.extended_value or 0, "+")
    prop = _prop_name(ctx, op)
    obj = ctx.this_or(op.op1, op)
    value, consumed = _op_data_value(ctx, op)
    target = php.PropertyFetch(target=obj, name=prop)
    _emit_assign(ctx, op, php.Assign(target=target, value=value, op=operator))
    return consumed


def _prop_name(ctx: DecompileContext, op: Opcode) -> object:
    if op.op2.is_const:
        name = op.op2.const_value()
        if isinstance(name, str):
            return name
    return ctx.resolve(op.op2, op)


def _op_data_value(ctx: DecompileContext, op: Opcode) -> tuple[php.Expr, int]:
    """ASSIGN_DIM/OBJ take their value from the following ZEND_OP_DATA."""
    next_index = op.index + 1
    if next_index < len(ctx.ops) and ctx.ops[next_index].name == "ZEND_OP_DATA":
        return ctx.resolve(ctx.ops[next_index].op1, op), 2
    ctx.warn(f"op {op.index}: {op.name} without trailing ZEND_OP_DATA")
    return php.Literal(None), 1


def handle_binary(ctx: DecompileContext, op: Opcode) -> None:
    operator = BINARY_OPS[op.name]
    right = ctx.resolve(op.op2, op)
    left = ctx.resolve(op.op1, op)
    ctx.store(op.result, php.BinaryOp(op=operator, left=left, right=right), op)


for _name in BINARY_OPS:
    opcode_handler(_name)(handle_binary)


@opcode_handler("ZEND_BOOL")
def handle_bool(ctx: DecompileContext, op: Opcode) -> None:
    ctx.store(op.result, php.Cast(type="bool", operand=ctx.resolve(op.op1, op)), op)


@opcode_handler("ZEND_BOOL_NOT")
def handle_bool_not(ctx: DecompileContext, op: Opcode) -> None:
    ctx.store(op.result, php.UnaryOp(op="!", operand=ctx.resolve(op.op1, op)), op)


@opcode_handler("ZEND_BW_NOT")
def handle_bw_not(ctx: DecompileContext, op: Opcode) -> None:
    ctx.store(op.result, php.UnaryOp(op="~", operand=ctx.resolve(op.op1, op)), op)


@opcode_handler("ZEND_CAST")
def handle_cast(ctx: DecompileContext, op: Opcode) -> None:
    cast_type = CAST_TYPES.get(op.extended_value or 0)
    operand = ctx.resolve(op.op1, op)
    if cast_type is None:
        ctx.warn(f"op {op.index}: unknown CAST type {op.extended_value}")
        ctx.store(op.result, operand, op)
        return
    ctx.store(op.result, php.Cast(type=cast_type, operand=operand), op)


@opcode_handler("ZEND_QM_ASSIGN")
def handle_qm_assign(ctx: DecompileContext, op: Opcode) -> None:
    ctx.store(op.result, ctx.resolve(op.op1, op), op)


def _inc_dec(ctx: DecompileContext, op: Opcode, operator: str, prefix: bool) -> None:
    target = ctx.resolve(op.op1, op)
    expr = php.IncDec(target=target, op=operator, is_prefix=prefix)
    if op.result.is_unused:
        ctx.emit(op.index, php.ExprStmt(expr))
    else:
        ctx.store(op.result, expr, op)


@opcode_handler("ZEND_PRE_INC")
def handle_pre_inc(ctx: DecompileContext, op: Opcode) -> None:
    _inc_dec(ctx, op, "++", True)


@opcode_handler("ZEND_PRE_DEC")
def handle_pre_dec(ctx: DecompileContext, op: Opcode) -> None:
    _inc_dec(ctx, op, "--", True)


@opcode_handler("ZEND_POST_INC")
def handle_post_inc(ctx: DecompileContext, op: Opcode) -> None:
    _inc_dec(ctx, op, "++", False)


@opcode_handler("ZEND_POST_DEC")
def handle_post_dec(ctx: DecompileContext, op: Opcode) -> None:
    _inc_dec(ctx, op, "--", False)


@opcode_handler("ZEND_FREE", "ZEND_FE_FREE")
def handle_free(ctx: DecompileContext, op: Opcode) -> None:
    # A freed-without-use temp is a discarded expression statement
    # (e.g. a call whose result nobody reads after a structured region).
    key = op.op1.temp_key
    if key is not None and key in ctx.temps:
        expr = ctx.temps.pop(key)
        if has_side_effects(expr):
            ctx.emit(op.index, php.ExprStmt(expr))


@opcode_handler("ZEND_NOP", "ZEND_EXT_NOP", "ZEND_EXT_STMT", "ZEND_EXT_FCALL_BEGIN",
                "ZEND_EXT_FCALL_END", "ZEND_SEPARATE", "ZEND_OP_DATA")
def handle_nop(ctx: DecompileContext, op: Opcode) -> None:
    # ZEND_OP_DATA reached directly means its owner did not consume it.
    if op.name == "ZEND_OP_DATA":
        ctx.warn(f"op {op.index}: orphan ZEND_OP_DATA")


@opcode_handler("ZEND_VERIFY_RETURN_TYPE", "ZEND_VERIFY_NEVER_TYPE")
def handle_verify_return_type(ctx: DecompileContext, op: Opcode) -> None:
    # Engine-inserted return-type check: transparent at the source level. The
    # checked value flows straight through, so pass op1 to the result temp when
    # there is one and emit nothing.
    if not op.op1.is_unused and not op.result.is_unused:
        ctx.store(op.result, ctx.resolve(op.op1, op), op)


@opcode_handler("ZEND_RECV")
def handle_recv(ctx: DecompileContext, op: Opcode) -> None:
    # Parameter binding -- declaration data, no statement.
    return None


@opcode_handler("ZEND_RECV_INIT")
def handle_recv_init(ctx: DecompileContext, op: Opcode) -> None:
    # op1.num carries the 1-based argument number; RECV opcodes are emitted
    # one per argument in order, so the opcode index is the fallback.
    arg_num = op.op1.num if op.op1.num else op.index + 1
    ctx.param_defaults[int(arg_num)] = ctx.resolve(op.op2, op)


@opcode_handler("ZEND_RECV_VARIADIC")
def handle_recv_variadic(ctx: DecompileContext, op: Opcode) -> None:
    return None


@opcode_handler("ZEND_MATCH")
def handle_match(ctx: DecompileContext, op: Opcode) -> int | None:
    subject = ctx.resolve(op.op1, op)
    jump_table = op.op2.const_value()
    if not isinstance(jump_table, dict):
        ctx.warn(f"op {op.index}: ZEND_MATCH jump table is not a dict")
        return None

    default_off = op.extended_value

    from typing import Any
    grouped: dict[int, list[Any] | None] = {}
    for k, off in jump_table.items():
        grouped.setdefault(off, []).append(k)
    if default_off is not None:
        grouped[default_off] = None

    sorted_offsets = sorted(grouped.keys())
    if not sorted_offsets:
        return None

    bytes_per_op = sorted_offsets[0] if sorted_offsets[0] > 0 else 28

    arms: list[php.MatchArm] = []
    res_key = None
    end_target = None

    from . import get_handler
    from ..context import literal_to_expr

    op_count = len(ctx.ops)
    last_index = op_count - 1

    for idx, off in enumerate(sorted_offsets):
        cond_keys = grouped[off]
        start = op.index + off // bytes_per_op
        if start > last_index:
            ctx.warn(
                f"op {op.index}: ZEND_MATCH arm offset {off} outside op array; "
                "using the final opcode"
            )
            start = last_index
        if idx + 1 < len(sorted_offsets):
            next_off = sorted_offsets[idx + 1]
            end = op.index + next_off // bytes_per_op - 1
        else:
            end = last_index
            for j in range(start, op_count):
                if ctx.ops[j].name == "ZEND_JMP":
                    end = j
                    break
        end = max(start, min(end, last_index))

        for j in range(start, end):
            sub_op = ctx.ops[j]
            h = get_handler(sub_op.name)
            if h is not None:
                h(ctx, sub_op)
            if sub_op.name == "ZEND_QM_ASSIGN" and sub_op.result.temp_key is not None:
                res_key = sub_op.result.temp_key

        jmp_op = ctx.ops[end]
        if jmp_op.name == "ZEND_JMP":
            target = jmp_op.jump_targets[0] if jmp_op.jump_targets else (
                jmp_op.op1.constant if jmp_op.op1.constant is not None else jmp_op.op1.num
            )
            if target is not None:
                end_target = target

        arm_val = ctx.temps.pop(res_key, None) if res_key is not None else None
        if arm_val is None:
            arm_val = php.Literal(None)
        conds = [literal_to_expr(k) for k in cond_keys] if cond_keys is not None else None
        arms.append(php.MatchArm(conds=conds, body=arm_val))

    match_expr = php.MatchExpr(subject=subject, arms=arms)
    if res_key is not None:
        ctx.temps[res_key] = match_expr
    if not op.result.is_unused and op.result.temp_key is not None:
        ctx.temps[op.result.temp_key] = match_expr

    if end_target is not None and end_target > op.index:
        return end_target - op.index
    return max(1, end - op.index)
