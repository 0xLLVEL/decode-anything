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
    stmts = [_optimize_stmt(stmt) for stmt in stmts]
    stmts = _reconstruct_switches(stmts)
    stmts = _lift_terminating_else(stmts)
    return _drop_dead_code_after_terminal(stmts)


def _lift_terminating_else(stmts: list[php.Stmt]) -> list[php.Stmt]:
    """If an `if` branch unconditionally terminates (return, throw, exit), its
    `else` block does not need to be indented. Flatten it into the outer sequence.
    """
    out: list[php.Stmt] = []
    for stmt in stmts:
        if isinstance(stmt, php.IfStmt) and stmt.orelse:
            then_term = bool(stmt.then and _stmt_terminates(stmt.then[-1]))
            elifs_term = all(b and _stmt_terminates(b[-1]) for _, b in stmt.elifs)
            if then_term and elifs_term:
                orelse = stmt.orelse
                stmt.orelse = []
                out.append(stmt)
                out.extend(_lift_terminating_else(orelse))
                continue
        out.append(stmt)
    return out


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
        is_void_or_ctor = (stmt.name == "__construct") or (
            bool(stmt.return_type and stmt.return_type.lower() == "void")
        )
        body = _optimize_stmts(stmt.body)
        if is_void_or_ctor:
            body = _normalize_void_returns(body)
        stmt.body = _prune_unreferenced_labels(
            _drop_trailing_bare_return(
                body,
                return_type=stmt.return_type,
                return_nullable=stmt.return_nullable,
                is_constructor=(stmt.name == "__construct"),
            )
        )
        for param in stmt.params:
            if param.default is not None:
                param.default = _optimize_expr(param.default)
    elif isinstance(stmt, php.ClassDecl):
        for method in stmt.methods:
            is_void_or_ctor = (method.name == "__construct") or (
                bool(method.return_type and method.return_type.lower() == "void")
            )
            body = _optimize_stmts(method.body)
            if is_void_or_ctor:
                body = _normalize_void_returns(body)
            method.body = _prune_unreferenced_labels(
                _drop_trailing_bare_return(
                    body,
                    return_type=method.return_type,
                    return_nullable=method.return_nullable,
                    is_constructor=(method.name == "__construct"),
                )
            )
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
            if isinstance(inner, php.BinaryOp):
                if inner.op in _INVERTED_COMPARISON:
                    inner.op = _INVERTED_COMPARISON[inner.op]
                    return inner
                if inner.op == "&&" and (
                    (isinstance(inner.left, php.UnaryOp) and inner.left.op == "!")
                    or (isinstance(inner.right, php.UnaryOp) and inner.right.op == "!")
                ):
                    return php.BinaryOp(
                        op="||",
                        left=_optimize_expr(_negate(inner.left)),
                        right=_optimize_expr(_negate(inner.right)),
                    )
                if inner.op == "||" and (
                    isinstance(inner.left, php.UnaryOp) and inner.left.op == "!"
                    and isinstance(inner.right, php.UnaryOp) and inner.right.op == "!"
                ):
                    return php.BinaryOp(
                        op="&&",
                        left=_optimize_expr(_negate(inner.left)),
                        right=_optimize_expr(_negate(inner.right)),
                    )
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
    if isinstance(expr, php.MatchExpr):
        expr.subject = _optimize_expr(expr.subject)
        for arm in expr.arms:
            if arm.conds is not None:
                arm.conds = [_optimize_expr(c) for c in arm.conds]
            arm.body = _optimize_expr(arm.body)
        return expr
    if isinstance(expr, php.ClosureExpr):
        expr.body = _prune_unreferenced_labels(_optimize_stmts(expr.body))
        for p in expr.params:
            if p.default is not None:
                p.default = _optimize_expr(p.default)
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
    ):
        inner = stmt.orelse[0]
        stmt.elifs.append((inner.cond, inner.then))
        stmt.elifs.extend(inner.elifs)
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


def _stmt_terminates(stmt: php.Stmt) -> bool:
    """Return True if execution unconditionally terminates after this statement."""
    if isinstance(stmt, (php.ReturnStmt, php.ThrowStmt)):
        return True
    if isinstance(stmt, php.ExprStmt) and isinstance(stmt.expr, php.ExitExpr):
        return True
    if isinstance(stmt, php.TryStmt):
        if not (stmt.body and _stmt_terminates(stmt.body[-1])):
            return False
        for c in stmt.catches:
            if not (c.body and _stmt_terminates(c.body[-1])):
                return False
        return True
    if isinstance(stmt, php.IfStmt):
        if not (stmt.then and _stmt_terminates(stmt.then[-1])):
            return False
        if not (stmt.orelse and _stmt_terminates(stmt.orelse[-1])):
            return False
        for _, b in stmt.elifs:
            if not (b and _stmt_terminates(b[-1])):
                return False
        return True
    return False


def _drop_dead_code_after_terminal(stmts: list[php.Stmt]) -> list[php.Stmt]:
    """Prune unreachable statements that follow an unconditional terminal statement.

    If any following statement is a LabelStmt, execution can jump to it via goto,
    so subsequent statements are not dead code.
    """
    out: list[php.Stmt] = []
    for idx, stmt in enumerate(stmts):
        out.append(stmt)
        if _stmt_terminates(stmt):
            remaining = stmts[idx + 1 :]
            has_label = any(isinstance(s, php.LabelStmt) for s in remaining)
            if not has_label:
                break
    return out


def _normalize_void_returns(stmts: list[php.Stmt]) -> list[php.Stmt]:
    """In constructor and : void functions, convert `return null;` to bare `return;`."""
    for s in stmts:
        if isinstance(s, php.ReturnStmt):
            if s.value is None or (isinstance(s.value, php.Literal) and s.value.value is None):
                s.value = None
        elif isinstance(s, php.IfStmt):
            _normalize_void_returns(s.then)
            for _, b in s.elifs:
                _normalize_void_returns(b)
            _normalize_void_returns(s.orelse)
        elif isinstance(s, (php.WhileStmt, php.DoWhileStmt, php.ForeachStmt)):
            _normalize_void_returns(s.body)
        elif isinstance(s, php.TryStmt):
            _normalize_void_returns(s.body)
            for c in s.catches:
                _normalize_void_returns(c.body)
            if s.finally_body:
                _normalize_void_returns(s.finally_body)
        elif isinstance(s, php.SwitchStmt):
            for c in s.cases:
                _normalize_void_returns(c.body)
    return stmts


def _drop_trailing_bare_return(
    stmts: list[php.Stmt],
    return_type: str | None = None,
    return_nullable: bool = False,
    is_constructor: bool = False,
) -> list[php.Stmt]:
    """The compiler appends an implicit `return null;` or `return;` to functions."""
    stmts = _drop_dead_code_after_terminal(stmts)
    if not stmts:
        return stmts

    if isinstance(stmts[-1], php.ReturnStmt):
        val = stmts[-1].value
        is_none_val = val is None or (isinstance(val, php.Literal) and val.value is None)
        if is_none_val:
            if len(stmts) > 1 and _stmt_terminates(stmts[-2]):
                return stmts[:-1]
            if is_constructor:
                return stmts[:-1]
            if return_type and not return_nullable:
                if len(stmts) > 1 and _stmt_terminates(stmts[-2]):
                    return stmts[:-1]
                rtype = return_type.lower()
                if rtype == "array":
                    stmts[-1].value = php.ArrayLiteral()
                    return stmts
                elif rtype == "string":
                    stmts[-1].value = php.Literal(value="")
                    return stmts
                elif rtype == "bool":
                    stmts[-1].value = php.Literal(value=False)
                    return stmts
                elif rtype in ("int", "float"):
                    stmts[-1].value = php.Literal(value=0)
                    return stmts
                elif rtype == "void":
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


def _has_side_effects(expr: php.Expr) -> bool:
    if isinstance(expr, (php.FuncCall, php.MethodCall, php.StaticCall, php.New, php.Assign)):
        return True
    if isinstance(expr, php.UnaryOp):
        return _has_side_effects(expr.operand)
    if isinstance(expr, php.BinaryOp):
        return _has_side_effects(expr.left) or _has_side_effects(expr.right)
    if isinstance(expr, php.Cast):
        return _has_side_effects(expr.operand)
    return False


def _drop_redundant_gotos(stmts: list[php.Stmt]) -> list[php.Stmt]:
    """Drop redundant gotos:
    1. `goto label_X;` if execution immediately reaches `label_X:`.
    2. `if (cond) { goto label_X; }` if immediately followed by `label_X:`.
    """
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
        elif (
            isinstance(stmt, php.IfStmt)
            and not stmt.elifs
            and not stmt.orelse
            and len(stmt.then) == 1
            and isinstance(stmt.then[0], php.GotoStmt)
        ):
            target_label = stmt.then[0].label
            j = i + 1
            while j < n and isinstance(stmts[j], php.OpcodeComment):
                j += 1
            if j < n and isinstance(stmts[j], php.LabelStmt) and stmts[j].label == target_label:
                if _has_side_effects(stmt.cond):
                    out.append(php.ExprStmt(stmt.cond))
                i += 1
                continue
        out.append(stmt)
        i += 1
    return out


def _parse_neq(cond: php.Expr) -> tuple[php.Expr, php.Expr] | None:
    if isinstance(cond, php.UnaryOp) and cond.op == "!":
        if isinstance(cond.operand, php.BinaryOp) and cond.operand.op in ("==", "==="):
            return cond.operand.left, cond.operand.right
    elif isinstance(cond, php.BinaryOp) and cond.op in ("!=", "!=="):
        return cond.left, cond.right
    return None


def _match_switch_dispatcher(stmt: php.Stmt):
    if not isinstance(stmt, php.IfStmt) or stmt.orelse or stmt.elifs:
        return None
    parsed = _parse_neq(stmt.cond)
    if parsed is None:
        return None
    subject, case0_val = parsed

    if not stmt.then:
        return None

    cases: list[tuple[php.Expr, str | None]] = [(case0_val, None)]
    default_label: str | None = None

    for idx, s in enumerate(stmt.then):
        if isinstance(s, php.IfStmt) and not s.orelse and not s.elifs:
            icond = s.cond
            if isinstance(icond, php.BinaryOp) and icond.op in ("==", "==="):
                val = None
                if icond.left == subject:
                    val = icond.right
                elif icond.right == subject:
                    val = icond.left
                if val is not None and len(s.then) == 1 and isinstance(s.then[0], php.GotoStmt):
                    cases.append((val, s.then[0].label))
                    continue
        elif isinstance(s, php.GotoStmt) and idx == len(stmt.then) - 1:
            default_label = s.label
            continue
        return None

    return {
        "subject": subject,
        "cases": cases,
        "default_label": default_label,
    }


def _try_extract_switch(stmts: list[php.Stmt], start_idx: int, match: dict):
    subject = match["subject"]
    cases_info: list[tuple[php.Expr, str | None]] = match["cases"]
    default_label: str | None = match["default_label"]
    n = len(stmts)

    label_indices: dict[str, int] = {}
    for idx in range(start_idx + 1, n):
        s = stmts[idx]
        if isinstance(s, php.LabelStmt):
            label_indices[s.label] = idx

    for val, lbl in cases_info:
        if lbl is not None and lbl not in label_indices:
            return None

    case0_end = start_idx + 1
    while case0_end < n and not isinstance(stmts[case0_end], php.LabelStmt):
        case0_end += 1

    case0_stmts = stmts[start_idx + 1 : case0_end]

    break_label: str | None = None
    if case0_stmts:
        last_s = case0_stmts[-1]
        if isinstance(last_s, php.GotoStmt):
            break_label = last_s.label
        elif not isinstance(last_s, (php.ReturnStmt, php.ThrowStmt)):
            return None

    all_case_labels: list[tuple[str, php.Expr | None]] = [
        (lbl, val) for val, lbl in cases_info if lbl is not None
    ]
    if default_label is not None and default_label in label_indices:
        if break_label is None or default_label != break_label:
            all_case_labels.append((default_label, None))

    sorted_case_labels = sorted(all_case_labels, key=lambda x: label_indices[x[0]])

    if break_label is None:
        case_label_names = {lbl for lbl, _ in all_case_labels}
        for lbl, _ in sorted_case_labels:
            lidx = label_indices[lbl]
            j = lidx + 1
            while j < n and not isinstance(stmts[j], php.LabelStmt):
                j += 1
            if j > lidx + 1 and isinstance(stmts[j - 1], php.GotoStmt):
                target = stmts[j - 1].label
                if target not in case_label_names:
                    break_label = target
                    break

    def clean_body(body_stmts: list[php.Stmt]) -> list[php.Stmt]:
        res: list[php.Stmt] = []
        for s in body_stmts:
            if isinstance(s, php.GotoStmt) and break_label and s.label == break_label:
                res.append(php.BreakStmt(level=1))
            else:
                res.append(s)
        if res and not isinstance(res[-1], (php.ReturnStmt, php.ThrowStmt, php.BreakStmt)):
            res.append(php.BreakStmt(level=1))
        return res

    extracted_cases: list[php.SwitchCase] = []
    extracted_cases.append(php.SwitchCase(test=cases_info[0][0], body=clean_body(case0_stmts)))

    last_end = case0_end
    for lbl, val in sorted_case_labels:
        lbl_idx = label_indices[lbl]
        if lbl_idx < last_end:
            return None
        body_end = lbl_idx + 1
        while body_end < n and not isinstance(stmts[body_end], php.LabelStmt):
            body_end += 1
        body = clean_body(stmts[lbl_idx + 1 : body_end])
        extracted_cases.append(php.SwitchCase(test=val, body=body))
        last_end = body_end

    switch_stmt = php.SwitchStmt(subject=subject, cases=extracted_cases)
    return switch_stmt, last_end


def _reconstruct_switches(stmts: list[php.Stmt]) -> list[php.Stmt]:
    out: list[php.Stmt] = []
    i = 0
    n = len(stmts)
    while i < n:
        stmt = stmts[i]
        match = _match_switch_dispatcher(stmt)
        if match is not None:
            res = _try_extract_switch(stmts, i, match)
            if res is not None:
                new_switch, next_i = res
                out.append(new_switch)
                i = next_i
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

