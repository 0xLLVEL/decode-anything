# Brute force the 32-bit seed behind the ionCube 7.2 opcode mask.
#
# Model recovered from the 32-bit loader (see docs/ioncube-72-static.md M4.4):
#
#   lcg0 = 69069*S + 1234567
#   xs0  = C applied (S % 9) + 1 times, C(x): x^=x<<10; x^=x>>15; x^=x<<4; x^=x>>13
#   fn   = A if (S & 1) else B
#   A(x): x^=x<<13; x^=x>>17; x^=x<<5
#   B(x): x^=x>>9;  x^=x*2;   x^=x>>7
#   step: lcg = 69069*lcg + 123; xs = fn(xs); value = lcg + xs
#
# The mask stores one byte per opcode. Try every lane and every seed.
#
#   powershell -File tools\ic72_seed_brute.ps1

param(
    [string]$Mask = "00 97 0b c4 2c 80 d1 f6",
    [int]$Lane = -1
)

$source = @'
using System;
using System.Diagnostics;

public static class Ic72Seed
{
    static uint C(uint x)
    {
        x ^= x << 10; x ^= x >> 15; x ^= x << 4; x ^= x >> 13;
        return x;
    }
    static uint A(uint x)
    {
        x ^= x << 13; x ^= x >> 17; x ^= x << 5;
        return x;
    }
    static uint B(uint x)
    {
        x ^= x >> 9; x ^= x << 1; x ^= x >> 7;
        return x;
    }

    public static string Run(byte[] target, int lane)
    {
        int n = target.Length;
        uint[] lcg = new uint[n];
        uint[] xs = new uint[n];
        for (uint seed = 0; seed < 0xFFFFFFFFu; seed++)
        {
            uint l = 69069u * seed + 1234567u;
            uint x = seed;
            int rounds = (int)(seed % 9u) + 1;
            for (int r = 0; r < rounds; r++) x = C(x);
            bool variantA = (seed & 1) != 0;
            bool ok = true;
            for (int i = 0; i < n; i++)
            {
                l = 69069u * l + 123u;
                x = variantA ? A(x) : B(x);
                uint v = l + x;
                byte b = lane < 0 ? (byte)(v & 0xFF) : (byte)((v >> (lane * 8)) & 0xFF);
                if (b != target[i]) { ok = false; break; }
            }
            if (ok) return "FOUND seed=0x" + seed.ToString("X8") + " lane=" + lane;
        }
        return null;
    }
}
'@

Add-Type -TypeDefinition $source -Language CSharp

if ($Lane -ge 0) { $lanes = @($Lane) } else { $lanes = @(0, 1, 2, 3) }
$bytes = [byte[]]($Mask.Split(' ') | ForEach-Object { [Convert]::ToByte($_, 16) })

foreach ($l in $lanes) {
    $sw = [Diagnostics.Stopwatch]::StartNew()
    $r = [Ic72Seed]::Run($bytes, $l)
    $sw.Stop()
    if ($r) {
        Write-Output "$r  ($([math]::Round($sw.Elapsed.TotalSeconds,1))s)"
    } else {
        Write-Output "lane $l : no seed in 2^32 ($([math]::Round($sw.Elapsed.TotalSeconds,1))s)"
    }
}
