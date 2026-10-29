#!/usr/bin/env python3
"""
sg_lzo1x.py — standalone LZO1X-1 decompressor.

Ported from SourceGuardian's loader decompressor (ixed.8.1.win, sub_100088E0),
which implements the standard minilzo LZO1X state machine. See section 05 of
"SourceGuardian PHP 8.1 — Static Container & Bytecode Recovery Without
Execution" (https://www.amariei.org/sourceguardian-php81-static-decode.html)
for the full write-up.

No SourceGuardian-specific logic lives here — this is the public LZO1X
algorithm (M.F. Oberhumer), useful on its own for any LZO1X stream.
"""


def lzo1x_decompress(src: bytes) -> bytes:
    src = bytes(src)
    if not src:
        return b""
    ip = 0
    out = bytearray()

    def literal(n: int):
        nonlocal ip
        out.extend(src[ip:ip + n])
        ip += n

    def copy_match(m: int, count: int):
        for _ in range(count):
            out.append(out[m])
            m += 1

    state = 'top'
    t = src[ip]
    if t > 17:
        ip += 1
        t -= 17
        literal(t)
        state = 'flr' if t >= 4 else 'match'
        if state == 'match':
            t = src[ip]
            ip += 1

    while True:
        if state == 'top':
            t = src[ip]
            ip += 1
            if t >= 16:
                state = 'match'
                continue
            if t == 0:
                while src[ip] == 0:
                    t += 255
                    ip += 1
                t += 15 + src[ip]
                ip += 1
            literal(t + 3)
            state = 'flr'

        elif state == 'flr':
            t = src[ip]
            ip += 1
            if t >= 16:
                state = 'match'
                continue
            d = 0x0801 + (t >> 2) + (src[ip] << 2)
            ip += 1
            m = len(out) - d
            out.append(out[m])
            out.append(out[m + 1])
            out.append(out[m + 2])
            state = 'mdone'

        elif state == 'match':
            if t >= 64:
                d = 1 + ((t >> 2) & 7) + (src[ip] << 3)
                ip += 1
                count = (t >> 5) - 1
            elif t >= 32:
                count = t & 31
                if count == 0:
                    while src[ip] == 0:
                        count += 255
                        ip += 1
                    count += 31 + src[ip]
                    ip += 1
                d = 1 + (src[ip] >> 2) + (src[ip + 1] << 6)
                ip += 2
            else:
                h = (t & 8) << 11
                count = t & 7
                if count == 0:
                    while src[ip] == 0:
                        count += 255
                        ip += 1
                    count += 7 + src[ip]
                    ip += 1
                d = h + (src[ip] >> 2) + (src[ip + 1] << 6)
                ip += 2
                if d == 0:
                    break  # zero distance == end of stream
                d += 0x4000
            m = len(out) - d
            out.append(out[m])
            out.append(out[m + 1])
            copy_match(m + 2, count)
            state = 'mdone'

        elif state == 'mdone':
            trailing = src[ip - 2] & 3
            if trailing == 0:
                state = 'top'
            else:
                literal(trailing)
                t = src[ip]
                ip += 1
                state = 'match'

    return bytes(out)


if __name__ == '__main__':
    import sys
    if len(sys.argv) != 3:
        print('usage: python sg_lzo1x.py <in.lzo1x> <out.bin>', file=sys.stderr)
        sys.exit(1)
    data = open(sys.argv[1], 'rb').read()
    open(sys.argv[2], 'wb').write(lzo1x_decompress(data))
