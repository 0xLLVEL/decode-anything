"""Emit clean, deterministic PHP source from the AST."""

from __future__ import annotations

from .. import ast as php
from ..utils import is_valid_php_identifier
from ..utils.php_values import PhpBytes, try_decode_ioncube_array

INDENT = "    "

# Operator precedence (higher binds tighter), PHP 8 rules.
_PREC = {
    "or": 1, "xor": 1, "and": 1,
    "=": 3,
    "?:": 4,
    "??": 5,
    "||": 6,
    "&&": 7,
    "|": 8,
    "^": 9,
    "&": 10,
    "==": 11, "!=": 11, "===": 11, "!==": 11, "<=>": 11,
    "<": 12, "<=": 12, ">": 12, ">=": 12,
    ".": 13,
    "<<": 14, ">>": 14,
    "+": 15, "-": 15,
    "*": 16, "/": 16, "%": 16,
    "!": 17,
    "instanceof": 18,
    "unary": 19,
    "**": 20,
    "postfix": 21,
    "atom": 100,
}

_ASSOCIATIVE = {".", "+", "*", "&&", "||", "&", "|", "^", "and", "or"}


class PhpEmitter:
    def __init__(self) -> None:
        self._depth = 0  # statement indentation depth, used by multiline arrays

    def emit_file(self, node: php.PhpFile) -> str:
        lines: list[str] = ["<?php", ""]
        if node.header_comment:
            lines.append("/*")
            for comment_line in node.header_comment.splitlines():
                lines.append(f" * {comment_line}".rstrip())
            lines.append(" */")
            lines.append("")
        body = self._stmts(node.statements, 0)
        if body:
            lines.extend(body)
        text = "\n".join(lines)
        return text.rstrip("\n") + "\n"

    # -- statements -----------------------------------------------------------

    def _stmts(self, stmts: list[php.Stmt], depth: int) -> list[str]:
        lines: list[str] = []
        for index, stmt in enumerate(stmts):
            rendered = self._stmt(stmt, depth)
            if index > 0 and isinstance(stmt, (php.FunctionDecl, php.ClassDecl)):
                lines.append("")
            lines.extend(rendered)
        return lines

    def _stmt(self, stmt: php.Stmt, depth: int) -> list[str]:
        pad = INDENT * depth
        self._depth = depth
        if isinstance(stmt, php.ExprStmt):
            return [f"{pad}{self._expr(stmt.expr)};"]
        if isinstance(stmt, php.EchoStmt):
            args = ", ".join(self._expr(e) for e in stmt.exprs)
            return [f"{pad}echo {args};"]
        if isinstance(stmt, php.ReturnStmt):
            if stmt.value is None:
                return [f"{pad}return;"]
            return [f"{pad}return {self._expr(stmt.value)};"]
        if isinstance(stmt, php.IfStmt):
            return self._if(stmt, depth)
        if isinstance(stmt, php.WhileStmt):
            head = f"{pad}while ({self._expr(stmt.cond)}) {{"
            return [head, *self._stmts(stmt.body, depth + 1), f"{pad}}}"]
        if isinstance(stmt, php.DoWhileStmt):
            return [
                f"{pad}do {{",
                *self._stmts(stmt.body, depth + 1),
                f"{pad}}} while ({self._expr(stmt.cond)});",
            ]
        if isinstance(stmt, php.ForeachStmt):
            value = self._expr(stmt.value_var)
            if stmt.by_ref:
                value = "&" + value
            as_clause = value
            if stmt.key_var is not None:
                as_clause = f"{self._expr(stmt.key_var)} => {value}"
            head = f"{pad}foreach ({self._expr(stmt.iterable)} as {as_clause}) {{"
            return [head, *self._stmts(stmt.body, depth + 1), f"{pad}}}"]
        if isinstance(stmt, php.SwitchStmt):
            return self._switch(stmt, depth)
        if isinstance(stmt, php.BreakStmt):
            return [f"{pad}break;" if stmt.level == 1 else f"{pad}break {stmt.level};"]
        if isinstance(stmt, php.ContinueStmt):
            return [f"{pad}continue;" if stmt.level == 1 else f"{pad}continue {stmt.level};"]
        if isinstance(stmt, php.GlobalStmt):
            names = ", ".join(f"${name}" for name in stmt.names)
            return [f"{pad}global {names};"]
        if isinstance(stmt, php.StaticVarStmt):
            if stmt.default is not None:
                return [f"{pad}static ${stmt.name} = {self._expr(stmt.default)};"]
            return [f"{pad}static ${stmt.name};"]
        if isinstance(stmt, php.UnsetStmt):
            args = ", ".join(self._expr(e) for e in stmt.exprs)
            return [f"{pad}unset({args});"]
        if isinstance(stmt, php.ThrowStmt):
            return [f"{pad}throw {self._expr(stmt.expr)};"]
        if isinstance(stmt, php.TryStmt):
            lines = [f"{pad}try {{", *self._stmts(stmt.body, depth + 1)]
            for clause in stmt.catches:
                types = " | ".join(clause.class_names) or "Exception"
                var = f" ${clause.var_name}" if clause.var_name else ""
                lines.append(f"{pad}}} catch ({types}{var}) {{")
                lines.extend(self._stmts(clause.body, depth + 1))
            if stmt.finally_body is not None:
                lines.append(f"{pad}}} finally {{")
                lines.extend(self._stmts(stmt.finally_body, depth + 1))
            lines.append(f"{pad}}}")
            return lines
        if isinstance(stmt, php.CommentStmt):
            return [f"{pad}// {line}" for line in stmt.text.splitlines()] or [f"{pad}//"]
        if isinstance(stmt, php.OpcodeComment):
            detail = f" {stmt.detail}" if stmt.detail else ""
            return [f"{pad}/* [opcode {stmt.opcode_index}] {stmt.opcode_name}{detail} */"]
        if isinstance(stmt, php.GotoStmt):
            return [f"{pad}goto {stmt.label};"]
        if isinstance(stmt, php.LabelStmt):
            # Labels sit at the statement's own indent, conventionally flush-left
            # within the function; keep them at the current indent for clarity.
            return [f"{pad}{stmt.label}:"]
        if isinstance(stmt, php.FunctionDecl):
            return self._function(stmt, depth)
        if isinstance(stmt, php.ClassDecl):
            return self._class(stmt, depth)
        return [f"{pad}/* unsupported statement {type(stmt).__name__} */"]

    def _switch(self, stmt: php.SwitchStmt, depth: int) -> list[str]:
        pad = INDENT * depth
        inner = INDENT * (depth + 1)
        lines = [f"{pad}switch ({self._expr(stmt.subject)}) {{"]
        for case in stmt.cases:
            if case.test is None:
                lines.append(f"{inner}default:")
            else:
                lines.append(f"{inner}case {self._expr(case.test)}:")
            lines.extend(self._stmts(case.body, depth + 2))
        lines.append(f"{pad}}}")
        return lines

    def _if(self, stmt: php.IfStmt, depth: int) -> list[str]:
        pad = INDENT * depth
        lines = [f"{pad}if ({self._expr(stmt.cond)}) {{"]
        lines.extend(self._stmts(stmt.then, depth + 1))
        for cond, body in stmt.elifs:
            lines.append(f"{pad}}} elseif ({self._expr(cond)}) {{")
            lines.extend(self._stmts(body, depth + 1))
        if stmt.orelse:
            lines.append(f"{pad}}} else {{")
            lines.extend(self._stmts(stmt.orelse, depth + 1))
        lines.append(f"{pad}}}")
        return lines

    def _function(self, decl: php.FunctionDecl, depth: int) -> list[str]:
        pad = INDENT * depth
        lines = self._doc_comment(decl.doc_comment, pad)
        ref = "&" if decl.by_ref else ""
        signature = f"{pad}function {ref}{decl.name}({self._params(decl.params)})"
        signature += self._return_type(decl.return_type, decl.return_nullable)
        lines.append(signature + " {")
        lines.extend(self._stmts(decl.body, depth + 1))
        lines.append(f"{pad}}}")
        return lines

    def _class(self, decl: php.ClassDecl, depth: int) -> list[str]:
        pad = INDENT * depth
        lines = self._doc_comment(decl.doc_comment, pad)
        keyword = "interface" if decl.is_interface else "class"
        modifiers = ""
        if decl.is_abstract:
            modifiers = "abstract "
        elif decl.is_final:
            modifiers = "final "
        head = f"{pad}{modifiers}{keyword} {decl.name}"
        if decl.parent:
            head += f" extends {decl.parent}"
        if decl.interfaces:
            head += " implements " + ", ".join(decl.interfaces)
        lines.append(head + " {")

        inner = INDENT * (depth + 1)
        first_member = True
        for const in decl.constants:
            lines.append(f"{inner}const {const.name} = {self._expr(const.value)};")
            first_member = False
        if decl.constants and (decl.properties or decl.methods):
            lines.append("")
        for prop in decl.properties:
            modifiers = prop.visibility
            if prop.is_static:
                modifiers += " static"
            if prop.is_readonly:
                modifiers += " readonly"
            type_prefix = ""
            if prop.type:
                type_prefix = self._render_type_hint(prop.type, prop.is_nullable) + " "
            default = f" = {self._expr(prop.default)}" if prop.default is not None else ""
            lines.extend(self._doc_comment(prop.doc_comment, inner))
            lines.append(f"{inner}{modifiers} {type_prefix}${prop.name}{default};")
            first_member = False
        for index, method in enumerate(decl.methods):
            if index > 0 or not first_member:
                lines.append("")
            lines.extend(self._method(method, depth + 1, in_interface=decl.is_interface))
        lines.append(f"{pad}}}")
        return lines

    def _method(self, decl: php.MethodDecl, depth: int, in_interface: bool = False) -> list[str]:
        pad = INDENT * depth
        lines = self._doc_comment(decl.doc_comment, pad)
        modifiers = [decl.visibility]
        # Interface methods are implicitly abstract — PHP rejects an explicit
        # `abstract` keyword there. Only abstract *class* methods carry it.
        if decl.is_abstract and not in_interface:
            modifiers.insert(0, "abstract")
        if decl.is_final:
            modifiers.insert(0, "final")
        if decl.is_static:
            modifiers.append("static")
        ref = "&" if decl.by_ref else ""
        signature = (
            f"{pad}{' '.join(modifiers)} function {ref}{decl.name}({self._params(decl.params)})"
        )
        signature += self._return_type(decl.return_type, decl.return_nullable)
        if decl.is_abstract:
            lines.append(signature + ";")
            return lines
        lines.append(signature + " {")
        lines.extend(self._stmts(decl.body, depth + 1))
        lines.append(f"{pad}}}")
        return lines

    def _params(self, params: list[php.Param]) -> str:
        rendered = []
        for param in params:
            parts = []
            if param.type:
                parts.append(self._render_type_hint(param.type, param.nullable))
            name = "$" + param.name
            if param.variadic:
                name = "..." + name
            if param.by_ref:
                name = "&" + name
            parts.append(name)
            text = " ".join(parts)
            if param.default is not None:
                text += f" = {self._expr(param.default)}"
            rendered.append(text)
        return ", ".join(rendered)

    def _render_type_hint(self, type_hint: str, nullable: bool) -> str:
        if not type_hint:
            return ""
        if type_hint in ("mixed", "void", "never"):
            return type_hint
        if "|" in type_hint or "&" in type_hint:
            if nullable and "null" not in type_hint.split("|"):
                if "|" not in type_hint:
                    return f"({type_hint})|null"
                return f"{type_hint}|null"
            return type_hint
        return f"{'?' if nullable else ''}{type_hint}"

    def _return_type(self, return_type: str | None, nullable: bool) -> str:
        if not return_type:
            return ""
        rendered = self._render_type_hint(return_type, nullable)
        return f": {rendered}" if rendered else ""

    def _doc_comment(self, doc: str | None, pad: str) -> list[str]:
        if not doc or not isinstance(doc, str):
            return []
        start_idx = doc.find("/**")
        if start_idx == -1:
            return []
        doc = doc[start_idx:]
        if "*/" not in doc:
            doc = doc.rstrip() + "\n */"
        else:
            end_idx = doc.rfind("*/") + 2
            doc = doc[:end_idx]
        lines = []
        for line in doc.splitlines():
            cleaned_line = "".join(c for c in line if c in "\t\r\n" or 32 <= ord(c) < 127 or ord(c) > 127)
            lines.append(f"{pad}{cleaned_line}")
        return lines

    # -- expressions ------------------------------------------------------------

    def _expr(self, expr: php.Expr, parent_prec: int = 0) -> str:
        text, prec = self._render(expr)
        if prec < parent_prec:
            return f"({text})"
        return text

    def _render(self, expr: php.Expr) -> tuple[str, int]:
        if isinstance(expr, php.Literal):
            return self._literal(expr.value), _PREC["atom"]
        if isinstance(expr, php.Variable):
            if isinstance(expr.name, str):
                if is_valid_php_identifier(expr.name):
                    return f"${expr.name}", _PREC["atom"]
                return f"${{{_quote_string(expr.name)}}}", _PREC["atom"]
            if isinstance(expr.name, (php.Variable, php.TempVar)):
                inner_text, _ = self._render(expr.name)
                return f"${inner_text}", _PREC["atom"]
            if isinstance(expr.name, php.Expr):
                return f"${{{self._expr(expr.name)}}}", _PREC["atom"]
            return f"${{{expr.name}}}", _PREC["atom"]
        if isinstance(expr, php.TempVar):
            return f"${expr.name}", _PREC["atom"]
        if isinstance(expr, php.ConstFetch):
            return expr.name, _PREC["atom"]
        if isinstance(expr, php.ClassConstFetch):
            return f"{expr.class_name}::{expr.const_name}", _PREC["atom"]
        if isinstance(expr, php.ArrayLiteral):
            return self._array(expr), _PREC["atom"]
        if isinstance(expr, php.PropertyFetch):
            target = self._expr(expr.target, _PREC["postfix"])
            name = expr.name if isinstance(expr.name, str) and is_valid_php_identifier(expr.name) \
                else "{" + self._expr(expr.name) + "}" if isinstance(expr.name, php.Expr) \
                else "{" + self._literal(expr.name) + "}"
            arrow = "?->" if getattr(expr, "nullsafe", False) else "->"
            return f"{target}{arrow}{name}", _PREC["postfix"]
        if isinstance(expr, php.StaticPropertyFetch):
            return f"{expr.class_name}::${expr.name}", _PREC["postfix"]
        if isinstance(expr, php.DimFetch):
            target = self._expr(expr.target, _PREC["postfix"])
            index = self._expr(expr.index) if expr.index is not None else ""
            return f"{target}[{index}]", _PREC["postfix"]
        if isinstance(expr, php.BinaryOp):
            return self._binary(expr)
        if isinstance(expr, php.UnaryOp):
            if expr.op == "...":
                return f"...{self._expr(expr.operand, _PREC['unary'])}", _PREC["unary"]
            prec = _PREC["!"] if expr.op == "!" else _PREC["unary"]
            return f"{expr.op}{self._expr(expr.operand, prec)}", prec
        if isinstance(expr, php.Cast):
            return f"({expr.type}) {self._expr(expr.operand, _PREC['unary'])}", _PREC["unary"]
        if isinstance(expr, php.Assign):
            target = self._expr(expr.target, _PREC["postfix"])
            operator = f"{expr.op}=" if expr.op else "="
            if expr.by_ref:
                return f"{target} =& {self._expr(expr.value, _PREC['='])}", _PREC["="]
            return f"{target} {operator} {self._expr(expr.value, _PREC['='])}", _PREC["="]
        if isinstance(expr, php.IncDec):
            target = self._expr(expr.target, _PREC["postfix"])
            if expr.is_prefix:
                return f"{expr.op}{target}", _PREC["unary"]
            return f"{target}{expr.op}", _PREC["postfix"]
        if isinstance(expr, php.FuncCall):
            name = expr.name if isinstance(expr.name, str) else self._expr(expr.name, _PREC["postfix"])
            return f"{name}({self._args(expr.args)})", _PREC["postfix"]
        if isinstance(expr, php.MethodCall):
            target = self._expr(expr.target, _PREC["postfix"])
            name = expr.name if isinstance(expr.name, str) and is_valid_php_identifier(expr.name) \
                else "{" + (self._expr(expr.name) if isinstance(expr.name, php.Expr) else self._literal(expr.name)) + "}"
            arrow = "?->" if getattr(expr, "nullsafe", False) else "->"
            return f"{target}{arrow}{name}({self._args(expr.args)})", _PREC["postfix"]
        if isinstance(expr, php.StaticCall):
            cls = expr.class_name if isinstance(expr.class_name, str) else self._expr(expr.class_name, _PREC["postfix"])
            name = expr.name if isinstance(expr.name, str) else "{" + self._expr(expr.name) + "}"
            return f"{cls}::{name}({self._args(expr.args)})", _PREC["postfix"]
        if isinstance(expr, php.New):
            cls = expr.class_name if isinstance(expr.class_name, str) else self._expr(expr.class_name, _PREC["postfix"])
            return f"new {cls}({self._args(expr.args)})", _PREC["unary"]
        if isinstance(expr, php.Ternary):
            cond = self._expr(expr.cond, _PREC["?:"] + 1)
            if expr.if_true is None:
                return f"{cond} ?: {self._expr(expr.if_false, _PREC['?:'] + 1)}", _PREC["?:"]
            if_true = self._expr(expr.if_true, _PREC["?:"] + 1)
            if_false = self._expr(expr.if_false, _PREC["?:"] + 1)
            return f"{cond} ? {if_true} : {if_false}", _PREC["?:"]
        if isinstance(expr, php.Isset):
            return f"isset({self._args(expr.exprs)})", _PREC["atom"]
        if isinstance(expr, php.EmptyExpr):
            return f"empty({self._expr(expr.operand)})", _PREC["atom"]
        if isinstance(expr, php.InstanceOf):
            operand = self._expr(expr.operand, _PREC["instanceof"] + 1)
            cls = expr.class_name if isinstance(expr.class_name, str) else self._expr(expr.class_name, _PREC["postfix"])
            return f"{operand} instanceof {cls}", _PREC["instanceof"]
        if isinstance(expr, php.ErrorSuppress):
            return f"@{self._expr(expr.operand, _PREC['unary'])}", _PREC["unary"]
        if isinstance(expr, php.IncludeExpr):
            return f"{expr.kind} {self._expr(expr.operand, _PREC['='])}", _PREC["="] - 1
        if isinstance(expr, php.ExitExpr):
            if expr.operand is None:
                return "exit", _PREC["atom"]
            return f"exit({self._expr(expr.operand)})", _PREC["atom"]
        if isinstance(expr, php.ClosureExpr):
            return self._closure(expr), _PREC["atom"]
        if isinstance(expr, php.MatchExpr):
            return self._match(expr), _PREC["atom"]
        if isinstance(expr, php.RawExpr):
            return expr.code, 0
        return f"/* unsupported expr {type(expr).__name__} */ null", _PREC["atom"]

    def _binary(self, expr: php.BinaryOp) -> tuple[str, int]:
        prec = _PREC.get(expr.op, 11)
        left = self._expr(expr.left, prec)
        # Right operand of a left-associative operator needs parens at equal
        # precedence unless the operator chains associatively.
        right_min = prec if expr.op in _ASSOCIATIVE and _same_op(expr.right, expr.op) else prec + 1
        right = self._expr(expr.right, right_min)
        return f"{left} {expr.op} {right}", prec

    def _args(self, args: list[php.Expr]) -> str:
        return ", ".join(self._expr(a) for a in args)

    def _array(self, expr: php.ArrayLiteral) -> str:
        if not expr.items:
            return "[]"
        # Render values at one level deeper so nested arrays indent correctly.
        saved_depth = self._depth
        rendered = []
        for item in expr.items:
            self._depth = saved_depth + 1
            value = self._expr(item.value)
            self._depth = saved_depth
            if item.by_ref:
                value = "&" + value
            if item.key is not None:
                rendered.append(f"{self._expr(item.key)} => {value}")
            else:
                rendered.append(value)
        single_line = "[" + ", ".join(rendered) + "]"
        if len(single_line) <= 80 and len(rendered) <= 4:
            return single_line
        # Long arrays: one item per line, indented one level deeper than the
        # statement that contains them.
        outer_pad = INDENT * saved_depth
        inner_pad = outer_pad + INDENT
        inner = (",\n" + inner_pad).join(rendered)
        return "[\n" + inner_pad + inner + ",\n" + outer_pad + "]"

    def _closure(self, expr: php.ClosureExpr) -> str:
        head = "static function" if expr.is_static else "function"
        signature = f"{head} ({self._params(expr.params)})"
        if expr.uses:
            signature += " use (" + ", ".join(f"${u}" for u in expr.uses) + ")"
        # Indent the body relative to the statement the closure sits in, and
        # restore the saved depth afterwards (nested closures recurse here).
        depth = self._depth
        body_lines = self._stmts(expr.body, depth + 1)
        self._depth = depth
        if not body_lines:
            return signature + " {}"
        close_pad = INDENT * depth
        return signature + " {\n" + "\n".join(body_lines) + "\n" + close_pad + "}"

    def _match(self, expr: php.MatchExpr) -> str:
        subject = self._expr(expr.subject)
        arms_rendered = []
        depth = self._depth + 1
        pad = INDENT * depth
        for arm in expr.arms:
            if arm.conds is None:
                cond_str = "default"
            else:
                cond_str = ", ".join(self._expr(c) for c in arm.conds)
            val_str = self._expr(arm.body)
            arms_rendered.append(f"{pad}{cond_str} => {val_str},")
        close_pad = INDENT * self._depth
        return "match (" + subject + ") {\n" + "\n".join(arms_rendered) + "\n" + close_pad + "}"

    def _literal(self, value: object) -> str:
        if value is None:
            return "null"
        if isinstance(value, bool):
            return "true" if value else "false"
        if isinstance(value, int):
            return str(value)
        if isinstance(value, float):
            text = repr(value)
            return text
        if isinstance(value, PhpBytes):
            raw = bytes(value)
            decoded = try_decode_ioncube_array(raw)
            if decoded is not None:
                return self._array(_ioncube_to_array_literal(decoded))
            try:
                as_str = raw.decode('utf-8')
                if as_str.isprintable() or all(c in '\t\n\r' or c.isprintable() for c in as_str):
                    return _quote_string(as_str)
            except UnicodeDecodeError:
                pass
            return _double_quoted_bytes(raw)
        if isinstance(value, str):
            if value.startswith('['):
                decoded = try_decode_ioncube_array(value.encode('latin-1'))
                if decoded is not None:
                    return self._array(_ioncube_to_array_literal(decoded))
            return _quote_string(value)
        if isinstance(value, (list, tuple)):
            items = [php.ArrayItem(value=php.Literal(value=v)) for v in value]
            return self._array(php.ArrayLiteral(items=items))
        if isinstance(value, dict):
            keys = list(value.keys())
            if keys and all((isinstance(k, int) or (isinstance(k, str) and k.isdigit())) for k in keys):
                int_keys = [int(k) for k in keys]
                if sorted(int_keys) == list(range(len(int_keys))):
                    ordered_keys = keys if isinstance(keys[0], int) else [str(i) for i in range(len(keys))]
                    items = [php.ArrayItem(value=php.Literal(value=value[k])) for k in ordered_keys]
                    return self._array(php.ArrayLiteral(items=items))
            items = [php.ArrayItem(key=php.Literal(value=k), value=php.Literal(value=v)) for k, v in value.items()]
            return self._array(php.ArrayLiteral(items=items))
        return f"/* unrepresentable literal */ null"


def _ioncube_to_array_literal(entries: list) -> php.ArrayLiteral:
    """Convert ionCube decoded ``[(key, value), ...]`` to an :class:`ArrayLiteral`."""
    # Omit explicit keys when all keys are sequential ints 0, 1, 2, ...
    all_int = all(isinstance(k, int) for k, _ in entries)
    sequential = all_int and all(k == i for i, (k, _) in enumerate(entries))

    items = []
    for k, v in entries:
        key_expr = None if sequential else php.Literal(value=k)
        val_expr = _ioncube_to_array_literal(v) if isinstance(v, list) else php.Literal(value=v)
        items.append(php.ArrayItem(key=key_expr, value=val_expr))
    return php.ArrayLiteral(items=items)


def _same_op(expr: php.Expr, op: str) -> bool:
    return isinstance(expr, php.BinaryOp) and expr.op == op


def _quote_string(value: str) -> str:
    if all(32 <= ord(ch) < 127 or ch in "\t" for ch in value) or value.isprintable():
        escaped = value.replace("\\", "\\\\").replace("'", "\\'")
        return f"'{escaped}'"
    return _double_quoted_bytes(value.encode("utf-8", "surrogateescape"))


def _double_quoted_bytes(payload: bytes) -> str:
    chunks = []
    for byte in payload:
        ch = chr(byte)
        if ch == '"':
            chunks.append('\\"')
        elif ch == "\\":
            chunks.append("\\\\")
        elif ch == "$":
            chunks.append("\\$")
        elif ch == "\n":
            chunks.append("\\n")
        elif ch == "\r":
            chunks.append("\\r")
        elif ch == "\t":
            chunks.append("\\t")
        elif 32 <= byte < 127:
            chunks.append(ch)
        else:
            chunks.append(f"\\x{byte:02x}")
    return '"' + "".join(chunks) + '"'


def emit_php(node: php.PhpFile) -> str:
    return PhpEmitter().emit_file(node)
