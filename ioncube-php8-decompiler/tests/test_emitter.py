"""Milestone 5: PHP emitter and AST optimizer."""

from php_reconstructor import ast as php
from php_reconstructor.decompiler.optimize import optimize
from php_reconstructor.emitter import PhpEmitter, emit_php
from php_reconstructor.utils.php_values import PhpBytes


def render_expr(expr: php.Expr) -> str:
    return PhpEmitter()._expr(expr)


class TestLiterals:
    def test_scalars(self):
        assert render_expr(php.Literal(None)) == "null"
        assert render_expr(php.Literal(True)) == "true"
        assert render_expr(php.Literal(False)) == "false"
        assert render_expr(php.Literal(42)) == "42"
        assert render_expr(php.Literal("abc")) == "'abc'"

    def test_string_escaping(self):
        assert render_expr(php.Literal("don't")) == "'don\\'t'"
        assert render_expr(php.Literal("a\\b")) == "'a\\\\b'"

    def test_binary_string_double_quoted(self):
        rendered = render_expr(php.Literal(PhpBytes(b"\x00abc")))
        assert rendered == '"\\x00abc"'


class TestPrecedence:
    def test_mul_inside_add_no_parens(self):
        expr = php.BinaryOp(op="+", left=php.Variable("a"),
                            right=php.BinaryOp(op="*", left=php.Variable("b"), right=php.Variable("c")))
        assert render_expr(expr) == "$a + $b * $c"

    def test_add_inside_mul_needs_parens(self):
        expr = php.BinaryOp(op="*", left=php.BinaryOp(op="+", left=php.Variable("a"), right=php.Variable("b")),
                            right=php.Variable("c"))
        assert render_expr(expr) == "($a + $b) * $c"

    def test_left_assoc_subtraction(self):
        # a - (b - c) must keep parens.
        expr = php.BinaryOp(op="-", left=php.Variable("a"),
                            right=php.BinaryOp(op="-", left=php.Variable("b"), right=php.Variable("c")))
        assert render_expr(expr) == "$a - ($b - $c)"

    def test_concat_chain_no_parens(self):
        expr = php.BinaryOp(op=".", left=php.Variable("a"),
                            right=php.BinaryOp(op=".", left=php.Variable("b"), right=php.Variable("c")))
        assert render_expr(expr) == "$a . $b . $c"

    def test_or_inside_and_parenthesized(self):
        expr = php.BinaryOp(op="&&",
                            left=php.BinaryOp(op="||", left=php.Variable("a"), right=php.Variable("b")),
                            right=php.Variable("c"))
        assert render_expr(expr) == "($a || $b) && $c"


class TestStatements:
    def test_if_else_layout(self):
        stmt = php.IfStmt(
            cond=php.Variable("c"),
            then=[php.EchoStmt(exprs=[php.Literal("y")])],
            orelse=[php.EchoStmt(exprs=[php.Literal("n")])],
        )
        text = emit_php(php.PhpFile(statements=[stmt]))
        assert "if ($c) {\n    echo 'y';\n} else {\n    echo 'n';\n}" in text

    def test_deterministic_output(self):
        node = php.PhpFile(statements=[
            php.ExprStmt(php.Assign(target=php.Variable("a"), value=php.Literal(1)))
        ])
        assert emit_php(node) == emit_php(node)


class TestOptimizer:
    def test_bool_cast_stripped_in_condition(self):
        stmt = php.IfStmt(cond=php.Cast(type="bool", operand=php.Variable("x")), then=[])
        optimized = optimize(php.PhpFile(statements=[stmt]))
        assert isinstance(optimized.statements[0].cond, php.Variable)

    def test_not_comparison_inverted(self):
        expr = php.UnaryOp(op="!", operand=php.BinaryOp(op="==", left=php.Variable("a"), right=php.Literal(1)))
        stmt = php.IfStmt(cond=expr, then=[])
        optimized = optimize(php.PhpFile(statements=[stmt]))
        cond = optimized.statements[0].cond
        assert isinstance(cond, php.BinaryOp)
        assert cond.op == "!="

    def test_double_negation_removed(self):
        expr = php.UnaryOp(op="!", operand=php.UnaryOp(op="!", operand=php.Variable("a")))
        stmt = php.IfStmt(cond=expr, then=[])
        optimized = optimize(php.PhpFile(statements=[stmt]))
        assert isinstance(optimized.statements[0].cond, php.Variable)

    def test_empty_then_flipped(self):
        stmt = php.IfStmt(cond=php.Variable("c"), then=[],
                          orelse=[php.EchoStmt(exprs=[php.Literal("x")])])
        optimized = optimize(php.PhpFile(statements=[stmt]))
        result = optimized.statements[0]
        assert result.then and not result.orelse
        assert isinstance(result.cond, php.UnaryOp)

    def test_else_if_collapsed_to_elseif(self):
        inner = php.IfStmt(cond=php.Variable("b"), then=[php.EchoStmt(exprs=[php.Literal("2")])])
        outer = php.IfStmt(cond=php.Variable("a"), then=[php.EchoStmt(exprs=[php.Literal("1")])],
                           orelse=[inner])
        text = emit_php(optimize(php.PhpFile(statements=[outer])))
        assert "} elseif ($b) {" in text


class TestAstDump:
    def test_to_dict_round(self):
        stmt = php.ExprStmt(php.Assign(target=php.Variable("a"), value=php.Literal(1)))
        data = php.PhpFile(statements=[stmt]).to_dict()
        assert data["node"] == "PhpFile"
        assert data["statements"][0]["node"] == "ExprStmt"
        assert data["statements"][0]["expr"]["node"] == "Assign"
