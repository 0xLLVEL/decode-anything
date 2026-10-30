"""`return;` and `return null;` compile to the same ZEND_RETURN; pick one spelling."""

from __future__ import annotations

import sys
from pathlib import Path

SRC = Path(__file__).resolve().parents[1] / "ioncube-php8-decompiler" / "src"
sys.path.insert(0, str(SRC))

from php_reconstructor import ast as php  # noqa: E402
from php_reconstructor.decompiler.optimize import optimize  # noqa: E402
from php_reconstructor.emitter.php_emitter import emit_php  # noqa: E402


def _emit(*statements: php.Stmt) -> str:
    return emit_php(optimize(php.PhpFile(statements=list(statements)))).replace(
        "\r\n", "\n"
    )


def _null_return() -> php.ReturnStmt:
    return php.ReturnStmt(value=php.Literal(value=None))


def _guard(x: str) -> php.IfStmt:
    return php.IfStmt(cond=php.Variable(name=x), then=[_null_return()])


def test_null_return_becomes_bare_in_a_function_that_returns_no_value():
    code = _emit(
        php.FunctionDecl(name="info", body=[_guard("safe")]),
    )

    assert "return;" in code
    assert "return null" not in code


def test_null_return_is_kept_when_the_function_returns_values():
    code = _emit(
        php.FunctionDecl(
            name="find",
            body=[_guard("id"), php.ReturnStmt(value=php.Literal(value="hit"))],
        ),
    )

    assert "return null;" in code
    assert "return;\n" not in code


def test_void_function_always_gets_bare_return():
    code = _emit(
        php.FunctionDecl(
            name="log_it",
            return_type="void",
            body=[_guard("skip"), php.ReturnStmt(value=php.Literal(value="x"))],
        ),
    )

    assert "return;" in code
    assert "return null" not in code


def test_file_scope_guard_uses_bare_return():
    code = _emit(_guard("ready"))

    assert "return;" in code
    assert "return null" not in code
