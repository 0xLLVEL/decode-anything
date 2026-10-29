"""Program-level decompilation: op_arrays -> PhpFile AST (functions,
methods, classes, top-level code)."""

from __future__ import annotations

from .. import ast as php
from ..opcode import ArgInfo, OpArray, PhpClassInfo, Program
import re

from ..utils import is_valid_php_identifier

_TYPE_ATOM_RE = r"\\?[A-Za-z_][A-Za-z0-9_]*(\\[A-Za-z_][A-Za-z0-9_]*)*"
_TYPE_GROUP_RE = rf"{_TYPE_ATOM_RE}(?:&{_TYPE_ATOM_RE})*"
_TYPE_PART_RE = rf"(?:\({_TYPE_GROUP_RE}\)|{_TYPE_GROUP_RE})"
_TYPE_NAME_RE = re.compile(rf"^\??{_TYPE_PART_RE}(\|{_TYPE_PART_RE})*$")


def _sane_type(type_name: str | None) -> str | None:
    """Drop pseudo-types like ``type(128)`` that the dump emits for
    unknown zend type codes."""
    if type_name and _TYPE_NAME_RE.match(type_name):
        return type_name
    return None
from .context import DecompileContext, literal_to_expr
from .structurer import RangeDecompiler


def decompile_program(program: Program) -> php.PhpFile:
    php_file = php.PhpFile()

    consumed_closures: set[str] = set()
    ordered: list[tuple[int, int, php.Stmt]] = []
    sequence = 0

    main = program.main
    if main is not None:
        tagged_stmts, ctx = _decompile_op_array_tagged(main, program)
        consumed_closures |= ctx.consumed_closures
        for op_index, stmt in _strip_main_trailing_return_tagged(tagged_stmts):
            ordered.append((_stmt_source_line(main, op_index), sequence, stmt))
            sequence += 1

    for op_array in program.functions():
        if op_array.id in consumed_closures:
            continue
        decl, ctx = decompile_function(op_array, program)
        consumed_closures |= ctx.consumed_closures
        ordered.append((_op_array_source_line(op_array), sequence, decl))
        sequence += 1

    for class_id, class_info in program.classes.items():
        decl, used = decompile_class(class_info, program)
        consumed_closures |= used
        ordered.append((10**9, sequence, decl))
        sequence += 1

    php_file.statements.extend(stmt for _, _, stmt in sorted(ordered))

    # Closures never referenced by a DECLARE_LAMBDA_FUNCTION: keep them
    # visible instead of dropping decoded code.
    for op_array in program.closures():
        if op_array.id in consumed_closures:
            continue
        php_file.statements.append(
            php.CommentStmt(text=f"orphan closure from dump: {op_array.id}")
        )
        decl, ctx = decompile_function(op_array, program)
        decl.name = f"__closure_{_safe_suffix(op_array.id)}"
        consumed_closures |= ctx.consumed_closures
        php_file.statements.append(decl)

    return php_file


def decompile_function(op_array: OpArray, program: Program | None = None) -> tuple[php.FunctionDecl, DecompileContext]:
    body, ctx = _decompile_op_array(op_array, program)
    decl = php.FunctionDecl(
        name=function_name(op_array),
        params=build_params(op_array, ctx),
        body=body,
        return_type=_sane_type(op_array.return_type),
        return_nullable=op_array.return_allow_null,
        by_ref=op_array.returns_reference,
        doc_comment=op_array.doc_comment,
    )
    return decl, ctx


def decompile_method(name: str, op_array: OpArray, program: Program | None = None) -> tuple[php.MethodDecl, DecompileContext]:
    body, ctx = _decompile_op_array(op_array, program)
    flags = op_array.fn_flags_decoded
    decl = php.MethodDecl(
        name=name,
        params=build_params(op_array, ctx),
        body=body,
        visibility=op_array.visibility or "public",
        is_static=op_array.is_static,
        is_abstract=bool(flags.get("is_abstract")),
        is_final=bool(flags.get("is_final")),
        return_type=_sane_type(op_array.return_type),
        return_nullable=op_array.return_allow_null,
        by_ref=op_array.returns_reference,
        doc_comment=op_array.doc_comment,
    )
    return decl, ctx


def decompile_class(class_info: PhpClassInfo, program: Program) -> tuple[php.ClassDecl, set[str]]:
    decl = php.ClassDecl(
        name=class_info.name,
        parent=class_info.parent,
        interfaces=list(class_info.interfaces),
        is_abstract=class_info.is_abstract,
        is_final=class_info.is_final,
        is_interface=class_info.is_interface,
        doc_comment=class_info.doc_comment,
    )
    for const_name, value in class_info.constants.items():
        decl.constants.append(
            php.ClassConstDecl(name=const_name, value=literal_to_expr(value))
        )
    for prop in class_info.properties:
        decl.properties.append(
            php.PropertyDecl(
                name=prop.name,
                visibility=prop.visibility,
                is_static=prop.is_static,
                is_readonly=prop.is_readonly,
                type=prop.type_name,
                is_nullable=prop.allow_null,
                default=literal_to_expr(prop.default) if prop.has_default else None,
                doc_comment=prop.doc_comment,
            )
        )

    consumed: set[str] = set()
    for method_name, oa_id in class_info.methods.items():
        op_array = program.op_arrays.get(oa_id)
        if op_array is None:
            decl.methods.append(
                php.MethodDecl(name=method_name, body=[php.CommentStmt(text=f"missing op_array {oa_id}")])
            )
            continue
        display_name = _method_display_name(method_name, op_array)
        method, ctx = decompile_method(display_name, op_array, program)
        consumed |= ctx.consumed_closures
        decl.methods.append(method)
    return decl, consumed


def decompile_closure_expr(
    op_array: OpArray,
    program: Program | None = None,
    use_names: list[str] | None = None,
    parent_consumed: set[str] | None = None,
) -> php.ClosureExpr:
    ctx = DecompileContext(op_array, program)
    if parent_consumed is not None:
        ctx.consumed_closures = parent_consumed
    ctx.consumed_closures.add(op_array.id)
    if use_names:
        ctx.lexical_names = set(use_names)
    body = RangeDecompiler(ctx).run()
    body = _drop_trailing_bare_return(body)
    uses = use_names if use_names is not None else list(dict.fromkeys(ctx.uses))
    return php.ClosureExpr(
        params=build_params(op_array, ctx),
        uses=uses,
        body=body,
        is_static=op_array.is_static,
    )


def function_name(op_array: OpArray) -> str:
    # function_name keeps the original casing; the function-table key is
    # lowercased by the engine, so it is only a fallback.
    if is_valid_php_identifier(op_array.function_name):
        return str(op_array.function_name)
    key = op_array.meta.get("function_table_key")
    if isinstance(key, dict):
        from ..utils import unwrap_safe_value

        key = unwrap_safe_value(key)
    if is_valid_php_identifier(key):
        return str(key)
    return f"__fn_{_safe_suffix(op_array.id)}"


def build_params(op_array: OpArray, ctx: DecompileContext) -> list[php.Param]:
    """Merge arg_info, CV names and RECV_INIT defaults into parameters."""
    params: list[php.Param] = []
    count = max(
        op_array.num_args or 0,
        len(op_array.args),
        len(ctx.param_defaults),
    )
    required = op_array.required_num_args
    for position in range(count):
        info: ArgInfo | None = op_array.args[position] if position < len(op_array.args) else None
        name = None
        if info and is_valid_php_identifier(info.name):
            name = info.name
        elif position < len(op_array.vars):
            name = op_array.vars[position]
        param_type = _sane_type(info.type_name) if info else None
        param = php.Param(
            name=name or f"arg{position + 1}",
            type=param_type,
            nullable=bool(info and info.allow_null and param_type),
            by_ref=bool(info and info.pass_by_reference),
            variadic=bool(info and info.is_variadic),
            default=ctx.param_defaults.get(position + 1),
        )
        if (
            param.default is None
            and info is not None
            and info.has_default
            and required is not None
            and position >= required
        ):
            param.default = php.Literal(None)
        params.append(param)
    return params


def _decompile_op_array(op_array: OpArray, program: Program | None) -> tuple[list[php.Stmt], DecompileContext]:
    ctx = DecompileContext(op_array, program)
    stmts = RangeDecompiler(ctx).run()
    return stmts, ctx


def _decompile_op_array_tagged(
    op_array: OpArray, program: Program | None
) -> tuple[list[tuple[int, php.Stmt]], DecompileContext]:
    ctx = DecompileContext(op_array, program)
    RangeDecompiler(ctx).run()
    return list(ctx.current_sink()), ctx


def _strip_main_trailing_return(stmts: list[php.Stmt]) -> list[php.Stmt]:
    """Drop the implicit `return 1;` the compiler appends to {main}."""
    if stmts and isinstance(stmts[-1], php.ReturnStmt):
        value = stmts[-1].value
        if value is None or (isinstance(value, php.Literal) and value.value in (1, True, None)):
            return stmts[:-1]
    return stmts


def _strip_main_trailing_return_tagged(
    stmts: list[tuple[int, php.Stmt]]
) -> list[tuple[int, php.Stmt]]:
    if stmts and isinstance(stmts[-1][1], php.ReturnStmt):
        value = stmts[-1][1].value
        if value is None or (isinstance(value, php.Literal) and value.value in (1, True, None)):
            return stmts[:-1]
    return stmts


def _stmt_source_line(op_array: OpArray, op_index: int) -> int:
    if 0 <= op_index < len(op_array.opcodes):
        line = op_array.opcodes[op_index].line
        if line is not None:
            return line
    return _op_array_source_line(op_array)


def _op_array_source_line(op_array: OpArray) -> int:
    if op_array.line_start is not None and op_array.line_start > 0:
        return op_array.line_start
    for op in op_array.opcodes:
        if op.line is not None and op.line > 0:
            return op.line
    return 10**9


def _drop_trailing_bare_return(stmts: list[php.Stmt]) -> list[php.Stmt]:
    """Drop the implicit `return;` the compiler appends to a closure body."""
    if stmts and isinstance(stmts[-1], php.ReturnStmt) and stmts[-1].value is None:
        return stmts[:-1]
    return stmts


def _method_display_name(name: str, op_array: OpArray) -> str:
    # Prefer function_name (original casing) over the lowercased table keys.
    if is_valid_php_identifier(op_array.function_name):
        return str(op_array.function_name)
    meta_name = op_array.meta.get("method_name")
    if isinstance(meta_name, dict):
        from ..utils import unwrap_safe_value

        meta_name = unwrap_safe_value(meta_name)
    if is_valid_php_identifier(meta_name):
        return str(meta_name)
    if is_valid_php_identifier(name):
        return name
    return f"__method_{_safe_suffix(op_array.id)}"


def _safe_suffix(identifier: str) -> str:
    return "".join(ch if ch.isalnum() else "_" for ch in identifier)[-24:]
