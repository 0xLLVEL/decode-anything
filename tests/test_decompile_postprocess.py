"""Regression tests for source-level post-processing preserving valid PHP."""

from pathlib import Path

import pytest

from decompile import (
    _invert_condition,
    _invert_empty_if_guards,
    _normalize_psr4_namespaces,
    clean_php_source,
    ir_declares_strict_types,
    validate_php_structure,
)

FIXTURES = Path(__file__).parent / "fixtures" / "postprocess"


def test_double_bang_inside_strings_and_comments_is_preserved():
    result = clean_php_source(
        '<?php\n$a = "hello!!";\n$b = \'world!!\';\n// keep !!\n'
    )

    assert '"hello!!"' in result
    assert "'world!!'" in result
    assert "// keep !!" in result


def test_return_after_block_is_not_removed():
    result = clean_php_source(
        """<?php
function f($x) {
    if ($x) {
        foo();
    }
    return;
    bar();
}
"""
    )

    assert "\n    return;\n    bar();\n" in result


def test_return_null_after_block_is_not_removed():
    result = clean_php_source(
        """<?php
function f($x) {
    if ($x) {
        foo();
    }
    return null;
    bar();
}
"""
    )

    assert "\n    return null;\n    bar();\n" in result


def test_top_level_return_null_keeps_previous_function_return_type_out():
    result = clean_php_source(
        """<?php
function f(): array {
    return [];
}
$x = 1;
return null;
"""
    )

    assert "\nreturn null;\n" in result


def test_declared_class_name_is_not_split_into_namespace():
    result = clean_php_source(
        r"""<?php
class SpondonIt\Service\SpondonItServiceProvider extends Illuminate\Support\ServiceProvider {
    public function register(): void {}
}
"""
    )

    assert r"namespace SpondonIt\Service;" in result
    assert r"class SpondonItServiceProvider extends ServiceProvider" in result
    assert "class Provider" not in result
    assert r"Spondon\It\Service\Provider" not in result


@pytest.mark.parametrize(
    ("code", "expected"),
    [
        ("new AppXMLParser();", r"new App\XML\Parser();"),
        ("new AppURL();", r"new App\URL();"),
        ("new AppDB();", r"new App\DB();"),
        ("new AppHttpClient();", r"new App\Http\Client();"),
        ("new AppUserRepository();", r"new App\User\Repository();"),
    ],
)
def test_acronym_class_names_split_into_whole_words(code, expected):
    assert _normalize_psr4_namespaces(code, namespace="App") == expected


def test_declared_acronym_class_name_is_not_split():
    code = "class AppXMLParser {}"

    result = _normalize_psr4_namespaces(
        code, namespace="App", declared_classes={"AppXMLParser"}
    )

    assert result == code


def test_empty_if_with_nested_parentheses_is_removed():
    result = clean_php_source(
        "<?php\nif (!str_contains($response, 'poster: \"')) {\n}\nfoo();\n"
    )

    assert "if (" not in result
    assert validate_php_structure(result) == (True, "")


def test_goto_that_is_the_only_branch_statement_is_preserved():
    result = clean_php_source(
        """<?php
function f($x) {
    if ($x) {
        goto label_5;
        label_5:
    }
}
"""
    )

    assert "goto label_5;" in result
    assert validate_php_structure(result) == (True, "")


def test_empty_control_flow_body_is_rejected():
    ok, message = validate_php_structure("<?php\nif ($x) {\n}\n")

    assert ok is False
    assert message == "line 2: empty if body"


def test_empty_branch_bodies_are_rejected():
    cases = {
        "if": "if ($x) {\n}\n",
        "elseif": "if ($x) {\n    foo();\n} elseif ($y) {\n}\n",
        "else": "if ($x) {\n    foo();\n} else {\n}\n",
        "switch": "switch ($x) {\n}\n",
    }

    for keyword, body in cases.items():
        ok, message = validate_php_structure("<?php\n" + body)
        assert ok is False, keyword
        assert f"empty {keyword} body" in message, keyword


def test_empty_loop_bodies_are_valid_php():
    cases = (
        "for ($i = 0; $i < 1; $i++) {\n}\n",
        "foreach ($xs as $x) {\n}\n",
        "while ($x) {\n}\n",
        "do {\n} while ($x);\n",
    )

    for body in cases:
        assert validate_php_structure("<?php\n" + body) == (True, ""), body


def test_empty_loop_with_side_effect_in_condition_is_preserved():
    result = clean_php_source(
        "<?php\n"
        "while (($row = $stmt->fetch()) !== false) {\n"
        "}\n"
        "do {\n"
        "} while (($line = fgets($fh)) !== false);\n"
    )

    assert "while (($row = $stmt->fetch()) !== false) {" in result
    assert "do {" in result
    assert "} while (($line = fgets($fh)) !== false);" in result


def test_control_flow_bodies_in_strings_and_comments_are_ignored():
    code = """<?php
if ($x) {
    echo 'if ($y) {}';
}
$message = "foreach ($xs as $x) {}";
// while ($x) {}
"""

    assert validate_php_structure(code) == (True, "")


def test_empty_method_bodies_are_not_control_flow():
    code = "<?php\nclass A {\n    public function noop(): void {}\n}\n"

    assert validate_php_structure(code) == (True, "")


@pytest.mark.parametrize(
    ("condition", "expected"),
    [
        ("$x", "!$x"),
        ("!$x", "$x"),
        ("!($a && $b)", "$a && $b"),
        ("!$a && $b", "$a || !$b"),
        ("$a >= 1 && $b < 2", "$a < 1 || $b >= 2"),
        ("$a || $b", "!$a && !$b"),
        ("$a && $b || $c", "(!$a || !$b) && !$c"),
        ("$x === null", "$x !== null"),
        ("!empty($x)", "empty($x)"),
        ("!foo($a, $b)", "foo($a, $b)"),
        ("$a instanceof Foo", "!($a instanceof Foo)"),
        ('$x === "a&&b"', '$x !== "a&&b"'),
        ("$a <=> $b", "!($a <=> $b)"),
    ],
)
def test_invert_condition_negates_without_changing_meaning(condition, expected):
    assert _invert_condition(condition) == expected


def test_unresolved_variable_is_not_replaced_with_server_superglobal():
    result = clean_php_source('<?php\n$x = ${None}["HTTP_HOST"];\n')

    assert "$_SERVER" not in result
    assert "${None}" in result.replace("\n", "")


def test_null_concat_is_not_rewritten_to_dir_constant():
    result = clean_php_source("<?php\n$p = null . '/../config.php';\n")

    assert "__DIR__" not in result
    assert "null . '/../config.php'" in result


def test_null_array_key_is_not_dropped():
    result = clean_php_source("<?php\n$a = [null => $v];\n")

    assert "[null => $v]" in result


def test_global_classes_used_in_namespaced_code_get_imported():
    result = clean_php_source(
        "<?php\nnamespace SpondonIt\\Service\\Middleware;\n\n"
        "class Guard\n{\n"
        "    public function handle($request, Closure $next)\n    {\n"
        "        try {\n            return $next($request);\n"
        "        } catch (Exception $e) {\n            throw $e;\n        }\n"
        "    }\n}\n"
    )

    assert "use Closure;" in result
    assert "use Exception;" in result


def test_global_classes_are_not_imported_without_a_namespace():
    result = clean_php_source("<?php\nfunction f(Closure $next) {}\n")

    assert "use Closure;" not in result


def test_locally_declared_exception_is_not_shadowed_by_a_global_import():
    result = clean_php_source(
        "<?php\nnamespace App\\Support;\n\n"
        "class Exception extends \\RuntimeException {}\n\n"
        "function f() {\n    try {\n        foo();\n    } catch (Exception $e) {\n        throw $e;\n    }\n}\n"
    )

    assert "use Exception;" not in result
    assert "class Exception extends" in result


def test_strict_types_declare_is_inserted_before_namespace_and_imports():
    result = clean_php_source(
        "<?php\nnamespace App\\Http;\n\nclass Foo\n{\n"
        "    public function bar(Closure $next) {}\n}\n",
        strict_types=True,
    )

    normalized = result.replace("\r\n", "\n")
    assert "<?php\n\ndeclare(strict_types=1);\n\nnamespace App\\Http;\n" in normalized
    assert normalized.index("declare(strict_types=1);") < normalized.index("use Closure;")


def test_strict_types_declare_is_inserted_without_a_namespace():
    result = clean_php_source("<?php\n$value = 1;\n", strict_types=True)

    assert result.replace("\r\n", "\n").startswith(
        "<?php\n\ndeclare(strict_types=1);\n"
    )


def test_strict_types_declare_precedes_imports_in_a_namespace_less_file():
    result = clean_php_source(
        "<?php\n\nclass Foo\n{\n    public function bar()\n    {\n"
        "        return Illuminate\\Support\\Facades\\Log::info('x');\n"
        "    }\n}\n",
        strict_types=True,
    )

    normalized = result.replace("\r\n", "\n")
    assert normalized.startswith("<?php\n\ndeclare(strict_types=1);\n")
    assert normalized.index("declare(strict_types=1);") < normalized.index(
        "use Illuminate\\Support\\Facades\\Log;"
    )


def test_strict_types_declare_is_not_added_to_non_strict_files():
    result = clean_php_source("<?php\nnamespace App;\n\nclass Foo {}\n")

    assert "declare(strict_types=1);" not in result


def test_strict_types_flag_is_read_from_the_main_op_array():
    assert ir_declares_strict_types(
        {"op_arrays": {"main": {"strict_types": True}, "function:61": {}}}
    )
    assert not ir_declares_strict_types(
        {"op_arrays": {"main": {"strict_types": False}}}
    )
    assert not ir_declares_strict_types({"op_arrays": {}})
    assert not ir_declares_strict_types({"op_arrays": []})


def test_existing_strict_types_declare_is_not_duplicated():
    result = clean_php_source(
        "<?php\ndeclare(strict_types=1);\n\nnamespace App;\n\nclass Foo {}\n",
        strict_types=True,
    )

    assert result.count("declare(strict_types=1);") == 1


def test_parent_calls_are_not_rewritten_to_self():
    result = clean_php_source(
        "<?php\nclass A {\n"
        "    public function __construct() {\n"
        "        parent::__construct();\n"
        "    }\n}"
    )

    assert "parent::__construct();" in result


def test_unstructured_catch_uses_throwable_instead_of_exception():
    result = clean_php_source(
        "<?php\nfunction f() {\n"
        "    $a = 1;\n"
        "    goto label_5;\n"
        "    /* [opcode 42] ZEND_CATCH unstructured catch */\n"
        "    echo 'caught';\n"
        "    label_5:\n"
        "    return 1;\n}\n"
    )

    assert "catch (\\Throwable $e) {" in result
    assert "catch (\\Exception" not in result


def test_leaked_compiler_temps_keep_their_assignments_and_identity():
    result = clean_php_source(
        "<?php\n$a = $tmp3;\n$b = $tmp4;\nfoo($a, $b);\n"
    )

    assert "$a = $tmp3;" in result
    assert "$b = $tmp4;" in result
    assert "temp resolved" not in result
    assert "$tempVal" not in result


def test_empty_guard_with_compound_condition_inverts_every_term():
    code = (
        "<?php\n"
        "function f($a, $b) {\n"
        "    while (true) {\n"
        "        if (!$a && $b) {\n"
        "        }\n"
        "        continue;\n"
        "    }\n"
        "}\n"
    )

    result = _invert_empty_if_guards(code)

    assert "if ($a || !$b) {" in result
    assert "continue;" in result


def test_loop_exit_guards_become_structured_breaks():
    result = clean_php_source(
        (FIXTURES / "loop_exit_guards.php").read_text(encoding="utf-8")
    )
    normalized = result.replace("\r\n", "\n")

    assert "goto " not in normalized
    assert normalized.count("break;") == 3
    assert "$__exit_guard_20 = true;\n            break;" in normalized
    assert "if (empty($__exit_guard_20)) {\n        echo 'after';\n    }" in normalized
    assert "$fn = function (bool $skip) use ($items) {" in normalized
    assert "        return true;\n    };" in normalized
    assert validate_php_structure(result) == (True, "")
