"""Brute the opcode mask chain: base_u32[i+1] = xorshift(base_u32[i]).

sub_18009CA60 reads one u32 per call through the object's step function at +24,
which sub_18009D040 sets to sub_18009D000 or sub_18009D020. Both are pure 32 bit
xorshifts. If the object feeds its own output back, the whole mask array is a
chain from a single starting u32, and the only unknown is that start.

The start is pinned by the receive opcodes: in each record the first `args`
opcodes are the same opcode, so their stored bytes XOR the same value. That gives
base_u32[0] = stored_le ^ (opcode * 0x01010101). Sweep all 198 opcodes and both
step functions, then require every later opcode to stay inside 0..0xC5.
"""

import struct
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from tools.ic72_record_walk import resync

M32 = 0xFFFFFFFF
ARG_COUNT = {1: 0, 2: 1, 3: 2, 4: 4}


def step_a(value):
    x = (value ^ (value << 13)) & M32
    x = ((x >> 17) ^ x) & M32
    return (x ^ (x << 5)) & M32


def step_b(value):
    z = (value ^ (value >> 9)) & M32
    z = (z ^ ((z << 1) & M32)) & M32
    return (z ^ (z >> 7)) & M32


STEPS = {"d000": step_a, "d020": step_b}


def stored_opcodes(payload, arg_count):
    head = 0x88 + 20 * arg_count
    ops, cells = struct.unpack_from("<2I", payload, head)
    word_base = head + 8
    words = [struct.unpack_from("<I", payload, word_base + 4 * k)[0] for k in range(cells)]
    out = []
    cursor = 0
    while cursor < cells and len(out) < ops:
        word = words[cursor]
        out.append((word & 0xFF, (word >> 8) & 0xFF))
        cursor += 1
        if ((word >> 8) & 0xFF) & 0x18 == 0x18:
            cursor += 1
    return out


def expand(start, count, step):
    words = []
    value = start
    for _ in range(count):
        words.append(value)
        value = step(value)
    return words


def key_bytes(words):
    out = bytearray()
    for value in words:
        out += struct.pack("<I", value)
    return bytes(out)


def sweep(name, entries, args):
    if args == 0:
        print("%-18s no arguments - the start is not pinned by a receive run" % name)
        return
    stored = [code for code, _ in entries]
    need = 0
    for i in range(args):
        need |= stored[i] << (8 * i)

    words_needed = (len(stored) + 3) // 4
    survivors = []
    for step_name, step in STEPS.items():
        for opcode in range(0xC6):
            target = need ^ (opcode * 0x01010101)
            mask = key_bytes(expand(target, words_needed, step))
            bad = 0
            for i, code in enumerate(stored):
                if (code ^ mask[i]) > 0xC5:
                    bad += 1
                    break
            if not bad:
                survivors.append((step_name, opcode, target))
    print("%-18s args=%d ops=%d survivors=%d" % (name, args, len(stored), len(survivors)))
    for step_name, opcode, target in survivors[:6]:
        mask = key_bytes(expand(target, words_needed, STEPS[step_name]))
        codes = [code ^ mask[i] for i, code in enumerate(stored)]
        print(
            "   %s opcode=%#04x start=%#010x  first=%s"
            % (step_name, opcode, target, " ".join("%02x" % c for c in codes[:12]))
        )
    return survivors


def main(argv):
    body = Path(argv[1] if len(argv) > 1 else "scratch_body72.bin").read_bytes()
    names = ["binancepay_config", "binancepay_link", "call_bp_proxy", "bp_call_api"]
    for i, record in enumerate(resync(body, 4)):
        if i == 0:
            continue
        payload = body[record.payload_offset : record.payload_offset + record.payload_size]
        entries = stored_opcodes(payload, ARG_COUNT[i])
        sweep(names[i - 1], entries, ARG_COUNT[i])


if __name__ == "__main__":
    main(sys.argv)
