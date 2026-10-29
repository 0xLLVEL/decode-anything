"""Handlers for the call protocol: INIT_* -> SEND_* -> DO_*."""

from __future__ import annotations

from ... import ast as php
from ...decompiler.context import CallFrame, DecompileContext
from ...opcode import Opcode
from . import opcode_handler

# ZEND_INIT_STATIC_METHOD_CALL with an IS_UNUSED class operand encodes the
# relative class in the low bits of extended_value (zend_fetch_class_type).
_RELATIVE_CLASS = {1: "self", 2: "parent", 3: "static"}


def _const_str(ctx: DecompileContext, op: Opcode, operand) -> object:
    if operand.is_const:
        value = operand.const_value()
        if isinstance(value, str):
            return value
    if operand.is_unused:
        return "?"
    return ctx.resolve(operand, op)


@opcode_handler("ZEND_INIT_FCALL", "ZEND_INIT_FCALL_BY_NAME", "ZEND_INIT_NS_FCALL_BY_NAME")
def handle_init_fcall(ctx: DecompileContext, op: Opcode) -> None:
    name = op.call_name or _const_str(ctx, op, op.op2)
    ctx.call_stack.append(CallFrame(kind="func", name=name))


@opcode_handler("ZEND_INIT_DYNAMIC_CALL")
def handle_init_dynamic_call(ctx: DecompileContext, op: Opcode) -> None:
    ctx.call_stack.append(CallFrame(kind="dynamic", name=ctx.resolve(op.op2, op)))


@opcode_handler("ZEND_INIT_USER_CALL")
def handle_init_user_call(ctx: DecompileContext, op: Opcode) -> None:
    # call_user_func(_array) forwarding -- keep the callable expression.
    ctx.call_stack.append(CallFrame(kind="dynamic", name=ctx.resolve(op.op2, op)))


@opcode_handler("ZEND_INIT_METHOD_CALL")
def handle_init_method_call(ctx: DecompileContext, op: Opcode) -> None:
    target = ctx.this_or(op.op1, op)
    name = _const_str(ctx, op, op.op2)
    ctx.call_stack.append(CallFrame(kind="method", name=name, target=target))


@opcode_handler("ZEND_INIT_STATIC_METHOD_CALL")
def handle_init_static_method_call(ctx: DecompileContext, op: Opcode) -> None:
    if op.op1.is_unused:
        fetch_type = (op.extended_value or 0) & 0x0F
        if not fetch_type and op.op1.var is not None:
            fetch_type = op.op1.var & 0x0F
        class_name: object = _RELATIVE_CLASS.get(fetch_type, "self")
    else:
        class_name = _const_str(ctx, op, op.op1)
    name = _const_str(ctx, op, op.op2)
    if name == "?":
        name = "__construct"
    ctx.call_stack.append(CallFrame(kind="static", name=name, class_name=class_name))


@opcode_handler("ZEND_NEW")
def handle_new(ctx: DecompileContext, op: Opcode) -> None:
    if op.op1.is_unused:
        fetch_type = (op.extended_value or 0) & 0x0F
        if not fetch_type and op.op1.var is not None:
            fetch_type = op.op1.var & 0x0F
        class_name: object = _RELATIVE_CLASS.get(fetch_type, "self")
    else:
        class_name = _const_str(ctx, op, op.op1)
    ctx.call_stack.append(
        CallFrame(kind="new", class_name=class_name, new_result_key=op.result.temp_key)
    )


@opcode_handler(
    "ZEND_SEND_VAL", "ZEND_SEND_VAL_EX", "ZEND_SEND_VAR", "ZEND_SEND_VAR_EX",
    "ZEND_SEND_VAR_NO_REF", "ZEND_SEND_VAR_NO_REF_EX", "ZEND_SEND_REF",
    "ZEND_SEND_FUNC_ARG", "ZEND_SEND_USER",
)
def handle_send(ctx: DecompileContext, op: Opcode) -> None:
    value = ctx.resolve(op.op1, op)
    if ctx.call_stack:
        ctx.call_stack[-1].args.append(value)
    else:
        ctx.warn(f"op {op.index}: {op.name} outside any call frame")


@opcode_handler("ZEND_SEND_ARRAY", "ZEND_SEND_UNPACK")
def handle_send_unpack(ctx: DecompileContext, op: Opcode) -> None:
    value = php.UnaryOp(op="...", operand=ctx.resolve(op.op1, op))
    if ctx.call_stack:
        ctx.call_stack[-1].args.append(value)
    else:
        ctx.warn(f"op {op.index}: {op.name} outside any call frame")


@opcode_handler("ZEND_CHECK_FUNC_ARG", "ZEND_CHECK_UNDEF_ARGS", "ZEND_FUNC_GET_ARGS")
def handle_check_func_arg(ctx: DecompileContext, op: Opcode) -> None:
    return None


@opcode_handler("ZEND_DO_FCALL", "ZEND_DO_FCALL_BY_NAME", "ZEND_DO_ICALL", "ZEND_DO_UCALL")
def handle_do_fcall(ctx: DecompileContext, op: Opcode) -> None:
    if not ctx.call_stack:
        ctx.warn(f"op {op.index}: {op.name} without INIT frame")
        return
    frame = ctx.call_stack.pop()
    expr = _build_call(frame)

    if frame.kind == "new":
        if frame.new_result_key is not None:
            ctx.temps[frame.new_result_key] = expr
        else:
            ctx.emit(op.index, php.ExprStmt(expr))
        return

    if op.result.is_unused:
        ctx.emit(op.index, php.ExprStmt(expr))
    else:
        ctx.store(op.result, expr, op)


@opcode_handler("ZEND_CALLABLE_CONVERT")
def handle_callable_convert(ctx: DecompileContext, op: Opcode) -> None:
    if not ctx.call_stack:
        ctx.warn(f"op {op.index}: {op.name} without INIT frame")
        return
    frame = ctx.call_stack.pop()
    frame.args = [php.RawExpr("...")]
    expr = _build_call(frame)
    if op.result.is_unused:
        ctx.emit(op.index, php.ExprStmt(expr))
    else:
        ctx.store(op.result, expr, op)


def _build_call(frame: CallFrame) -> php.Expr:
    if frame.kind == "new":
        return php.New(class_name=frame.class_name, args=frame.args)
    if frame.kind == "method":
        return php.MethodCall(
            target=frame.target or php.Variable("this"), name=frame.name, args=frame.args
        )
    if frame.kind == "static":
        return php.StaticCall(class_name=frame.class_name, name=frame.name, args=frame.args)
    return php.FuncCall(name=frame.name, args=frame.args)
