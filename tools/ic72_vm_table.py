"""Dump the ionCube 7.2 opcode spec array and handler table.

The loader builds zend-style op arrays and executes them through its own
handler table.  sub_18006F1A0 is the equivalent of zend_vm_get_opcode_handler:
it reads a 32-bit spec word per opcode, folds in the op's type bytes, and
returns handler_table[specialisation_offset + (spec & 0xffff)].

    spec word   = flags << 16 | base
    flags bit   -> extra index dimension
      0x01  op1_type        index from type_map[op+29]
      0x02  op2_type        index from type_map[op+30]
      0x04  result_type     index from type_map[op+61]
      0x08  result_type != 8                 (2 slots)
      0x10  op2.value < 12                   (2 slots)
      0x20  op2.value == 43 / == 44          (3 slots)
      0x40  op1.value == 147 / == 136        (3 slots)

Because every dimension is a fixed multiplier, each opcode owns a contiguous
run of slots.  Those runs tile the handler table, which is the check this
tool performs.
"""

import argparse
import struct
import sys


SPEC_ARRAY = 0x1800A8D70
TYPE_MAP = 0x1800A91E0
HANDLER_TABLE = 0x1800DA650

OPCODE_INDEX = 220          # measured bound, see spec_length()
UNIMPLEMENTED = 0xFFFFFFFF
DIMENSIONS = (
    (0x01, 5, "op1_type"),
    (0x02, 5, "op2_type"),
    (0x04, 5, "result_type"),
    (0x08, 2, "result_type!=8"),
    (0x10, 2, "op2.value<12"),
    (0x20, 3, "op2.value==43/44"),
    (0x40, 3, "op1.value==147/136"),
)

TEXT_RANGE = (0x180001000, 0x1800A8000)


class Image:
    def __init__(self, path):
        self.data = open(path, "rb").read()
        e_lfanew = struct.unpack_from("<I", self.data, 0x3C)[0]
        coff = e_lfanew + 4
        nsec, = struct.unpack_from("<H", self.data, coff + 2)
        optsize, = struct.unpack_from("<H", self.data, coff + 16)
        opt = coff + 20
        magic, = struct.unpack_from("<H", self.data, opt)
        base_off = 24 if magic == 0x20B else 28
        self.base = struct.unpack_from("<Q" if magic == 0x20B else "<I", self.data, opt + base_off)[0]
        self.sections = []
        for i in range(nsec):
            o = opt + optsize + i * 40
            name = self.data[o:o + 8].rstrip(b"\0").decode("ascii", "replace")
            vsize, vaddr, rawsize, rawptr = struct.unpack_from("<IIII", self.data, o + 8)
            self.sections.append((name, vaddr, vsize, rawptr, rawsize))

    def offset(self, va):
        rva = va - self.base
        for _name, vaddr, vsize, rawptr, rawsize in self.sections:
            if vaddr <= rva < vaddr + max(vsize, rawsize):
                return rawptr + (rva - vaddr)
        raise ValueError("unmapped address %#x" % va)

    def u32s(self, va, count):
        return struct.unpack("<%dI" % count, self.data[self.offset(va):self.offset(va) + 4 * count])

    def qwords(self, va, count):
        return struct.unpack("<%dQ" % count, self.data[self.offset(va):self.offset(va) + 8 * count])


def slots(flags):
    total = 1
    for bit, factor, _name in DIMENSIONS:
        if flags & bit:
            total *= factor
    return total


def flag_names(flags):
    return [name for bit, _factor, name in DIMENSIONS if flags & bit]


def spec_length(image):
    """The spec array ends where the byte ramp 00 01 02 03 starts."""
    words = image.u32s(SPEC_ARRAY, 256)
    for i, word in enumerate(words):
        if word == 0x03020100:
            return i
    return 256


def handler_run(image):
    """Length of the leading pointer run that stays inside .text."""
    probe = 8192
    raw = image.qwords(HANDLER_TABLE, probe)
    count = 0
    for value in raw:
        if TEXT_RANGE[0] <= value < TEXT_RANGE[1]:
            count += 1
        else:
            break
    return count


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("binary", help="ioncube_loader_win_7.2.dll")
    ap.add_argument("--opcode", type=int, help="print one spec entry in detail")
    ap.add_argument("--max", type=int, default=256, help="highest opcode index to print (default 256)")
    ap.add_argument("--quiet", action="store_true", help="only print the summary")
    args = ap.parse_args()

    image = Image(args.binary)
    length = spec_length(image)
    spec = image.u32s(SPEC_ARRAY, length)
    type_map = image.u32s(TYPE_MAP, OPCODE_INDEX)
    run = handler_run(image)

    live = [i for i, word in enumerate(spec) if word and word != UNIMPLEMENTED]
    print("image base      %#x" % image.base)
    print("spec array      %#x   %d entries, %d implemented" % (SPEC_ARRAY, length, len(live)))
    print("type map        %#x   %d distinct type bytes" % (TYPE_MAP, len(set(type_map[:32]))))
    print("handler table   %#x   %d entries before the first non-.text word" % (HANDLER_TABLE, run))

    tiled = 0
    end = None
    for i in range(1, length):
        word = spec[i]
        if not word or word == UNIMPLEMENTED:
            break
        base = word & 0xFFFF
        if end is not None and base != end:
            break
        end = base + slots(word >> 16)
        tiled += 1
    print("tiling          opcodes 1..%d are contiguous, ending at slot %d" % (tiled, end))

    if args.opcode is not None:
        i = args.opcode
        word = spec[i]
        print()
        if word in (0, UNIMPLEMENTED):
            print("opcode %d  %s" % (i, "unused" if word == 0 else "marked unimplemented (%#x)" % word))
        else:
            print("opcode %d  spec %#010x  base %d  flags %#06x  slots %d"
                  % (i, word, word & 0xFFFF, word >> 16, slots(word >> 16)))
            print("  dimensions    %s" % ", ".join(flag_names(word >> 16) or ["none"]))
        print("  type_map[0..7] %s" % (type_map[:8],))

    if args.quiet:
        return

    print()
    print("idx   spec        base  slots  flags  dimensions")
    for i in range(min(args.max, length)):
        word = spec[i]
        if word == 0:
            print("%3d   -            -     -      -      unused" % i)
            continue
        if word == UNIMPLEMENTED:
            print("%3d   %#010x  -     -      -      unimplemented" % (i, word))
            continue
        flags = word >> 16
        print("%3d   %#010x  %5d  %5d  %#06x  %s"
              % (i, word, word & 0xFFFF, slots(flags), flags, ", ".join(flag_names(flags)) or "none"))


if __name__ == "__main__":
    sys.exit(main())
