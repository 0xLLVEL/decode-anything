"""Handlers for array construction opcodes."""

from __future__ import annotations

from ... import ast as php
from ...decompiler.context import DecompileContext
from ...opcode import Opcode
from . import opcode_handler


@opcode_handler("ZEND_INIT_ARRAY")
def handle_init_array(ctx: DecompileContext, op: Opcode) -> None:
    array = php.ArrayLiteral()
    if not op.op1.is_unused:
        key = None if op.op2.is_unused else ctx.resolve(op.op2, op)
        value = ctx.resolve(op.op1, op)
        by_ref = bool((op.extended_value or 0) & 1)
        array.items.append(php.ArrayItem(value=value, key=key, by_ref=by_ref))
    ctx.store(op.result, array, op)


@opcode_handler("ZEND_ADD_ARRAY_ELEMENT")
def handle_add_array_element(ctx: DecompileContext, op: Opcode) -> None:
    # Appends into the same temp slot that INIT_ARRAY produced.
    array = ctx.peek(op.result)
    if not isinstance(array, php.ArrayLiteral):
        ctx.warn(f"op {op.index}: ADD_ARRAY_ELEMENT without live array temp")
        array = php.ArrayLiteral()
        ctx.store(op.result, array, op)
    key = None if op.op2.is_unused else ctx.resolve(op.op2, op)
    value = ctx.resolve(op.op1, op)
    by_ref = bool((op.extended_value or 0) & 1)
    array.items.append(php.ArrayItem(value=value, key=key, by_ref=by_ref))


@opcode_handler("ZEND_ADD_ARRAY_UNPACK")
def handle_add_array_unpack(ctx: DecompileContext, op: Opcode) -> None:
    array = ctx.peek(op.result)
    if not isinstance(array, php.ArrayLiteral):
        array = php.ArrayLiteral()
        ctx.store(op.result, array, op)
    value = php.UnaryOp(op="...", operand=ctx.resolve(op.op1, op))
    array.items.append(php.ArrayItem(value=value))


@opcode_handler("ZEND_IN_ARRAY")
def handle_in_array(ctx: DecompileContext, op: Opcode) -> None:
    haystack = ctx.resolve(op.op2, op)
    needle = ctx.resolve(op.op1, op)
    args = [needle, haystack]
    if op.extended_value:
        args.append(php.Literal(True))
    ctx.store(op.result, php.FuncCall(name="in_array", args=args), op)


@opcode_handler("ZEND_COUNT")
def handle_count(ctx: DecompileContext, op: Opcode) -> None:
    ctx.store(op.result, php.FuncCall(name="count", args=[ctx.resolve(op.op1, op)]), op)


@opcode_handler("ZEND_ARRAY_KEY_EXISTS")
def handle_array_key_exists(ctx: DecompileContext, op: Opcode) -> None:
    key = ctx.resolve(op.op1, op)
    array = ctx.resolve(op.op2, op)
    ctx.store(op.result, php.FuncCall(name="array_key_exists", args=[key, array]), op)


@opcode_handler("ZEND_STRLEN")
def handle_strlen(ctx: DecompileContext, op: Opcode) -> None:
    ctx.store(op.result, php.FuncCall(name="strlen", args=[ctx.resolve(op.op1, op)]), op)

