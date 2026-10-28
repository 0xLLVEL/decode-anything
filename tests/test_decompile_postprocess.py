"""Regression tests for source-level post-processing preserving valid PHP."""

from decompile import clean_php_source


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
