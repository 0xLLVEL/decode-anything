"""Static decode of a PHP 7.2 ionCube body - everything the artifact carries.

The opcode byte is the one field not present in the file: it is `stored ^ mask`,
and the mask is built by the loader from material this sample keeps inside the
license-key segment. Every other field is byte exact against a runtime dump:

    word cursor, cell count, class byte, line number, aux descriptors,
    literal table    397/397 operands agree with the loader

So this decodes the 96% that is real and marks the 4% that is not, instead of
inventing opcodes. Pass `--truth <runtime dump.json>` to annotate each slot with
the opcode the loader actually produced.

    python tools/ic72_static_dump.py scratch_body72.bin --record 2
    python tools/ic72_static_dump.py scratch_body72.bin --truth scratch/bp72.opcodes.json
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from tools.ic72_op_walk import ARG_COUNT, NAMES, walk_record
from tools.ic72_record_walk import resync


def load_truth(path):
    table = {}
    for entry in json.loads(Path(path).read_text(encoding="utf-8"))["op_arrays"].values():
        name = entry.get("function_name")
        name = name.get("value") if isinstance(name, dict) else name
        table[name] = [op["opcode"] for op in entry["opcodes"]]
    return table


def operand_text(slot, kind, node, literals):
    if kind == "CONST" and literals and 1 <= node <= len(literals):
        text = literals[node - 1].text
        return "CONST(%d)=%r" % (node, text)
    return "%s(%d)" % (kind, node)


def main(argv):
    body = Path(argv[1] if len(argv) > 1 else "scratch_body72.bin").read_bytes()
    mask_path = argv[argv.index("--mask") + 1] if "--mask" in argv else None
    masks = {}
    if mask_path:
        masks = {
            k: bytes.fromhex(v)
            for k, v in json.loads(Path(mask_path).read_text(encoding="utf-8")).items()
        }
    want = int(argv[argv.index("--record") + 1]) if "--record" in argv else None
    truth = load_truth(argv[argv.index("--truth") + 1]) if "--truth" in argv else {}

    for index, record in enumerate(resync(body, 4)):
        if index == 0 or (want is not None and index != want):
            continue
        payload = body[record.payload_offset : record.payload_offset + record.payload_size]
        walked = walk_record(payload, ARG_COUNT[index])
        opcodes = truth.get(record.name)
        print("=" * 92)
        print(
            "record #%d  %s  ops=%d cells=%d  cursor=%d/%d aux=%d/%d"
            % (
                index,
                record.name,
                walked["ops"],
                walked["cells"],
                walked["word_cursor"],
                walked["cells"],
                walked["aux_consumed"],
                15 * walked["ops"],
            )
        )
        if opcodes and len(opcodes) != walked["ops"]:
            print("  ground truth has %d opcodes - mismatched, ignoring" % len(opcodes))
            opcodes = None
        print("=" * 92)

        for entry in walked["entries"]:
            slot = entry["index"]
            op = opcodes[slot] if opcodes else None
            if op is None and record.name in masks and slot < len(masks[record.name]):
                op = entry["opcode"] ^ masks[record.name][slot]
            label = "stored=0x%02X op=%3d" % (entry["opcode"], op) if op is not None else "stored=0x%02X op=  ?" % entry["opcode"]
            cells = " ".join(
                operand_text(s, k, n, record.literals) for s, k, n in entry["operands"]
            )
            print("  %03d  %-16s class=%-3s line=%-4d %s" % (slot, label, entry["class"], entry["line"], cells))
        print()


if __name__ == "__main__":
    main(sys.argv)
