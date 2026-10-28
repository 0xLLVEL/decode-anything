"""AST cleanup passes (Milestone 5).

Each pass is a small, isolated transformation; ``optimize`` runs them all.
They only ever make the tree *more* readable -- never change semantics:

* drop ``(bool)`` casts in boolean contexts (if/while/ternary conditions),
* fold ``!`` over comparisons into the inverted comparison,
* remove double negation,
* flip ``if (!c) {} else {B}`` into ``if (c) {B}``,
* drop empty ``else`` branches.
"""

from __future__ import annotations

from .. import ast as php

_INVERTED_COMPARISON = {
    "==": "!=",
    "!=": "==",
    "===": "!==",
    "!==": "===",
    "<": ">=",
    ">=": "<",
    ">": "<=",
    "<=": ">",
}


def optimize(node: php.PhpFile) -> php.PhpFile:
    node.statements = _prune_unreferenced_labels(_optimize_stmts(node.statements))
    return node


def _optimize_stmts(stmts: list[php.Stmt]) -> list[php.Stmt]:
    stmts = _drop_redundant_gotos(stmts)
    return [_optimize_stmt(stmt) for stmt in stmts]


def _optimize_stmt(stmt: php.Stmt) -> php.Stmt:
    if isinstance(stmt, php.ExprStmt):
        stmt.expr = _optimize_expr(stmt.expr)
    elif isinstance(stmt, php.EchoStmt):
        stmt.exprs = [_optimize_expr(e) for e in stmt.exprs]
    elif isinstance(stmt, php.ReturnStmt):
        if stmt.value is not None:
            stmt.value = _optimize_expr(stmt.value)
    elif isinstance(stmt, php.IfStmt):
        stmt.cond = _boolean_context(_optimize_expr(stmt.cond))
        stmt.then = _optimize_stmts(stmt.then)
        stmt.elifs = [
            (_boolean_context(_optimize_expr(cond)), _optimize_stmts(body))
            for cond, body in stmt.elifs
        ]
        stmt.orelse = _optimize_stmts(stmt.orelse)
        stmt = _normalize_if(stmt)
    elif isinstance(stmt, php.WhileStmt):
        stmt.cond = _boolean_context(_optimize_expr(stmt.cond))
        stmt.body = _drop_trailing_continue(_optimize_stmts(stmt.body))
    elif isinstance(stmt, php.DoWhileStmt):
        stmt.cond = _boolean_context(_optimize_expr(stmt.cond))
        stmt.body = _drop_trailing_continue(_optimize_stmts(stmt.body))
    elif isinstance(stmt, php.ForeachStmt):
        stmt.iterable = _optimize_expr(stmt.iterable)
        stmt.body = _drop_trailing_continue(_optimize_stmts(stmt.body))
    elif isinstance(stmt, php.SwitchStmt):
        stmt.subject = _optimize_expr(stmt.subject)
        for case in stmt.cases:
            if case.test is not None:
                case.test = _optimize_expr(case.test)
            case.body = _optimize_stmts(case.body)
    elif isinstance(stmt, php.UnsetStmt):
        stmt.exprs = [_optimize_expr(e) for e in stmt.exprs]
    elif isinstance(stmt, php.ThrowStmt):
        stmt.expr = _optimize_expr(stmt.expr)
    elif isinstance(stmt, php.TryStmt):
        stmt.body = _optimize_stmts(stmt.body)
        for clause in stmt.catches:
            clause.body = _optimize_stmts(clause.body)
        if stmt.finally_body is not None:
            stmt.finally_body = _optimize_stmts(stmt.finally_body)
    elif isinstance(stmt, php.FunctionDecl):
        stmt.body = _prune_unreferenced_labels(_drop_trailing_bare_return(_optimize_stmts(stmt.body)))
        for param in stmt.params:
            if param.default is not None:
                param.default = _optimize_expr(param.default)
    elif isinstance(stmt, php.ClassDecl):
        for method in stmt.methods:
            method.body = _prune_unreferenced_labels(_drop_trailing_bare_return(_optimize_stmts(method.body)))
            for param in method.params:
                if param.default is not None:
                    param.default = _optimize_expr(param.default)
    elif isinstance(stmt, php.StaticVarStmt):
        if stmt.default is not None:
            stmt.default = _optimize_expr(stmt.default)
    return stmt


def _optimize_expr(expr: php.Expr) -> php.Expr:
    # Bottom-up rewrite.
    if isinstance(expr, php.BinaryOp):
        expr.left = _optimize_expr(expr.left)
        expr.right = _optimize_expr(expr.right)
        if expr.op in ("&&", "||"):
            expr.left = _boolean_context(expr.left)
            expr.right = _boolean_context(expr.right)
        return expr
    if isinstance(expr, php.UnaryOp):
        expr.operand = _optimize_expr(expr.operand)
        if expr.op == "!":
            inner = _boolean_context(expr.operand)
            if isinstance(inner, php.UnaryOp) and inner.op == "!":
                return _boolean_context(inner.operand)
            if isinstance(inner, php.BinaryOp) and inner.op in _INVERTED_COMPARISON:
                inner.op = _INVERTED_COMPARISON[inner.op]
                return inner
            expr.operand = inner
        return expr
    if isinstance(expr, php.Cast):
        expr.operand = _optimize_expr(expr.operand)
        return expr
    if isinstance(expr, php.Assign):
        expr.target = _optimize_expr(expr.target)
        expr.value = _optimize_expr(expr.value)
        return expr
    if isinstance(expr, php.Ternary):
        expr.cond = _boolean_context(_optimize_expr(expr.cond))
        if expr.if_true is not None:
            expr.if_true = _optimize_expr(expr.if_true)
        expr.if_false = _optimize_expr(expr.if_false)
        return expr
    if isinstance(expr, (php.FuncCall, php.MethodCall, php.StaticCall, php.New)):
        expr.args = [_optimize_expr(a) for a in expr.args]
        if isinstance(expr, php.MethodCall):
            expr.target = _optimize_expr(expr.target)
        return expr
    if isinstance(expr, php.DimFetch):
        expr.target = _optimize_expr(expr.target)
        if expr.index is not None:
            expr.index = _optimize_expr(expr.index)
        return expr
    if isinstance(expr, php.PropertyFetch):
        expr.target = _optimize_expr(expr.target)
        return expr
    if isinstance(expr, php.ArrayLiteral):
        for item in expr.items:
            item.value = _optimize_expr(item.value)
            if item.key is not None:
                item.key = _optimize_expr(item.key)
        return expr
    if isinstance(expr, php.ErrorSuppress):
        expr.operand = _optimize_expr(expr.operand)
        return expr
    if isinstance(expr, php.IncludeExpr):
        expr.operand = _optimize_expr(expr.operand)
        return expr
    if isinstance(expr, (php.Isset,)):
        expr.exprs = [_optimize_expr(e) for e in expr.exprs]
        return expr
    if isinstance(expr, php.EmptyExpr):
        expr.operand = _optimize_expr(expr.operand)
        return expr
    if isinstance(expr, php.InstanceOf):
        expr.operand = _optimize_expr(expr.operand)
        return expr
    return expr


def _boolean_context(expr: php.Expr) -> php.Expr:
    """In a condition, `(bool) x` is just `x`."""
    while isinstance(expr, php.Cast) and expr.type == "bool":
        expr = expr.operand
    return expr


def _normalize_if(stmt: php.IfStmt) -> php.IfStmt:
    if not stmt.then and stmt.orelse and not stmt.elifs:
        stmt.cond = _negate(stmt.cond)
        stmt.then = stmt.orelse
        stmt.orelse = []
    # else { if (...) {...} } -> elseif chain
    while (
        len(stmt.orelse) == 1
        and isinstance(stmt.orelse[0], php.IfStmt)
        and not stmt.orelse[0].elifs
    ):
        inner = stmt.orelse[0]
        stmt.elifs.append((inner.cond, inner.then))
        stmt.orelse = inner.orelse
    return stmt


def _drop_trailing_continue(stmts: list[php.Stmt]) -> list[php.Stmt]:
    """`continue;` as the last statement of a loop body is a no-op.

    Also drops one nested level: `if (...) { ...; continue; }` at the very
    end of the body.
    """
    if stmts and isinstance(stmts[-1], php.ContinueStmt) and stmts[-1].level == 1:
        stmts = stmts[:-1]
    if stmts and isinstance(stmts[-1], php.IfStmt):
        last_if = stmts[-1]
        if not last_if.elifs and not last_if.orelse and last_if.then and \
                isinstance(last_if.then[-1], php.ContinueStmt) and last_if.then[-1].level == 1:
            last_if.then = last_if.then[:-1]
    return stmts


def _drop_trailing_bare_return(stmts: list[php.Stmt]) -> list[php.Stmt]:
    """The compiler appends an implicit `return null;` or `return;` to functions."""
    if stmts and isinstance(stmts[-1], php.ReturnStmt):
        val = stmts[-1].value
        is_none_val = val is None or (isinstance(val, php.Literal) and val.value is None)
        if is_none_val:
            if len(stmts) > 1 and isinstance(stmts[-2], (php.ReturnStmt, php.ThrowStmt)):
                return stmts[:-1]
            if val is None:
                return stmts[:-1]
    return stmts


def _negate(expr: php.Expr) -> php.Expr:
    if isinstance(expr, php.UnaryOp) and expr.op == "!":
        return expr.operand
    if isinstance(expr, php.BinaryOp) and expr.op in _INVERTED_COMPARISON:
        return php.BinaryOp(op=_INVERTED_COMPARISON[expr.op], left=expr.left, right=expr.right)
    return php.UnaryOp(op="!", operand=expr)


def _drop_redundant_gotos(stmts: list[php.Stmt]) -> list[php.Stmt]:
    """Drop `goto label_X;` if execution immediately reaches `label_X:`."""
    out: list[php.Stmt] = []
    i = 0
    n = len(stmts)
    while i < n:
        stmt = stmts[i]
        if isinstance(stmt, php.GotoStmt):
            j = i + 1
            while j < n and isinstance(stmts[j], php.OpcodeComment):
                j += 1
            if j < n and isinstance(stmts[j], php.LabelStmt) and stmts[j].label == stmt.label:
                i += 1
                continue
        out.append(stmt)
        i += 1
    return out


def _prune_unreferenced_labels(stmts: list[php.Stmt]) -> list[php.Stmt]:
    """Remove any `label_X:` that has no corresponding `goto label_X;`."""
    goto_labels: set[str] = set()

    def scan_gotos(s: php.Stmt) -> None:
        if isinstance(s, php.GotoStmt):
            goto_labels.add(s.label)
        elif isinstance(s, php.IfStmt):
            for t in s.then:
                scan_gotos(t)
            for _, b in s.elifs:
                for t in b:
                    scan_gotos(t)
            for o in s.orelse:
                scan_gotos(o)
        elif isinstance(s, (php.WhileStmt, php.DoWhileStmt, php.ForeachStmt)):
            for b in s.body:
                scan_gotos(b)
        elif isinstance(s, php.TryStmt):
            for b in s.body:
                scan_gotos(b)
            for c in s.catches:
                for b in c.body:
                    scan_gotos(b)
            if s.finally_body:
                for b in s.finally_body:
                    scan_gotos(b)
        elif isinstance(s, php.SwitchStmt):
            for c in s.cases:
                for b in c.body:
                    scan_gotos(b)

    for s in stmts:
        scan_gotos(s)

    def prune(block: list[php.Stmt]) -> list[php.Stmt]:
        filtered: list[php.Stmt] = []
        for s in block:
            if isinstance(s, php.LabelStmt) and s.label not in goto_labels:
                continue
            if isinstance(s, php.IfStmt):
                s.then = prune(s.then)
                s.elifs = [(c, prune(b)) for c, b in s.elifs]
                s.orelse = prune(s.orelse)
            elif isinstance(s, (php.WhileStmt, php.DoWhileStmt, php.ForeachStmt)):
                s.body = prune(s.body)
            elif isinstance(s, php.TryStmt):
                s.body = prune(s.body)
                for c in s.catches:
                    c.body = prune(c.body)
                if s.finally_body:
                    s.finally_body = prune(s.finally_body)
            elif isinstance(s, php.SwitchStmt):
                for c in s.cases:
                    c.body = prune(c.body)
            filtered.append(s)
        return filtered

    return prune(stmts)

