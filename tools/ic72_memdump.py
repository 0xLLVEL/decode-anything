"""Dump decoded ionCube 7.x buffers straight out of the PHP process.

The encoded script is included behind a shutdown hook that sleeps, so the
loader's decoded buffers stay resident while we read the target's memory from
outside.  Every committed private region is scanned for the needle and the
containing regions are written to disk for offline analysis.
"""

from __future__ import annotations

import argparse
import ctypes
import ctypes.wintypes as wt
import json
import subprocess
import sys
import tempfile
import time
from pathlib import Path

kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)

PROCESS_QUERY_INFORMATION = 0x0400
PROCESS_VM_READ = 0x0010
MEM_COMMIT = 0x1000
PAGE_GUARD = 0x100
PAGE_NOACCESS = 0x01


class MEMORY_BASIC_INFORMATION64(ctypes.Structure):
    _fields_ = [
        ("BaseAddress", ctypes.c_uint64),
        ("AllocationBase", ctypes.c_uint64),
        ("AllocationProtect", wt.DWORD),
        ("__alignment1", wt.DWORD),
        ("RegionSize", ctypes.c_uint64),
        ("State", wt.DWORD),
        ("Protect", wt.DWORD),
        ("Type", wt.DWORD),
        ("__alignment2", wt.DWORD),
    ]


kernel32.OpenProcess.argtypes = [wt.DWORD, wt.BOOL, wt.DWORD]
kernel32.OpenProcess.restype = wt.HANDLE
kernel32.ReadProcessMemory.argtypes = [
    wt.HANDLE,
    ctypes.c_void_p,
    ctypes.c_void_p,
    ctypes.c_size_t,
    ctypes.POINTER(ctypes.c_size_t),
]
kernel32.VirtualQueryEx.argtypes = [
    wt.HANDLE,
    ctypes.c_void_p,
    ctypes.POINTER(MEMORY_BASIC_INFORMATION64),
    ctypes.c_size_t,
]
kernel32.VirtualQueryEx.restype = ctypes.c_size_t
kernel32.TerminateProcess.argtypes = [wt.HANDLE, wt.UINT]


def read_memory(process: int, address: int, size: int) -> bytes:
    buffer = ctypes.create_string_buffer(size)
    read = ctypes.c_size_t()
    ok = kernel32.ReadProcessMemory(
        process, ctypes.c_void_p(address), buffer, size, ctypes.byref(read)
    )
    if not ok:
        return b""
    return buffer.raw[: read.value]


def scan(process: int, needles: list[bytes], limit: int = 0x7FFF0000):
    info = MEMORY_BASIC_INFORMATION64()
    address = 0
    while address < limit:
        if not kernel32.VirtualQueryEx(
            process, ctypes.c_void_p(address), ctypes.byref(info), ctypes.sizeof(info)
        ):
            break
        size = info.RegionSize
        if (
            info.State == MEM_COMMIT
            and not (info.Protect & PAGE_GUARD)
            and info.Protect != PAGE_NOACCESS
            and 0 < size <= 0x4000000
        ):
            data = read_memory(process, address, size)
            for needle in needles:
                start = 0
                while True:
                    index = data.find(needle, start)
                    if index < 0:
                        break
                    yield address + index, needle, info.BaseAddress, info.RegionSize
                    start = index + 1
        address += size or 0x1000


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--php", required=True, type=Path)
    parser.add_argument("--loader", required=True, type=Path)
    parser.add_argument("--target", required=True, type=Path)
    parser.add_argument("--needle", action="append", default=[])
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--sleep", type=int, default=25)
    parser.add_argument("--delay", type=float, default=1.5)
    parser.add_argument("--max-regions", type=int, default=8)
    args = parser.parse_args()

    work = Path(tempfile.mkdtemp(prefix="ic72mem-"))
    ini = work / "php.ini"
    ini.write_text(
        "[PHP]\r\nerror_reporting = 0\r\ndisplay_errors = 0\r\n"
        f'zend_extension = "{args.loader.resolve()}"\r\n',
        encoding="utf-8",
    )
    wrapper = work / "wrapper.php"
    wrapper.write_text(
        "<?php\n"
        f"register_shutdown_function(function () {{ sleep({args.sleep}); }});\n"
        "include $argv[1];\n",
        encoding="utf-8",
    )

    proc = subprocess.Popen(
        [str(args.php), "-c", str(ini), str(wrapper), str(args.target.resolve())],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        cwd=str(args.php.resolve().parent),
    )
    time.sleep(args.delay)
    handle = kernel32.OpenProcess(
        PROCESS_QUERY_INFORMATION | PROCESS_VM_READ, False, proc.pid
    )
    if not handle:
        proc.kill()
        raise SystemExit(f"OpenProcess failed: {ctypes.get_last_error()}")

    needles = [n.encode() for n in args.needle] or [b"Restricted Access"]
    args.out.mkdir(parents=True, exist_ok=True)
    saved: list[dict[str, object]] = []
    try:
        for address, needle, region_base, region_size in scan(int(handle), needles):
            region = read_memory(int(handle), region_base, region_size)
            target = args.out / f"region_{region_base:08x}.bin"
            if not target.exists():
                target.write_bytes(region)
                saved.append(
                    {
                        "region": hex(region_base),
                        "size": region_size,
                        "file": target.name,
                        "hits": [],
                    }
                )
            entry = next((s for s in saved if s["region"] == hex(region_base)), None)
            if entry is not None:
                entry["hits"].append(  # type: ignore[union-attr]
                    {"needle": needle.decode(), "offset": address - region_base}
                )
            if len(saved) >= args.max_regions:
                break
    finally:
        kernel32.TerminateProcess(int(handle), 1)
        proc.wait(timeout=10)

    (args.out / "index.json").write_text(json.dumps(saved, indent=2), encoding="utf-8")
    print(json.dumps(saved, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
