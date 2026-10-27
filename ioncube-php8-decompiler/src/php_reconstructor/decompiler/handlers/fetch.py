"""Handlers for variable / dimension / property / constant fetches and isset."""

from __future__ import annotations

from ... import ast as php
from ...decompiler.context import DecompileContext
from ...opcode import Opcode
from ...opcode.constants import ZEND_ISEMPTY
from . import opcode_handler


@opcode_handler("ZEND_FETCH_R", "ZEND_FETCH_W", "ZEND_FETCH_RW", "ZEND_FETCH_IS",
                "ZEND_FETCH_FUNC_ARG", "ZEND_FETCH_UNSET")
def handle_fetch_var(ctx: DecompileContext, op: Opcode) -> None:
    # Fetch a variable by name (superglobals, variable-variables).
    if op.op1.is_const:
        name = op.op1.const_value()
        if isinstance(name, str):
            expr: php.Expr = php.Variable(name)
        elif name is None:
            expr = php.RawExpr("${None}")
        elif isinstance(name, (bytes, bytearray)):
            try:
                expr = php.Variable(name.decode("utf-8"))
            except Exception:
                expr = php.Variable(repr(name))
        else:
            expr = php.Variable(str(name))
    else:
        inner = ctx.resolve(op.op1, op)
        expr = php.Variable(inner)
    ctx.store(op.result, expr, op)


@opcode_handler("ZEND_FETCH_THIS")
def handle_fetch_this(ctx: DecompileContext, op: Opcode) -> None:
    ctx.store(op.result, php.Variable("this"), op)



@opcode_handler("ZEND_FETCH_DIM_R", "ZEND_FETCH_DIM_W", "ZEND_FETCH_DIM_RW",
                "ZEND_FETCH_DIM_IS", "ZEND_FETCH_DIM_FUNC_ARG", "ZEND_FETCH_DIM_UNSET",
                "ZEND_FETCH_LIST_R")
def handle_fetch_dim(ctx: DecompileContext, op: Opcode) -> None:
    index = None if op.op2.is_unused else ctx.resolve(op.op2, op)
    container = ctx.resolve(op.op1, op)
    ctx.store(op.result, php.DimFetch(target=container, index=index), op)


@opcode_handler("ZEND_FETCH_OBJ_R", "ZEND_FETCH_OBJ_W", "ZEND_FETCH_OBJ_RW",
                "ZEND_FETCH_OBJ_IS", "ZEND_FETCH_OBJ_FUNC_ARG", "ZEND_FETCH_OBJ_UNSET")
def handle_fetch_obj(ctx: DecompileContext, op: Opcode) -> None:
    name: object
    if op.op2.is_const:
        value = op.op2.const_value()
        name = value if isinstance(value, str) else ctx.resolve(op.op2, op)
    else:
        name = ctx.resolve(op.op2, op)
    target = ctx.this_or(op.op1, op)
    ctx.store(op.result, php.PropertyFetch(target=target, name=name), op)


@opcode_handler("ZEND_FETCH_STATIC_PROP_R", "ZEND_FETCH_STATIC_PROP_W",
                "ZEND_FETCH_STATIC_PROP_RW", "ZEND_FETCH_STATIC_PROP_IS",
                "ZEND_FETCH_STATIC_PROP_FUNC_ARG", "ZEND_FETCH_STATIC_PROP_UNSET")
def handle_fetch_static_prop(ctx: DecompileContext, op: Opcode) -> None:
    prop = op.op1.const_value() if op.op1.is_const else None
    cls = op.op2.const_value() if op.op2.is_const else None
    ctx.store(
        op.result,
        php.StaticPropertyFetch(
            class_name=cls if isinstance(cls, str) else "static",
            name=prop if isinstance(prop, str) else "?",
        ),
        op,
    )


@opcode_handler("ZEND_FETCH_CONSTANT")
def handle_fetch_constant(ctx: DecompileContext, op: Opcode) -> None:
    name = op.op2.const_value()
    if isinstance(name, str):
        ctx.store(op.result, php.ConstFetch(name=name), op)
    else:
        ctx.warn(f"op {op.index}: FETCH_CONSTANT with non-string name")
        ctx.store(op.result, php.ConstFetch(name="UNKNOWN_CONSTANT"), op)


@opcode_handler("ZEND_FETCH_CLASS_CONSTANT")
def handle_fetch_class_constant(ctx: DecompileContext, op: Opcode) -> None:
    cls = op.op1.const_value() if op.op1.is_const else None
    if cls is None and not op.op1.is_unused:
        resolved = ctx.resolve(op.op1, op)
        cls = resolved if not isinstance(resolved, php.Literal) else None
    name = op.op2.const_value()
    ctx.store(
        op.result,
        php.ClassConstFetch(
            class_name=cls if isinstance(cls, str) else "static",
            const_name=name if isinstance(name, str) else "?",
        ),
        op,
    )


@opcode_handler("ZEND_FETCH_CLASS")
def handle_fetch_class(ctx: DecompileContext, op: Opcode) -> None:
    # Produces a class reference temp consumed by INSTANCEOF / NEW / etc.
    name = op.op2.const_value() if op.op2.is_const else None
    if isinstance(name, str):
        ctx.store(op.result, php.ConstFetch(name=name), op)
    elif not op.op2.is_unused:
        ctx.store(op.result, ctx.resolve(op.op2, op), op)
    else:
        ctx.store(op.result, php.ConstFetch(name="static"), op)


@opcode_handler("ZEND_INSTANCEOF")
def handle_instanceof(ctx: DecompileContext, op: Opcode) -> None:
    if op.op2.is_const:
        cls = op.op2.const_value()
        class_name: object = cls if isinstance(cls, str) else "?"
    else:
        resolved = ctx.resolve(op.op2, op)
        class_name = resolved.name if isinstance(resolved, php.ConstFetch) else resolved
    ctx.store(op.result, php.InstanceOf(operand=ctx.resolve(op.op1, op), class_name=class_name), op)


def _isset_or_empty(ctx: DecompileContext, op: Opcode, target: php.Expr) -> None:
    if (op.extended_value or 0) & ZEND_ISEMPTY:
        ctx.store(op.result, php.EmptyExpr(operand=target), op)
    else:
        ctx.store(op.result, php.Isset(exprs=[target]), op)


@opcode_handler("ZEND_ISSET_ISEMPTY_CV")
def handle_isset_cv(ctx: DecompileContext, op: Opcode) -> None:
    _isset_or_empty(ctx, op, php.Variable(ctx.cv_name(op.op1)))


@opcode_handler("ZEND_ISSET_ISEMPTY_VAR")
def handle_isset_var(ctx: DecompileContext, op: Opcode) -> None:
    if op.op1.is_const:
        name = op.op1.const_value()
        target = php.Variable(name) if isinstance(name, str) else php.Variable(str(name))
    else:
        target = php.Variable(ctx.resolve(op.op1, op))
    _isset_or_empty(ctx, op, target)


@opcode_handler("ZEND_ISSET_ISEMPTY_DIM_OBJ")
def handle_isset_dim(ctx: DecompileContext, op: Opcode) -> None:
    index = ctx.resolve(op.op2, op)
    container = ctx.resolve(op.op1, op)
    _isset_or_empty(ctx, op, php.DimFetch(target=container, index=index))


@opcode_handler("ZEND_ISSET_ISEMPTY_PROP_OBJ")
def handle_isset_prop(ctx: DecompileContext, op: Opcode) -> None:
    name = op.op2.const_value() if op.op2.is_const else ctx.resolve(op.op2, op)
    target = ctx.this_or(op.op1, op)
    _isset_or_empty(ctx, op, php.PropertyFetch(target=target, name=name))


@opcode_handler("ZEND_UNSET_CV")
def handle_unset_cv(ctx: DecompileContext, op: Opcode) -> None:
    ctx.emit(op.index, php.UnsetStmt(exprs=[php.Variable(ctx.cv_name(op.op1))]))


@opcode_handler("ZEND_UNSET_DIM")
def handle_unset_dim(ctx: DecompileContext, op: Opcode) -> None:
    index = ctx.resolve(op.op2, op)
    container = ctx.resolve(op.op1, op)
    ctx.emit(op.index, php.UnsetStmt(exprs=[php.DimFetch(target=container, index=index)]))


@opcode_handler("ZEND_UNSET_OBJ")
def handle_unset_obj(ctx: DecompileContext, op: Opcode) -> None:
    name = op.op2.const_value() if op.op2.is_const else ctx.resolve(op.op2, op)
    target = ctx.this_or(op.op1, op)
    ctx.emit(op.index, php.UnsetStmt(exprs=[php.PropertyFetch(target=target, name=name)]))
