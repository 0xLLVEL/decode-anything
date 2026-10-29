"""
ioncube_loader_extractor.py

Standalone — runs directly on ioncube_loader_win_X.Y.dll, no IDA Pro needed.

Usage:
    python ioncube_loader_extractor.py ioncube_loader_win_8.1.dll
    python ioncube_loader_extractor.py ioncube_loader_win_8.2.dll
    python ioncube_loader_extractor.py ioncube_loader_win_8.3.dll
    python ioncube_loader_extractor.py ioncube_loader_win_8.4.dll

Extracts the shared container constants used by decode_hrc_header.py and
prints the body-profile fields that still require loader-specific analysis.
No external dependencies — uses only the Python standard library.
"""

import sys
import struct
import re
from pathlib import Path


# ─── minimal PE parser ────────────────────────────────────────────────────────

class PESection:
    def __init__(self, name, vaddr, raw_offset, raw_size, data):
        self.name       = name
        self.vaddr      = vaddr      # RVA
        self.raw_offset = raw_offset
        self.raw_size   = raw_size
        self.data       = data       # bytes of the section


class PE:
    def __init__(self, path):
        self.raw  = Path(path).read_bytes()
        self.base = 0
        self.sections: list[PESection] = []
        self._parse()

    def _u16(self, off): return struct.unpack_from("<H", self.raw, off)[0]
    def _u32(self, off): return struct.unpack_from("<I", self.raw, off)[0]

    def _parse(self):
        dos_magic = self.raw[:2]
        assert dos_magic == b"MZ", "Not a PE file"
        pe_off = self._u32(0x3C)
        assert self.raw[pe_off:pe_off+4] == b"PE\x00\x00"

        coff_off    = pe_off + 4
        num_secs    = self._u16(coff_off + 2)
        opt_hdr_sz  = self._u16(coff_off + 16)
        opt_off     = coff_off + 20

        magic = self._u16(opt_off)
        if magic == 0x10B:   # PE32
            self.base = self._u32(opt_off + 28)
        elif magic == 0x20B: # PE32+
            self.base = struct.unpack_from("<Q", self.raw, opt_off + 24)[0]
        else:
            raise ValueError(f"Unknown optional header magic: 0x{magic:04X}")

        sec_off = opt_off + opt_hdr_sz
        for i in range(num_secs):
            s = sec_off + i * 40
            raw_name   = self.raw[s:s+8].rstrip(b"\x00")
            name       = raw_name.decode("ascii", errors="replace")
            vaddr      = self._u32(s + 12)
            raw_size   = self._u32(s + 16)
            raw_offset = self._u32(s + 20)
            data       = self.raw[raw_offset: raw_offset + raw_size]
            self.sections.append(PESection(name, vaddr, raw_offset, raw_size, data))

    def section(self, name: str) -> PESection | None:
        for s in self.sections:
            if s.name == name:
                return s
        return None

    def va_to_raw(self, va: int) -> int:
        """Convert virtual address (absolute) to file offset."""
        rva = va - self.base
        for s in self.sections:
            if s.vaddr <= rva < s.vaddr + s.raw_size:
                return s.raw_offset + (rva - s.vaddr)
        raise ValueError(f"VA 0x{va:08X} not in any section")

    def read_u32_va(self, va: int) -> int:
        off = self.va_to_raw(va)
        return struct.unpack_from("<I", self.raw, off)[0]


# ─── pattern search ───────────────────────────────────────────────────────────

def scan_section(sec: PESection, pattern: bytes | str, base_va: int) -> list[int]:
    """
    Find all occurrences of pattern in section data.
    Pattern can be:
      - bytes: literal match
      - str: hex string with optional '??' wildcards, e.g. "81 F3 ?? ?? ?? ??"
    Returns list of VAs.
    """
    if isinstance(pattern, str):
        parts  = pattern.split()
        regex  = b"".join(b"." if p == "??" else bytes([int(p, 16)]) for p in parts)
        flags  = re.DOTALL
        hits   = [m.start() for m in re.finditer(regex, sec.data, flags)]
    else:
        hits = []
        start = 0
        while True:
            idx = sec.data.find(pattern, start)
            if idx == -1:
                break
            hits.append(idx)
            start = idx + 1

    return [sec.vaddr + base_va + h for h in hits]


def u32_at(sec: PESection, va: int, base_va: int) -> int:
    off = va - base_va - sec.vaddr
    return struct.unpack_from("<I", sec.data, off)[0]


def bytes_at(sec: PESection, va: int, base_va: int, n: int) -> bytes:
    off = va - base_va - sec.vaddr
    if off < 0 or off + n > len(sec.data):
        return b""
    return sec.data[off: off + n]


# ─── instruction helpers (applied to raw bytes, no IDA) ──────────────────────

def xor_reg_imm32(data: bytes, off: int):
    """If bytes at off encode 'xor <r32>, imm32', return (imm32, instr_size). Else None."""
    if off >= len(data):
        return None
    b0 = data[off]
    if b0 == 0x35 and off + 5 <= len(data):            # xor eax, imm32
        return struct.unpack_from("<I", data, off + 1)[0], 5
    if b0 == 0x81 and off + 6 <= len(data):
        modrm = data[off + 1]
        if (modrm & 0xF8) == 0xF0 and (modrm & 0xC0) == 0xC0:  # xor r32, imm32
            return struct.unpack_from("<I", data, off + 2)[0], 6
    return None


def sub_reg_imm32(data: bytes, off: int):
    """If bytes at off encode 'sub <r32>, imm32', return (imm32, instr_size). Else None."""
    if off >= len(data):
        return None
    b0 = data[off]
    if b0 == 0x2D and off + 5 <= len(data):            # sub eax, imm32
        return struct.unpack_from("<I", data, off + 1)[0], 5
    if b0 == 0x81 and off + 6 <= len(data):
        modrm = data[off + 1]
        if (modrm & 0xF8) == 0xE8 and (modrm & 0xC0) == 0xC0:  # sub r32, imm32
            return struct.unpack_from("<I", data, off + 2)[0], 6
    return None


_JCC = frozenset([
    0x70,0x71,0x72,0x73,0x74,0x75,0x76,0x77,
    0x78,0x79,0x7A,0x7B,0x7C,0x7D,0x7E,0x7F,
    0xEB,  # jmp short
])


def _skip_jcc(data: bytes, off: int) -> int:
    """If a short jcc or jmp short is at off, return next offset; else return off."""
    if off >= len(data):
        return off
    b0 = data[off]
    if b0 in _JCC:
        return off + 2
    if b0 == 0x0F and off + 1 < len(data) and (data[off+1] & 0xF0) == 0x80:
        return off + 6  # jcc near
    return off


def _modrm_extra(data: bytes, off: int) -> int:
    """Return extra bytes consumed by a ModRM byte at off (not counting opcode or ModRM itself)."""
    if off >= len(data):
        return 0
    modrm = data[off]
    mod = (modrm >> 6) & 3
    rm  = modrm & 7
    if mod == 3:
        return 0                          # register, no extra
    has_sib = (rm == 4 and mod != 3)     # SIB byte present
    if mod == 0:
        if rm == 5:
            return 4                      # disp32, no SIB
        if has_sib:
            sib = data[off + 1] if off + 1 < len(data) else 0
            if (sib & 7) == 5:            # SIB base=disp32
                return 1 + 4
            return 1                      # SIB only
        return 0
    if mod == 1:
        return (1 if has_sib else 0) + 1  # SIB? + disp8
    if mod == 2:
        return (1 if has_sib else 0) + 4  # SIB? + disp32
    return 0


def _rough_insn_size(data: bytes, off: int) -> int:
    """Instruction size estimate for forward scanning (handles ModRM/SIB correctly)."""
    if off >= len(data):
        return 1
    b0 = data[off]
    # 1-byte opcodes
    if b0 in (0x50,0x51,0x52,0x53,0x54,0x55,0x56,0x57,
               0x58,0x59,0x5A,0x5B,0x5C,0x5D,0x5E,0x5F,
               0x90, 0xC3, 0xC9, 0x99):
        return 1
    # opcode + imm8
    if b0 in (0x74,0x75,0x7C,0x7D,0x7E,0x7F,0x72,0x73,0x70,0x71,
               0x76,0x77,0x78,0x79,0x7A,0x7B, 0xEB, 0x6A):
        return 2
    # opcode + imm32
    if b0 in (0x35, 0x2D, 0x05, 0x3D, 0x25, 0x0D, 0x15, 0x1D,
               0xE8, 0xE9, 0x68, 0xA1, 0xA3, 0xB8, 0xB9, 0xBA,
               0xBB, 0xBC, 0xBD, 0xBE, 0xBF):
        return 5
    # 81 /x imm32 — opcode(1) + ModRM(1) + extra + imm32(4)
    if b0 == 0x81:
        return 2 + _modrm_extra(data, off + 1) + 4
    # 83 /x imm8
    if b0 == 0x83:
        return 2 + _modrm_extra(data, off + 1) + 1
    # 0F 8x imm32 (jcc near)
    if b0 == 0x0F:
        return 6
    # 8B/89/8D — opcode + ModRM + extras
    if b0 in (0x8B, 0x89, 0x8D, 0x85, 0x01, 0x03, 0x2B, 0x33):
        return 2 + _modrm_extra(data, off + 1)
    # add/sub/xor with imm8 via 83
    return 3  # conservative fallback


# ─── extractor functions ──────────────────────────────────────────────────────

def find_version_dispatch(text: PESection, base_va: int):
    """
    Structural pattern in .text:
        xor  ebx, VERSION_XOR      ; 81 F3 [le32]
        ...
        cmp  ebx, HRC_VER_A        ; 81 FB [le32]
        j??  ...
        cmp  ebx, HRC_VER_B
        ...
    Find the longest chain of consecutive cmp ebx (≥3).
    """
    CMP_EBX = bytes([0x81, 0xFB])
    best = None
    data = text.data

    for va in scan_section(text, "81 F3", base_va):
        off = va - base_va - text.vaddr
        xor_val = struct.unpack_from("<I", data, off + 2)[0]
        if xor_val == 0:
            continue

        versions = []
        pos  = off + 6
        slack = 128   # bytes budget for non-cmp instructions

        while slack > 0 and len(versions) < 16:
            if pos + 6 > len(data):
                break
            if data[pos:pos+2] == CMP_EBX:
                v = struct.unpack_from("<I", data, pos + 2)[0]
                if v:
                    versions.append((v, base_va + text.vaddr + pos))
                pos += 6
            else:
                # skip jcc or rough-estimate instruction size
                new_pos = _skip_jcc(data, pos)
                if new_pos == pos:
                    sz = _rough_insn_size(data, pos)
                    slack -= sz
                    pos += sz
                else:
                    slack -= (new_pos - pos)
                    pos = new_pos

        if len(versions) >= 3:
            if best is None or len(versions) > len(best["versions"]):
                best = {
                    "xor_va":     va,
                    "VERSION_XOR": xor_val,
                    "versions":   versions,
                }

    return best


def find_file_size_pair(text: PESection, base_va: int):
    """
    Find FILE_SIZE_XOR and FILE_SIZE_OFFSET.
    Looks for 'xor reg, imm32' followed within ~10 instructions by
    'sub reg, imm32' where offset ∈ [100, 80 000].
    Anchors on known bytes DE 8C 95 23 (FILE_SIZE_XOR = 0x23958CDE) when present.
    """
    results = []
    seen    = set()
    data    = text.data

    def _try(off):
        r = xor_reg_imm32(data, off)
        if not r:
            return
        xor_val, xsz = r
        if xor_val < 0x100:
            return
        pos = off + xsz
        for _ in range(12):
            if pos >= len(data):
                break
            sr = sub_reg_imm32(data, pos)
            if sr:
                offset, _ = sr
                if 100 <= offset <= 80_000:
                    k = (xor_val, offset)
                    if k not in seen:
                        seen.add(k)
                        results.append({
                            "FILE_SIZE_XOR":    xor_val,
                            "xor_va":           base_va + text.vaddr + off,
                            "FILE_SIZE_OFFSET": offset,
                            "sub_va":           base_va + text.vaddr + pos,
                        })
                break
            pos += _rough_insn_size(data, pos)

    # Primary: anchor on known XOR constant bytes (stable across known 8.x loaders)
    known_pattern = bytes([0xDE, 0x8C, 0x95, 0x23])
    start = 0
    while True:
        idx = data.find(known_pattern, start)
        if idx == -1:
            break
        # Step back 1 or 2 bytes to the opcode
        for back in (1, 2):
            if idx - back >= 0:
                _try(idx - back)
        start = idx + 1

    # Fallback: scan all xor eax, imm32 (35 xx xx xx xx)
    if not results:
        idx = 0
        while True:
            idx = data.find(b"\x35", idx)
            if idx == -1:
                break
            _try(idx)
            idx += 1

    return results


def find_header_size_pair(text: PESection, base_va: int):
    """
    Find HEADER_SIZE_XOR and HEADER_SIZE_OFFSET.
    Pattern: xor reg, HEADER_SIZE_XOR (large)
             sub reg, HEADER_SIZE_OFFSET (also large, > 0x01000000)
             xor reg, reg               (33 xx — distinguishing: XOR with another register)
    Anchors on known bytes 93 F5 4F 18 (HEADER_SIZE_XOR = 0x184FF593).
    """
    results = []
    seen    = set()
    data    = text.data

    def _try(off):
        r = xor_reg_imm32(data, off)
        if not r:
            return
        xor_val, xsz = r
        if xor_val < 0x01000000:   # must be a large constant
            return
        pos = off + xsz
        for _ in range(15):
            if pos >= len(data):
                break
            sr = sub_reg_imm32(data, pos)
            if sr:
                offset, ssz = sr
                if offset >= 0x01000000:   # HEADER_SIZE_OFFSET is also large
                    k = (xor_val, offset)
                    if k not in seen:
                        seen.add(k)
                        results.append({
                            "HEADER_SIZE_XOR":    xor_val,
                            "xor_va":             base_va + text.vaddr + off,
                            "HEADER_SIZE_OFFSET": offset,
                            "sub_va":             base_va + text.vaddr + pos,
                        })
                break
            pos += _rough_insn_size(data, pos)

    # Primary: anchor on known XOR constant bytes
    known_pattern = bytes([0x93, 0xF5, 0x4F, 0x18])
    start = 0
    while True:
        idx = data.find(known_pattern, start)
        if idx == -1:
            break
        for back in (1, 2):
            if idx - back >= 0:
                _try(idx - back)
        start = idx + 1

    # Fallback: scan all 81 F5 (xor ebp, imm32)
    if not results:
        idx = 0
        while True:
            idx = data.find(b"\x81\xf5", idx)
            if idx == -1:
                break
            _try(idx)
            idx += 1

    return results


# ─── main ─────────────────────────────────────────────────────────────────────

def main(dll_path: str):
    pe   = PE(dll_path)
    text = pe.section(".text")
    if text is None:
        print("ERROR: no .text section found")
        return

    base = pe.base
    fname = Path(dll_path).name

    print()
    print("=" * 64, flush=True)
    print(f"  IonCube Loader Extractor  (standalone, no IDA needed)")
    print(f"  File : {fname}")
    print(f"  Base : 0x{base:08X}")
    print("=" * 64, flush=True)

    # 1. version dispatch
    print("\n[1] VERSION DISPATCH")
    vd = find_version_dispatch(text, base)
    if vd:
        print(f"  VERSION_XOR  = 0x{vd['VERSION_XOR']:08X}   (@ 0x{vd['xor_va']:08X})")
        print(f"  HRC_VERSIONS = {{  # {len(vd['versions'])} entries")
        for v, va in vd["versions"]:
            print(f"    0x{v:08X},   # @ 0x{va:08X}")
        print(f"  }}")
    else:
        print("  !! NOT FOUND — verify .text has xor ebx + chain cmp ebx pattern")

    # 2. file-size constants
    print("\n[2] FILE SIZE CONSTANTS")
    fs = find_file_size_pair(text, base)
    if fs:
        r = fs[0]
        print(f"  FILE_SIZE_XOR    = 0x{r['FILE_SIZE_XOR']:08X}   (@ 0x{r['xor_va']:08X})")
        print(f"  FILE_SIZE_OFFSET = {r['FILE_SIZE_OFFSET']}   (@ 0x{r['sub_va']:08X})")
        if len(fs) > 1:
            print(f"  NOTE: {len(fs)} candidates found — verify address in IDA if uncertain")
    else:
        print("  !! NOT FOUND")

    # 3. header-size constants
    print("\n[3] HEADER SIZE CONSTANTS")
    hs = find_header_size_pair(text, base)
    if hs:
        r = hs[0]
        print(f"  HEADER_SIZE_XOR    = 0x{r['HEADER_SIZE_XOR']:08X}   (@ 0x{r['xor_va']:08X})")
        print(f"  HEADER_SIZE_OFFSET = 0x{r['HEADER_SIZE_OFFSET']:08X}   (@ 0x{r['sub_va']:08X})")
        if len(hs) > 1:
            print(f"  NOTE: {len(hs)} candidates")
    else:
        print("  !! NOT FOUND")

    # 4. body constants
    print("\n[4] BODY CONSTANTS  (need manual RE per loader — addresses differ in each binary)")
    for name in [
        "VARIANT_TABLES      ",
        "OPCODE_HANDLER_META ",
        "OPCODE_META_ID      ",
        "TYPE_DIMENSION_TABLE",
        "GLOBAL_FEATURE_WORD ",
        "STRING_XOR_KEY      ",
        "STRING_POINTER_TABLE",
    ]:
        print(f"  {name} = TODO")

    # copy-paste block
    print()
    print("-" * 64)
    print("  COPY-PASTE -> decode_hrc_header.py")
    print("-" * 64)
    if vd:
        print(f"VERSION_XOR = 0x{vd['VERSION_XOR']:08X}")
        vals = ", ".join(f"0x{v:08X}" for v, _ in vd["versions"])
        print(f"HRC_VERSIONS = {{{vals}}}")
    if fs:
        r = fs[0]
        print(f"FILE_SIZE_XOR    = 0x{r['FILE_SIZE_XOR']:08X}")
        print(f"FILE_SIZE_OFFSET = {r['FILE_SIZE_OFFSET']}")
    if hs:
        r = hs[0]
        print(f"HEADER_SIZE_XOR    = 0x{r['HEADER_SIZE_XOR']:08X}")
        print(f"HEADER_SIZE_OFFSET = 0x{r['HEADER_SIZE_OFFSET']:08X}")
    print("-" * 64)
    print()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(f"Usage: python {Path(sys.argv[0]).name} ioncube_loader_win_X.Y.dll")
        sys.exit(1)
    main(sys.argv[1])
