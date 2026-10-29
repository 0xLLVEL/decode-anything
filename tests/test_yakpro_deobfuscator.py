"""Tests for YAK Pro Static Deobfuscator."""

import shutil
import subprocess
import pytest
from yakpro_deobfuscator import (
    is_yakpro_obfuscated,
    clean_strings,
    strip_outer_negation,
    deobfuscate_yakpro,
)


def test_is_yakpro_obfuscated():
    header_sample = "<?php\n// Obfuscated by YAK Pro - Php Obfuscator 2.0.14\ngoto abc;\n"
    assert is_yakpro_obfuscated(header_sample) is True

    heuristic_sample = '<?php\ngoto L1; L1: $x = "\\x61"; goto L2; L2: $y = "\\x62"; goto L3; L3: goto L4; L4: goto L5; L5: return;'
    assert is_yakpro_obfuscated(heuristic_sample) is True

    plain_php = "<?php\necho 'hello world';\n$x = 10;\n"
    assert is_yakpro_obfuscated(plain_php) is False


def test_clean_strings():
    # Hex escape
    code_hex = '$msg = "\\x48\\x65\\x6c\\x6c\\x6f\\x20\\x57\\x6f\\x72\\x6c\\x64";'
    cleaned = clean_strings(code_hex)
    assert cleaned == '$msg = "Hello World";'

    # Octal escape
    code_oct = '$str = "\\101\\102\\103";'
    cleaned_oct = clean_strings(code_oct)
    assert cleaned_oct == '$str = "ABC";'

    # Interpolated string with variable preserved
    code_interp = '$greeting = "Hello $name\\x21";'
    cleaned_interp = clean_strings(code_interp)
    assert "$name" in cleaned_interp


def test_strip_outer_negation():
    # Simple negation
    expr, stripped = strip_outer_negation("!($a == 1)")
    assert stripped is True
    assert expr == "$a == 1"

    # Chained constructor call: outer parens around `new Class()` must not break
    expr, stripped = strip_outer_negation("!((new SystemInfo())->isRunningInContainer())")
    assert stripped is True
    assert expr == "(new SystemInfo())->isRunningInContainer()"

    # Non-negated expression
    expr, stripped = strip_outer_negation("$x > 10")
    assert stripped is False
    assert expr == "$x > 10"


def test_deobfuscate_linear_goto_chain():
    obf = """<?php
// Obfuscated by YAK Pro
goto entry;
step2:
$b = 20;
goto step3;
entry:
$a = 10;
goto step2;
step3:
$c = $a + $b;
return $c;
"""
    result = deobfuscate_yakpro(obf)
    assert "goto" not in result
    assert "$a = 10;" in result
    assert "$b = 20;" in result
    assert "$c = $a + $b;" in result
    # Order must be linear: $a before $b before $c
    pos_a = result.index("$a = 10;")
    pos_b = result.index("$b = 20;")
    pos_c = result.index("$c = $a + $b;")
    assert pos_a < pos_b < pos_c


def test_deobfuscate_inverted_if_else():
    obf = """<?php
// Obfuscated by YAK Pro
goto entry;
if_then:
$status = 'allowed';
goto done;
if_else:
$status = 'denied';
goto done;
entry:
if (!($is_admin)) {
    goto if_else;
}
goto if_then;
done:
return $status;
"""
    result = deobfuscate_yakpro(obf)
    assert "goto" not in result
    assert "if ($is_admin) {" in result
    assert "$status = 'allowed';" in result
    assert "else {" in result
    assert "$status = 'denied';" in result


def test_deobfuscate_loop():
    obf = """<?php
// Obfuscated by YAK Pro
goto entry;
loop_body:
$sum += $val;
goto loop_end;
entry:
$sum = 0;
foreach ($items as $val) {
    goto loop_body;
    loop_end:
}
goto finish;
finish:
return $sum;
"""
    result = deobfuscate_yakpro(obf)
    assert "goto" not in result
    assert "foreach ($items as $val) {" in result
    assert "$sum += $val;" in result


def test_deobfuscate_try_catch():
    obf = """<?php
// Obfuscated by YAK Pro
goto entry;
try_body:
$res = do_risky();
goto end_try;
catch_body:
$res = null;
goto after;
entry:
try {
    goto try_body;
    end_try:
} catch (\\Exception $e) {
    goto catch_body;
}
goto after;
after:
return $res;
"""
    result = deobfuscate_yakpro(obf)
    assert "goto" not in result
    assert "try {" in result
    assert "$res = do_risky();" in result
    assert "catch (\\Exception $e) {" in result
    assert "$res = null;" in result


@pytest.mark.skipif(shutil.which("php") is None, reason="PHP CLI not available")
def test_syntax_validity_with_php_cli():
    obf = """<?php
// Obfuscated by YAK Pro - Php Obfuscator 2.0.14
goto start;
block_2:
$msg = "\\x48\\x65\\x6c\\x6c\\x6f";
goto block_3;
start:
$x = 42;
if (!($x > 0)) {
    goto block_3;
}
goto block_2;
block_3:
echo $msg ?? "\\x64\\x65\\x66\\x61\\x75\\x6c\\x74";
"""
    clean = deobfuscate_yakpro(obf)
    proc = subprocess.run(
        ["php", "-l"],
        input=clean,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    assert proc.returncode == 0, f"PHP syntax error: {proc.stdout} {proc.stderr}"


def test_deobfuscate_class_methods():
    obf = """<?php
class Calculator {
    private int $factor = 2;

    public function multiply(int $a, int $b): int {
        goto calc;
        ret:
        return $res;
        calc:
        $res = $a * $b * $this->factor;
        goto ret;
    }

    public function status(): string {
        return "ready";
    }
}
"""
    clean = deobfuscate_yakpro(obf)
    assert "goto" not in clean
    assert "class Calculator {" in clean
    assert "private int $factor = 2;" in clean
    assert "public function multiply(int $a, int $b): int {" in clean
    assert "$res = $a * $b * $this->factor;" in clean
    assert "return $res;" in clean
    assert 'return "ready";' in clean

