"""Read the loader's function map from .pdata.

IDA round trips are slow and the 300 s decompile ceiling bites.  The PE already
carries every function extent in the exception directory, so this reads it
directly: 12-byte RUNTIME_FUNCTION records of (begin RVA, end RVA, unwind RVA).

    python tools/ic72_loader_map.py loader/ioncube_loader_win_7.2.dll
    python tools/ic72_loader_map.py loader/ioncube_loader_win_7.2.dll --at 0x18009DFE0
    python tools/ic72_loader_map.py loader/ioncube_loader_win_7.2.dll --range 0x18009D000 0x18009E000
    python tools/ic72_loader_map.py loader/ioncube_loader_win_7.2.dll --largest 20
"""

import argparse
import struct
import sys


class Image:
    def __init__(self, path):
        self.data = open(path, "rb").read()
        e_lfanew = struct.unpack_from("<I", self.data, 0x3C)[0]
        coff = e_lfanew + 4
        nsec, = struct.unpack_from("<H", self.data, coff + 2)
        optsize, = struct.unpack_from("<H", self.data, coff + 16)
        opt = coff + 20
        magic, = struct.unpack_from("<H", self.data, opt)
        wide = magic == 0x20B
        self.base = struct.unpack_from("<Q" if wide else "<I", self.data, opt + (24 if wide else 28))[0]
        self.sections = []
        for i in range(nsec):
            o = opt + optsize + i * 40
            name = self.data[o:o + 8].rstrip(b"\0").decode("ascii", "replace")
            vsize, vaddr, rawsize, rawptr = struct.unpack_from("<IIII", self.data, o + 8)
            self.sections.append((name, vaddr, vsize, rawptr, rawsize))

    def section(self, name):
        for entry in self.sections:
            if entry[0] == name:
                return entry
        raise KeyError(name)

    def functions(self):
        _name, vaddr, _vsize, rawptr, rawsize = self.section(".pdata")
        out = []
        for i in range(rawsize // 12):
            begin, end, _unwind = struct.unpack_from("<III", self.data, rawptr + i * 12)
            if begin:
                out.append((self.base + begin, self.base + end))
        return sorted(out)


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("binary")
    ap.add_argument("--at", type=lambda s: int(s, 0), help="function containing this address")
    ap.add_argument("--range", nargs=2, type=lambda s: int(s, 0), metavar=("LO", "HI"))
    ap.add_argument("--largest", type=int, default=0, help="print the N largest functions")
    args = ap.parse_args()

    image = Image(args.binary)
    funcs = image.functions()
    print("%d functions from .pdata" % len(funcs))

    if args.at is not None:
        for begin, end in funcs:
            if begin <= args.at < end:
                print("containing  %#x .. %#x  (%d bytes)" % (begin, end, end - begin))
                return 0
        print("no function contains %#x" % args.at)
        return 1

    if args.range:
        lo, hi = args.range
        for begin, end in funcs:
            if lo <= begin < hi:
                print("%#x .. %#x  %6d" % (begin, end, end - begin))
        return 0

    if args.largest:
        for begin, end in sorted(funcs, key=lambda f: f[0] - f[1])[:args.largest]:
            print("%#x  %6d bytes" % (begin, end - begin))
        return 0

    for begin, end in funcs:
        print("%#x .. %#x  %6d" % (begin, end, end - begin))
    return 0


if __name__ == "__main__":
    sys.exit(main())
