"""Recover the real opcode mask array by joining the runtime dump to the payload.

The runtime bundle tells us the true opcode of every slot. The payload tells us
the stored byte. Their XOR is the mask array the loader built at `op_array + 64`,
one byte per opcode - the exact thing M3.16 and M3.17 could only guess at.

With ground truth in hand the mask can be tested instead of searched:

    python tools/ic72_mask_truth.py scratch_body72.bin scratch/bp72.opcodes.json
"""

import json
import struct
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from tools.ic72_record_walk import resync

M32 = 0xFFFFFFFF
ARG_COUNT = {1: 0, 2: 1, 3: 2, 4: 4}
NAMES = ["binancepay_config", "binancepay_link", "call_bp_proxy", "bp_call_api"]


def stored_bytes(payload, arg_count):
    head = 0x88 + 20 * arg_count
    ops, cells = struct.unpack_from("<2I", payload, head)
    word_base = head + 8
    words = [struct.unpack_from("<I", payload, word_base + 4 * k)[0] for k in range(cells)]
    out = []
    cursor = 0
    while cursor < cells and len(out) < ops:
        word = words[cursor]
        out.append(word & 0xFF)
        cursor += 1
        if ((word >> 8) & 0xFF) & 0x18 == 0x18:
            cursor += 1
    return out


def true_opcodes(dump):
    table = {}
    for entry in dump["op_arrays"].values():
        name = entry.get("function_name")
        if isinstance(name, dict):
            name = name.get("value")
        table[name] = [op["opcode"] for op in entry["opcodes"]]
    return table


def xorshift_a(value):
    x = (value ^ (value << 13)) & M32
    x = ((x >> 17) ^ x) & M32
    return (x ^ (x << 5)) & M32


def xorshift_b(value):
    z = (value ^ (value >> 9)) & M32
    z = (z ^ ((z << 1) & M32)) & M32
    return (z ^ (z >> 7)) & M32


def report(name, key):
    words = [struct.unpack_from("<I", key, 4 * j)[0] for j in range(len(key) // 4)]
    lcg = sum(1 for j in range(len(words) - 1) if (69069 * words[j] + 123) & M32 == words[j + 1])
    xa = sum(1 for j in range(len(words) - 1) if xorshift_a(words[j]) == words[j + 1])
    xb = sum(1 for j in range(len(words) - 1) if xorshift_b(words[j]) == words[j + 1])
    print(
        "%-18s bytes=%3d words=%2d distinct=%2d lcg=%d/%d xs_a=%d/%d xs_b=%d/%d"
        % (name, len(key), len(words), len(set(words)), lcg, len(words) - 1, xa, len(words) - 1, xb, len(words) - 1)
    )
    print("   key[0:16] = %s" % key[:16].hex(" "))
    return words


def main(argv):
    body_path = Path(argv[1] if len(argv) > 1 else "scratch_body72.bin")
    dump_path = Path(argv[2] if len(argv) > 2 else "scratch/bp72.opcodes.json")
    body = body_path.read_bytes()
    dump = json.loads(dump_path.read_text(encoding="utf-8"))
    table = true_opcodes(dump)

    for index, record in enumerate(resync(body, 4)):
        if index == 0:
            continue
        payload = body[record.payload_offset : record.payload_offset + record.payload_size]
        stored = stored_bytes(payload, ARG_COUNT[index])
        opcodes = table.get(record.name)
        if not opcodes or len(opcodes) != len(stored):
            print("%-18s no ground truth (%d vs %s)" % (record.name, len(stored), len(opcodes or [])))
            continue
        key = bytes(a ^ b for a, b in zip(stored, opcodes))
        report(record.name, key)


if __name__ == "__main__":
    main(sys.argv)
