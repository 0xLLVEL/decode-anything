"""Regression tests for source-level post-processing preserving valid PHP."""

from pathlib import Path

import pytest

from decompile import (
    _invert_condition,
    _invert_empty_if_guards,
    clean_php_source,
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


def test_empty_control_flow_keywords_are_all_rejected():
    cases = {
        "if": "if ($x) {\n}\n",
        "elseif": "if ($x) {\n    foo();\n} elseif ($y) {\n}\n",
        "else": "if ($x) {\n    foo();\n} else {\n}\n",
        "for": "for ($i = 0; $i < 1; $i++) {\n}\n",
        "foreach": "foreach ($xs as $x) {\n}\n",
        "while": "while ($x) {\n}\n",
        "do": "do {\n} while ($x);\n",
        "switch": "switch ($x) {\n}\n",
    }

    for keyword, body in cases.items():
        ok, message = validate_php_structure("<?php\n" + body)
        assert ok is False, keyword
        assert f"empty {keyword} body" in message, keyword


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
