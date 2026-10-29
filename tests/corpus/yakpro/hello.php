<?php
/*
    |  Obfuscated by YAK Pro - Php Obfuscator  2.0.17  |
    |    GitHub: https://github.com/pk-fr/yakpro-po    |
*/

goto entry;
step2:
$b = "\x32\x30";
goto step3;
entry:
$a = "\x31\x30";
goto step2;
step3:
$total = $a + $b;
if (!($total > 10)) {
    goto deny;
}
goto allow;
allow:
$status = "\x6f\x6b";
goto done;
deny:
$status = "\x6e\x6f";
goto done;
done:
echo "total=" . $total . ";status=" . $status;
