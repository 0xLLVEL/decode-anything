"""Control-flow structuring: linear opcode walk that rebuilds if/else,
while, do-while, foreach, ternaries, short-circuit operators and try/catch.

The walker processes an inclusive index range.  Non-control-flow opcodes
are dispatched to the handler registry; jumps are pattern-matched:

* ``JMPZ/JMPNZ -> t`` (forward), ``ops[t-1] == JMP`` back before the branch
  -> ``while`` loop (condition first, back-jump at the end).
* ``JMPZ/JMPNZ -> t`` (forward), ``ops[t-1] == JMP`` further forward
  -> ``if / else``.
* ``JMPZ/JMPNZ -> t`` (forward), otherwise -> plain ``if``.
* ``JMPNZ/JMPZ -> t`` with ``t <= i`` (back edge) -> ``do { } while``.
* ``JMPZ_EX / JMPNZ_EX`` -> ``&&`` / ``||`` sub-expressions.
* ``FE_RESET_R + FE_FETCH_R`` -> ``foreach``.
* Inside loop bodies, ``JMP`` to the break/continue targets -> ``break;`` /
  ``continue;``.

Anything that does not match falls back to an :class:`OpcodeComment`
statement so the output stays valid PHP and nothing is silently dropped.
"""

from __future__ import annotations

from .. import ast as php
from ..opcode import OpArray, Opcode
from .context import DecompileContext, LoopInfo, literal_to_expr
from .handlers import get_handler

_LOOP_COND_JUMPS = {"ZEND_JMPZ", "ZEND_JMPNZ"}


class RangeDecompiler:
    def __init__(self, ctx: DecompileContext) -> None:
        self.ctx = ctx
        self.ops = ctx.ops
        self._active_try_catches: set[int] = set()

    # -- public entry --------------------------------------------------------

    def run(self) -> list[php.Stmt]:
        if self.ops:
            self.decompile_range(0, len(self.ops) - 1)
        for target in sorted(self.ctx.goto_targets - self.ctx.labels_emitted):
            self.ctx.labels_emitted.add(target)
            self.ctx.emit(target, php.LabelStmt(label=f"label_{target}"))
        for frame in self.ctx.call_stack:
            self.ctx.warn(f"unterminated call frame for {frame.name!r}")
        return self.ctx.statements()

    # -- range walker --------------------------------------------------------

    def decompile_range(self, start: int, end: int) -> None:
        """Decompile ops[start..end] (inclusive) into the current sink."""
        i = start
        while i <= end:
            i = self.step(i, end)

    def decompile_into(self, start: int, end: int) -> list[php.Stmt]:
        self.ctx.push_sink()
        self.decompile_range(start, end)
        return self.ctx.pop_sink()

    def step(self, i: int, end: int) -> int:
        # Emit a label here if a goto (an unstructurable forward jump) targets
        # this opcode or an earlier opcode that was skipped in a gap.
        for target in sorted(self.ctx.goto_targets - self.ctx.labels_emitted):
            if target <= i:
                self.ctx.labels_emitted.add(target)
                self.ctx.emit(target, php.LabelStmt(label=f"label_{target}"))


        op = self.ops[i]
        name = op.name

        if op.decode_failed:
            self.ctx.emit(i, php.OpcodeComment(i, name, "decode failed"))
            return i + 1

        try_stmt_end = self._try_catch_at(i, end)
        if try_stmt_end is not None:
            return try_stmt_end

        if name in ("ZEND_JMPZ", "ZEND_JMPNZ"):
            return self._conditional_jump(i, end, op)
        if name == "ZEND_JMP":
            return self._unconditional_jump(i, end, op)
        if name in ("ZEND_JMPZ_EX", "ZEND_JMPNZ_EX"):
            return self._short_circuit(i, end, op)
        if name in ("ZEND_JMP_SET", "ZEND_COALESCE"):
            return self._jmp_set(i, end, op)
        if name == "ZEND_JMP_NULL":
            return self._jmp_null(i, end, op)
        if name in ("ZEND_SWITCH_STRING", "ZEND_SWITCH_LONG") or (
            name in ("ZEND_CASE", "ZEND_CASE_STRICT") and self._starts_case_chain(i, end)
        ):
            return self._switch(i, end, op)
        if name in ("ZEND_FE_RESET_R", "ZEND_FE_RESET_RW"):
            return self._foreach(i, end, op)
        if name in ("ZEND_FE_FETCH_R", "ZEND_FE_FETCH_RW"):
            # Reached only when FE_RESET pairing failed.
            self.ctx.emit(i, php.OpcodeComment(i, name, "unpaired FE_FETCH"))
            return i + 1
        if name == "ZEND_CATCH":
            # Reached only outside try/catch carving; skip its body region.
            self.ctx.emit(i, php.OpcodeComment(i, name, "unstructured catch"))
            return i + 1

        handler = get_handler(name)
        if handler is None:
            self.ctx.warn(f"op {i}: no handler for {name}")
            self.ctx.emit(i, php.OpcodeComment(i, name, _describe(op)))
            return i + 1
        consumed = handler(self.ctx, op)
        return i + (consumed if isinstance(consumed, int) and consumed > 0 else 1)

    # -- conditional jumps -----------------------------------------------------

    def _conditional_jump(self, i: int, end: int, op: Opcode) -> int:
        target = op.jump_targets[0] if op.jump_targets else None
        cond = self.ctx.resolve(op.op1, op)
        if op.name == "ZEND_JMPNZ":
            jump_when_true = True
        else:
            jump_when_true = False

        if target is None:
            self.ctx.emit(i, php.OpcodeComment(i, op.name, "missing jump target"))
            return i + 1

        # break / continue inside a structured loop body.
        loop_stmt = self._loop_exit_stmt(target)
        if loop_stmt is not None:
            body_cond = cond if jump_when_true else php.UnaryOp(op="!", operand=cond)
            self.ctx.emit(i, php.IfStmt(cond=body_cond, then=[loop_stmt]))
            return i + 1

        if target <= i:
            target_op_name = self.ops[target].name
            if target_op_name in ("ZEND_RETURN", "ZEND_VERIFY_RETURN_TYPE", "ZEND_EXIT", "ZEND_THROW"):
                ret_body = self.decompile_into(target, min(target + 1, len(self.ops) - 1))
                ret_body = [s for s in ret_body if isinstance(s, (php.ReturnStmt, php.ExitExpr, php.ThrowStmt))]
                if ret_body:
                    body_cond = cond if jump_when_true else php.UnaryOp(op="!", operand=cond)
                    self.ctx.emit(i, php.IfStmt(cond=body_cond, then=ret_body))
                    return i + 1
            # Back edge: do { ... } while (cond);
            return self._do_while(i, op, cond, jump_when_true, target)

        if target > end + 1:
            # Conditional jump leaving the region: a source-level
            # `if (<cond>) goto <label>;` (the jump fires when the branch is
            # taken). JMPZ jumps on false, JMPNZ on true.
            goto_cond = cond if jump_when_true else php.UnaryOp(op="!", operand=cond)
            self.ctx.goto_targets.add(target)
            self.ctx.emit(i, php.IfStmt(cond=goto_cond, then=[php.GotoStmt(label=f"label_{target}")]))
            return i + 1

        # `if` condition is the *fallthrough* condition.
        if_cond = php.UnaryOp(op="!", operand=cond) if jump_when_true else cond

        # While pattern: last op before target jumps back before the branch
        # (the back-jump target is the start of the condition computation).
        # A back jump that exits to an *enclosing* loop's continue/break
        # target is not a while -- it is an `if` whose body ends in
        # continue/break.
        back = self._jmp_target(target - 1)
        if (
            back is not None
            and back <= i
            and target - 2 >= i
            and self._loop_exit_stmt(back) is None
        ):
            self.ctx.loop_stack.append(
                LoopInfo(break_targets={target}, continue_targets={back, i})
            )
            body = self.decompile_into(i + 1, target - 2)
            self.ctx.loop_stack.pop()
            self.ctx.emit(i, php.WhileStmt(cond=if_cond, body=body))
            return target

        # If/else pattern: then-branch ends with a forward JMP over the else.
        # Guard: this is a genuine else only if the would-be else region is
        # *not* entered by a jump originating inside the then-body. When the
        # then-body jumps into it (e.g. `if (C) { ...; goto END; }` followed by
        # shared continuation code that other branches also reach), the region
        # is a continuation, not an else — structure a plain `if` + `goto`
        # instead so the control flow stays faithful.
        skip = self._jmp_target(target - 1)
        if (
            skip is not None
            and skip > target
            and skip <= end + 1
            and target - 2 >= i
            and not self._region_entered_from(i + 1, target - 2, target, skip - 1)
        ):
            keys_before = set(self.ctx.temps)
            then_body = self.decompile_into(i + 1, target - 2)
            then_keys = set(self.ctx.temps) - keys_before
            then_value = (
                self.ctx.temps.pop(next(iter(then_keys)))
                if not then_body and len(then_keys) == 1
                else None
            )
            then_key = next(iter(then_keys)) if len(then_keys) == 1 else None

            keys_before_else = set(self.ctx.temps)
            else_body = self.decompile_into(target, skip - 1)
            else_keys = set(self.ctx.temps) - keys_before_else

            # Ternary: both branches are pure and feed the same temp slot.
            if (
                then_value is not None
                and not else_body
                and else_keys == {then_key}
                and then_key is not None
            ):
                else_value = self.ctx.temps.pop(then_key)
                self.ctx.temps[then_key] = php.Ternary(
                    cond=if_cond, if_true=then_value, if_false=else_value
                )
                return skip

            if then_value is not None and then_key is not None:
                # Not a ternary after all: rematerialize the then value.
                self.ctx.temps[then_key] = then_value
            self.ctx.emit(i, php.IfStmt(cond=if_cond, then=then_body, orelse=else_body))
            return skip

        # Plain if.
        then_body = self.decompile_into(i + 1, target - 1)
        self.ctx.emit(i, php.IfStmt(cond=if_cond, then=then_body))
        return target

    def _region_entered_from(
        self, body_start: int, body_end: int, region_start: int, region_end: int
    ) -> bool:
        """True if any op in [body_start, body_end] jumps into [region_start, region_end].

        Used to tell a real else (only reached by fallthrough) from a shared
        continuation (also reached by a jump out of the then-body).
        """
        if body_start > body_end:
            return False
        for k in range(body_start, min(body_end, len(self.ops) - 1) + 1):
            for t in (self.ops[k].jump_targets or ()):
                if region_start <= t <= region_end:
                    return True
        return False

    def _do_while(self, i: int, op: Opcode, cond: php.Expr, jump_when_true: bool, target: int) -> int:
        loop_cond = cond if jump_when_true else php.UnaryOp(op="!", operand=cond)
        sink = self.ctx.current_sink()
        body: list[php.Stmt] = []
        while sink and sink[-1][0] >= target:
            body.insert(0, sink.pop()[1])
        if body:
            self.ctx.emit(i, php.DoWhileStmt(body=body, cond=loop_cond))
        return i + 1

    def _loop_exit_stmt(self, target: int) -> php.Stmt | None:
        for depth, loop in enumerate(reversed(self.ctx.loop_stack), start=1):
            if target in loop.break_targets:
                return php.BreakStmt(level=depth)
            if target in loop.continue_targets:
                return php.ContinueStmt(level=depth)
        return None

    def _unconditional_jump(self, i: int, end: int, op: Opcode) -> int:
        target = op.jump_targets[0] if op.jump_targets else None
        if target is None:
            self.ctx.emit(i, php.OpcodeComment(i, op.name, "missing jump target"))
            return i + 1
        loop_stmt = self._loop_exit_stmt(target)
        if loop_stmt is not None:
            self.ctx.emit(i, loop_stmt)
            return i + 1
        if target > i and target <= end + 1:
            if target == i + 1:
                return i + 1  # jump to next op: no-op
            # Bottom-tested while: `JMP -> Lcond; Lbody: ...; Lcond: cond;
            # JMPNZ -> Lbody`.  PHP compiles while/for loops this way.
            structured = self._bottom_tested_while(i, end, target)
            if structured is not None:
                return structured
            self._emit_goto(i, op, target)
            return i + 1
        if target <= i:
            target_op_name = self.ops[target].name
            if target_op_name in ("ZEND_RETURN", "ZEND_VERIFY_RETURN_TYPE", "ZEND_EXIT", "ZEND_THROW"):
                ret_body = self.decompile_into(target, min(target + 1, len(self.ops) - 1))
                ret_body = [s for s in ret_body if isinstance(s, (php.ReturnStmt, php.ExitExpr, php.ThrowStmt))]
                if ret_body:
                    self.ctx.emit(i, ret_body[0])
                    return i + 1
            # Check if any outside instruction jumps into [target, i].
            # If so, wrapping in while(true) causes fatal PHP error:
            # "'goto' into loop or switch statement is disallowed"
            has_outside_jump = any(
                t in range(target, i + 1)
                for other_i, other_op in enumerate(self.ops)
                if (other_i < target or other_i > i)
                for t in (other_op.jump_targets or [])
            )
            if not has_outside_jump:
                # Back edge without conditional: while(true)-style loop tail.
                sink = self.ctx.current_sink()
                body: list[php.Stmt] = []
                while sink and sink[-1][0] >= target:
                    body.insert(0, sink.pop()[1])
                if body:
                    # A genuine while(true) loop body must contain an exit condition (break, return, throw, exit).
                    def _contains_exit(stmts):
                        for s in stmts:
                            if isinstance(s, (php.BreakStmt, php.ReturnStmt, php.ThrowStmt)):
                                return True
                            if isinstance(s, php.ExprStmt) and isinstance(s.expr, php.ExitExpr):
                                return True
                            if isinstance(s, php.IfStmt):
                                if _contains_exit(s.then) or _contains_exit(s.orelse or []):
                                    return True
                        return False

                    if _contains_exit(body):
                        self.ctx.emit(i, php.WhileStmt(cond=php.Literal(True), body=body))
                    else:
                        # Spurious backward jump: restore body linearly into sink
                        for s in body:
                            self.ctx.current_sink().append((target, s))
                return i + 1
            self._emit_goto(i, op, target)
            return i + 1
        self._emit_goto(i, op, target)
        return i + 1

    def _emit_goto(self, i: int, op: Opcode, target: int) -> None:
        """Render an unstructurable forward jump as ``goto label_<target>;``.

        ionCube preserves source-level ``goto`` (e.g. early-exit to a shared end
        label), which PHP compiles to a plain JMP. Forward targets are reached
        by the walker afterwards, so the label is placed when we get there. A
        rare backward target (already walked, no label) falls back to a comment.
        """
        if target > i:
            self.ctx.goto_targets.add(target)
            self.ctx.emit(i, php.GotoStmt(label=f"label_{target}"))
        else:
            self.ctx.emit(i, php.OpcodeComment(i, op.name, f"jump to {target}"))

    def _bottom_tested_while(self, i: int, end: int, cond_start: int) -> int | None:
        """Structure `JMP -> Lcond; body; Lcond: cond; J(N)Z -> body_start`."""
        body_start = i + 1
        cond_jump = None
        for c in range(cond_start, end + 1):
            candidate = self.ops[c]
            if candidate.name in _LOOP_COND_JUMPS and candidate.jump_targets and \
                    candidate.jump_targets[0] == body_start:
                cond_jump = candidate
                break
            if candidate.name in ("ZEND_JMPZ_EX", "ZEND_JMPNZ_EX"):
                continue  # short-circuit inside the condition; keep scanning
            if candidate.jump_targets and candidate.jump_targets[0] < cond_start:
                break  # some other backward jump: not our pattern
        if cond_jump is None:
            return None
        c = cond_jump.index

        def decompile_condition() -> php.Expr:
            """Run the condition ops; side-effect statements go to the current
            sink, the branch value is consumed from temps."""
            if c - 1 >= cond_start:
                self.decompile_range(cond_start, c - 1)
            cond = self.ctx.resolve(cond_jump.op1, cond_jump)
            if cond_jump.name == "ZEND_JMPZ":
                cond = php.UnaryOp(op="!", operand=cond)
            return cond

        # Prime the condition once before the loop (covers conditions with
        # side effects like `while ($row = $res->fetch_assoc())`).
        self.ctx.push_sink()
        cond_expr = decompile_condition()
        priming = self.ctx.pop_sink_tagged()
        for tagged in priming:
            self.ctx.current_sink().append((i, tagged[1]))

        self.ctx.loop_stack.append(
            LoopInfo(break_targets={c + 1}, continue_targets={cond_start})
        )
        self.ctx.push_sink()
        self.decompile_range(body_start, cond_start - 1)
        if priming:
            # Re-evaluate the condition at the end of the body so the loop
            # variable advances; discard the duplicate branch expression.
            decompile_condition()
        body = self.ctx.pop_sink()
        self.ctx.loop_stack.pop()

        self.ctx.emit(i, php.WhileStmt(cond=cond_expr, body=body))
        return c + 1

    # -- short-circuit && / || -------------------------------------------------

    def _short_circuit(self, i: int, end: int, op: Opcode) -> int:
        target = op.jump_targets[0] if op.jump_targets else None
        left = self.ctx.resolve(op.op1, op)
        result_key = op.result.temp_key
        if target is None or target <= i or target > end + 1 or result_key is None:
            self.ctx.emit(i, php.OpcodeComment(i, op.name, "unsupported short-circuit shape"))
            return i + 1

        # Evaluate the right-hand side range; it stores into the same slot.
        self.ctx.push_sink()
        self.decompile_range(i + 1, target - 1)
        spilled = self.ctx.pop_sink()
        for stmt in spilled:
            # Side-effect statements inside a condition (rare): keep them
            # before the condition rather than dropping them.
            self.ctx.current_sink().append((i, stmt))

        right = self.ctx.temps.pop(result_key, None)
        if right is None:
            self.ctx.warn(f"op {i}: {op.name} rhs did not produce t{result_key}")
            right = php.TempVar(result_key)
        if isinstance(right, php.Cast) and right.type == "bool":
            right = right.operand
        if isinstance(left, php.Cast) and left.type == "bool":
            left = left.operand

        operator = "&&" if op.name == "ZEND_JMPZ_EX" else "||"
        self.ctx.temps[result_key] = php.BinaryOp(op=operator, left=left, right=right)
        return target

    def _jmp_set(self, i: int, end: int, op: Opcode) -> int:
        # `a ?: b` / `a ?? b`: op1 value jumps over the else computation.
        target = op.jump_targets[0] if op.jump_targets else None
        if (
            target is not None
            and target <= i + 1
            and i + 1 < len(self.ops)
            and self.ops[i + 1].name == "ZEND_QM_ASSIGN"
        ):
            target = i + 2
        left = self.ctx.resolve(op.op1, op)
        result_key = op.result.temp_key
        if target is None or target <= i or target > end + 1 or result_key is None:
            self.ctx.emit(i, php.OpcodeComment(i, op.name, "unsupported shape"))
            return i + 1
        self.ctx.push_sink()
        self.decompile_range(i + 1, target - 1)
        for stmt in self.ctx.pop_sink():
            self.ctx.current_sink().append((i, stmt))
        right = self.ctx.temps.pop(result_key, php.TempVar(result_key))
        if op.name == "ZEND_COALESCE":
            self.ctx.temps[result_key] = php.BinaryOp(op="??", left=left, right=right)
        else:
            self.ctx.temps[result_key] = php.Ternary(cond=left, if_true=None, if_false=right)
        return target

    def _jmp_null(self, i: int, end: int, op: Opcode) -> int:
        target = op.jump_targets[0] if op.jump_targets else (
            op.op2.constant if op.op2.constant is not None else None
        )
        if target is not None and target < len(self.ops) and self.ops[target].name in (
            "ZEND_DO_FCALL", "ZEND_DO_FCALL_BY_NAME", "ZEND_DO_ICALL", "ZEND_DO_UCALL"
        ):
            end_target = target + 1
        elif target is not None:
            end_target = target
        else:
            end_target = i + 1

        result_key = op.result.temp_key
        if end_target <= i or end_target > len(self.ops):
            self.ctx.emit(i, php.OpcodeComment(i, op.name, "unsupported shape"))
            return i + 1

        self.ctx.push_sink()
        self.decompile_range(i + 1, end_target - 1)
        for stmt in self.ctx.pop_sink():
            self.ctx.current_sink().append((i, stmt))

        if result_key is not None:
            expr = self.ctx.temps.get(result_key)
            if isinstance(expr, (php.MethodCall, php.PropertyFetch)):
                expr.nullsafe = True
        return end_target

    # -- foreach ----------------------------------------------------------------

    def _foreach(self, i: int, end: int, op: Opcode) -> int:
        iterable = self.ctx.resolve(op.op1, op)
        iter_key = op.result.temp_key
        reset_done = op.jump_targets[0] if op.jump_targets else None

        fetch_index = i + 1
        while fetch_index <= end and self.ops[fetch_index].name == "ZEND_NOP":
            fetch_index += 1
        fetch = self.ops[fetch_index] if fetch_index <= end else None
        if fetch is None or fetch.name not in ("ZEND_FE_FETCH_R", "ZEND_FE_FETCH_RW"):
            self.ctx.emit(i, php.OpcodeComment(i, op.name, "FE_RESET without FE_FETCH"))
            return i + 1
        if iter_key is not None:
            # The fetch consumes the iterator temp; drop it so it is not
            # reported as a leak.
            self.ctx.temps.pop(iter_key, None)

        done = fetch.fe_fetch_done_opline
        if done is None:
            done = next((t for t in fetch.jump_targets), None)
        if done is None:
            done = reset_done
        if done is None or done <= fetch_index or done > end + 1:
            self.ctx.emit(i, php.OpcodeComment(i, op.name, "cannot locate loop end"))
            return i + 1

        body_start = fetch_index + 1
        body_end = done - 1
        if body_end >= body_start and self._jmp_target(body_end) == fetch_index:
            body_end -= 1

        value_var: php.Expr
        if fetch.op2.is_cv:
            value_var = php.Variable(self.ctx.cv_name(fetch.op2))
        else:
            value_var, body_start = self._foreach_loop_var(
                fetch.op2, body_start, body_end, "_value"
            )
        key_var = None
        if not fetch.result.is_unused:
            if fetch.result.is_cv:
                key_var = php.Variable(self.ctx.cv_name(fetch.result))
            elif fetch.result.is_temporary:
                key_var, body_start = self._foreach_loop_var(
                    fetch.result, body_start, body_end, "_key"
                )

        self.ctx.loop_stack.append(
            LoopInfo(break_targets={done, done + 1}, continue_targets={fetch_index})
        )
        body = self.decompile_into(body_start, body_end)
        self.ctx.loop_stack.pop()

        self.ctx.emit(
            i,
            php.ForeachStmt(
                iterable=iterable,
                value_var=value_var,
                key_var=key_var,
                by_ref=fetch.name == "ZEND_FE_FETCH_RW",
                body=body,
            ),
        )
        # Resume after the loop; skip a trailing FE_FREE.
        resume = done
        if resume <= end and self.ops[resume].name == "ZEND_FE_FREE":
            resume += 1
        return resume

    def _foreach_loop_var(
        self, operand, body_start: int, body_end: int, fallback: str
    ) -> tuple[php.Expr, int]:
        """Older encoders deliver the foreach key/value in a temp and emit
        ``ASSIGN $cv = temp`` as the first body opcode -- fold that into the
        foreach header."""
        if body_start <= body_end:
            first = self.ops[body_start]
            if (
                first.name == "ZEND_ASSIGN"
                and first.op1.is_cv
                and first.op2.is_temporary
                and (
                    operand.temp_key is None
                    or first.op2.temp_key == operand.temp_key
                )
            ):
                return php.Variable(self.ctx.cv_name(first.op1)), body_start + 1
        self.ctx.warn(f"foreach loop variable in temp slot; using ${fallback}")
        if operand.temp_key is not None:
            self.ctx.temps[operand.temp_key] = php.Variable(fallback)
        return php.Variable(fallback), body_start

    # -- switch ------------------------------------------------------------------

    def _starts_case_chain(self, i: int, end: int) -> bool:
        """A bare CASE (no preceding SWITCH opcode) that begins a dispatch."""
        return (
            i + 1 <= end
            and self.ops[i + 1].name in ("ZEND_JMPNZ", "ZEND_JMPZ")
            and bool(self.ops[i + 1].jump_targets)
        )

    def _switch(self, i: int, end: int, op: Opcode) -> int:
        """Rebuild a PHP `switch` from the CASE/JMPNZ dispatch chain.

        PHP 8.1 emits, for `switch ($x) { case A: ...; case B: ...; }`::

            SWITCH_STRING|SWITCH_LONG $x, <jump-table>
            CASE $x == A -> t ; JMPNZ t -> bodyA
            CASE $x == B -> t ; JMPNZ t -> bodyB
            JMP -> default|end
            bodyA: ... ; bodyB: ...
            FREE $x                                       (switch end)

        The CASE/JMPNZ chain is the normal source of body targets. ionCube can
        leave those targets one opcode late while the jump table still holds
        correct byte offsets. When its opcode stride can be inferred uniquely,
        the table repairs the chain without assuming an ABI-specific size.
        """
        subject_key = op.op1.temp_key
        subject = self.ctx.resolve(op.op1, op)

        scan = i + 1 if op.name in ("ZEND_SWITCH_STRING", "ZEND_SWITCH_LONG") else i
        raw_pairs: list[tuple[php.Expr, object, int]] = []
        default_target: int | None = None
        j = scan
        while j <= end:
            cur = self.ops[j]
            if cur.name in ("ZEND_CASE", "ZEND_CASE_STRICT"):
                nxt = self.ops[j + 1] if j + 1 <= end else None
                if nxt is not None and nxt.name in ("ZEND_JMPNZ", "ZEND_JMPZ") and nxt.jump_targets:
                    raw_label = cur.op2.const_value() if cur.op2.is_const else None
                    label = (
                        literal_to_expr(raw_label)
                        if cur.op2.is_const
                        else self.ctx.resolve(cur.op2, cur)
                    )
                    raw_pairs.append((label, raw_label, nxt.jump_targets[0]))
                    j += 2
                    continue
                break
            if cur.name == "ZEND_JMP" and cur.jump_targets:
                default_target = cur.jump_targets[0]
                j += 1
                break
            break
        dispatch_end = j

        if not raw_pairs:
            self.ctx.emit(i, php.OpcodeComment(i, op.name, "unstructured switch"))
            return i + 1

        pairs = [(label, target) for label, _, target in raw_pairs]
        switch_end = self._find_subject_free(subject_key, dispatch_end, end)
        if switch_end is None:
            switch_end = self._infer_switch_end(pairs, default_target, dispatch_end, end)

        table_targets = self._switch_table_targets(
            i, op, raw_pairs, dispatch_end, switch_end
        )
        if table_targets is not None:
            pairs = [
                (label, target)
                for (label, _, _), target in zip(raw_pairs, table_targets)
            ]

        entries: list[tuple[php.Expr | None, int]] = list(pairs)
        if (
            default_target is not None
            and dispatch_end <= default_target < switch_end
        ):
            entries.append((None, default_target))
        entries.sort(key=lambda entry: entry[1])

        self.ctx.loop_stack.append(
            LoopInfo(break_targets={switch_end}, continue_targets=set())
        )
        cases: list[php.SwitchCase] = []
        for idx, (label, target) in enumerate(entries):
            body_end = entries[idx + 1][1] - 1 if idx + 1 < len(entries) else switch_end - 1
            body = self.decompile_into(target, body_end)
            cases.append(php.SwitchCase(test=label, body=body))
        self.ctx.loop_stack.pop()

        self.ctx.emit(i, php.SwitchStmt(subject=subject, cases=cases))

        resume = switch_end
        if resume <= end and self.ops[resume].name in ("ZEND_FREE", "ZEND_FE_FREE"):
            if subject_key is None or self.ops[resume].op1.temp_key == subject_key:
                resume += 1
        return resume

    def _switch_table_targets(
        self,
        switch_index: int,
        op: Opcode,
        pairs: list[tuple[php.Expr, object, int]],
        body_start: int,
        switch_end: int,
    ) -> list[int] | None:
        table = op.op2.const_value() if op.op2.is_const else None
        if not isinstance(table, dict) or switch_end <= body_start:
            return None

        offsets: list[int] = []
        fallback_targets: list[int] = []
        for _, raw_label, fallback in pairs:
            offset = table.get(raw_label) if isinstance(raw_label, (int, str)) else None
            if offset is None and isinstance(raw_label, int):
                offset = table.get(str(raw_label))
            if not isinstance(offset, int) or isinstance(offset, bool) or offset <= 0:
                return None
            offsets.append(offset)
            fallback_targets.append(fallback)

        possible_strides: set[int] | None = None
        for offset in offsets:
            local_strides = {
                offset // (target - switch_index)
                for target in range(body_start, switch_end)
                if target > switch_index and offset % (target - switch_index) == 0
            }
            local_strides.discard(0)
            possible_strides = (
                local_strides
                if possible_strides is None
                else possible_strides & local_strides
            )
            if not possible_strides:
                return None

        ranked: list[tuple[int, int, list[int]]] = []
        for stride in possible_strides or ():
            targets = [
                switch_index + offset // stride
                for offset in offsets
            ]
            if targets != sorted(targets):
                continue
            score = sum(
                abs(target - fallback)
                for target, fallback in zip(targets, fallback_targets)
            )
            ranked.append((score, stride, targets))

        ranked.sort(key=lambda item: (item[0], item[1]))
        if not ranked or (len(ranked) > 1 and ranked[0][0] == ranked[1][0]):
            return None
        return ranked[0][2]

    def _find_subject_free(self, subject_key: int | None, start: int, end: int) -> int | None:
        if subject_key is None:
            return None
        for k in range(start, end + 1):
            cur = self.ops[k]
            if cur.name in ("ZEND_FREE", "ZEND_FE_FREE") and cur.op1.temp_key == subject_key:
                return k
        return None

    def _infer_switch_end(
        self,
        pairs: list[tuple[php.Expr, int]],
        default_target: int | None,
        dispatch_end: int,
        end: int,
    ) -> int:
        """End of a CV-subject switch (no FREE): the common break target, i.e.
        the furthest-forward JMP out of the case-body region."""
        targets = [t for _, t in pairs]
        if default_target is not None:
            targets.append(default_target)
        body_start = min(targets) if targets else dispatch_end
        candidate: int | None = None
        for k in range(body_start, end + 1):
            cur = self.ops[k]
            if cur.name == "ZEND_JMP" and cur.jump_targets and cur.jump_targets[0] > k:
                tgt = cur.jump_targets[0]
                candidate = tgt if candidate is None else max(candidate, tgt)
        if candidate is not None:
            return candidate
        return (max(targets) + 1) if targets else dispatch_end

    # -- try / catch -------------------------------------------------------------

    def _try_catch_at(self, i: int, end: int) -> int | None:
        entry = next(
            (
                e
                for e in self.ctx.op_array.try_catch
                if e.try_op == i
                and e.catch_op is not None
                and i < e.catch_op <= end
                and id(e) not in self._active_try_catches
                and e.catch_op < len(self.ops)
                and self.ops[e.catch_op].name == "ZEND_CATCH"
            ),
            None,
        )
        if entry is None or entry.catch_op is None:
            return None

        catch_op_index = entry.catch_op
        try_end = catch_op_index - 1
        after = None
        if self._jmp_target(try_end) is not None and (self._jmp_target(try_end) or 0) > catch_op_index:
            after = self._jmp_target(try_end)
            try_end -= 1

        self._active_try_catches.add(id(entry))
        try:
            try_body = self.decompile_into(i, try_end)
            catch_op = self.ops[catch_op_index]
            class_name = catch_op.op1.const_value() if catch_op.op1.is_const else None
            var_name = (
                self.ctx.cv_name(catch_op.result) if catch_op.result.is_cv else None
            )
            catch_end = (after - 1) if after is not None else end
            catch_body = self.decompile_into(catch_op_index + 1, catch_end)
        finally:
            self._active_try_catches.remove(id(entry))

        self.ctx.emit(
            i,
            php.TryStmt(
                body=try_body,
                catches=[
                    php.CatchClause(
                        class_names=[class_name if isinstance(class_name, str) else "Exception"],
                        var_name=var_name,
                        body=catch_body,
                    )
                ],
            ),
        )
        return after if after is not None else end + 1

    # -- helpers -------------------------------------------------------------------

    def _jmp_target(self, index: int) -> int | None:
        if 0 <= index < len(self.ops):
            op = self.ops[index]
            if op.name == "ZEND_JMP" and op.jump_targets:
                return op.jump_targets[0]
        return None


def _describe(op: Opcode) -> str:
    parts = []
    for label, operand in (("op1", op.op1), ("op2", op.op2), ("result", op.result)):
        if not operand.is_unused:
            parts.append(f"{label}={operand.kind.value}:{operand.var}")
    if op.extended_value:
        parts.append(f"ext={op.extended_value}")
    return " ".join(parts)


def decompile_body(op_array: OpArray, program=None) -> tuple[list[php.Stmt], DecompileContext]:
    """Decompile one op_array body; returns statements + the final context."""
    ctx = DecompileContext(op_array, program)
    stmts = RangeDecompiler(ctx).run()
    return stmts, ctx
