"""Trace ionCube 7.2 cipher selection with a real WOW64 breakpoint.

Runs ``php -l`` on an encoded file under the 7.2 loader (32-bit) and stops at:

* ``0x10001C40`` — cipher factory, ``ecx`` = cipher id, ``edx`` = mode
* ``0x10001BB0`` — cipher0 init, ``[esp+8]`` input, ``[esp+0x10]`` key,
  ``[esp+0x14]`` length, ``[esp+0x18]`` output

Every hit is appended to a JSONL log.  The debugger is a 64-bit process, so
32-bit registers are read through ``Wow64GetThreadContext``.
"""

from __future__ import annotations

import argparse
import ctypes
import ctypes.wintypes as wt
import json
import struct
import sys
import tempfile
from pathlib import Path

kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
psapi = ctypes.WinDLL("psapi", use_last_error=True)
psapi.GetModuleFileNameExW.argtypes = [
    wt.HANDLE,
    wt.HMODULE,
    wt.LPWSTR,
    wt.DWORD,
]

DEBUG_ONLY_THIS_PROCESS = 0x00000002
CREATE_NO_WINDOW = 0x08000000
DBG_CONTINUE = 0x00010002
DBG_EXCEPTION_NOT_HANDLED = 0x80010001
EXCEPTION_DEBUG_EVENT = 1
CREATE_PROCESS_DEBUG_EVENT = 3
LOAD_DLL_DEBUG_EVENT = 6
EXIT_PROCESS_DEBUG_EVENT = 5
# A WOW64 target reports 32-bit #BP/#DB as 0x4000001F/0x4000001E.
BREAKPOINT_CODES = {0x80000003, 0x4000001F}
SINGLE_STEP_CODES = {0x80000004, 0x4000001E}
WOW64_CONTEXT_CONTROL = 0x00010001
WOW64_CONTEXT_INTEGER = 0x00010002
WOW64_CONTEXT_SEGMENTS = 0x00010004
WOW64_CONTEXT_ALL = WOW64_CONTEXT_CONTROL | WOW64_CONTEXT_INTEGER | WOW64_CONTEXT_SEGMENTS
WOW64_CONTEXT_SIZE = 0x2CC
PAGE_EXECUTE_READWRITE = 0x40
PAGE_READWRITE = 0x04
PAGE_GUARD = 0x100
STATUS_GUARD_PAGE_VIOLATION = 0x80000001
GUARD_REGION_SIZE = 0x200000
GUARD_OFFSET = 0x5E000

# WOW64_CONTEXT offsets (winnt.h, x86 layout).
CTX_EDI = 0x9C
CTX_ESI = 0xA0
CTX_EBX = 0xA4
CTX_EDX = 0xA8
CTX_ECX = 0xAC
CTX_EAX = 0xB0
CTX_EBP = 0xB4
CTX_EIP = 0xB8
CTX_EFLAGS = 0xC0
CTX_ESP = 0xC4
EFLAGS_TRAP = 0x100

# RVAs inside ioncube_loader_win_7.2.dll (32-bit build, 15.5.x).
RVA_FACTORY = 0x1C40
RVA_CIPHER0_INIT = 0x1BB0
FACTORY_SIGNATURE = bytes.fromhex("a1a0cb0b10")
CIPHER0_SIGNATURE = bytes.fromhex("5153555657b906000000")


class STARTUPINFOW(ctypes.Structure):
    _fields_ = [
        ("cb", wt.DWORD),
        ("lpReserved", wt.LPWSTR),
        ("lpDesktop", wt.LPWSTR),
        ("lpTitle", wt.LPWSTR),
        ("dwX", wt.DWORD),
        ("dwY", wt.DWORD),
        ("dwXSize", wt.DWORD),
        ("dwYSize", wt.DWORD),
        ("dwXCountChars", wt.DWORD),
        ("dwYCountChars", wt.DWORD),
        ("dwFillAttribute", wt.DWORD),
        ("dwFlags", wt.DWORD),
        ("wShowWindow", wt.WORD),
        ("cbReserved2", wt.WORD),
        ("lpReserved2", ctypes.POINTER(ctypes.c_ubyte)),
        ("hStdInput", wt.HANDLE),
        ("hStdOutput", wt.HANDLE),
        ("hStdError", wt.HANDLE),
    ]


class PROCESS_INFORMATION(ctypes.Structure):
    _fields_ = [
        ("hProcess", wt.HANDLE),
        ("hThread", wt.HANDLE),
        ("dwProcessId", wt.DWORD),
        ("dwThreadId", wt.DWORD),
    ]


kernel32.CreateProcessW.argtypes = [
    wt.LPCWSTR,
    wt.LPWSTR,
    ctypes.c_void_p,
    ctypes.c_void_p,
    wt.BOOL,
    wt.DWORD,
    ctypes.c_void_p,
    wt.LPCWSTR,
    ctypes.POINTER(STARTUPINFOW),
    ctypes.POINTER(PROCESS_INFORMATION),
]
kernel32.CreateProcessW.restype = wt.BOOL
kernel32.WaitForDebugEvent.argtypes = [ctypes.c_void_p, wt.DWORD]
kernel32.WaitForDebugEvent.restype = wt.BOOL
kernel32.ContinueDebugEvent.argtypes = [wt.DWORD, wt.DWORD, wt.DWORD]
kernel32.WaitForDebugEvent.restype = wt.BOOL
kernel32.ReadProcessMemory.argtypes = [
    wt.HANDLE,
    ctypes.c_void_p,
    ctypes.c_void_p,
    ctypes.c_size_t,
    ctypes.POINTER(ctypes.c_size_t),
]
kernel32.WriteProcessMemory.argtypes = [
    wt.HANDLE,
    ctypes.c_void_p,
    ctypes.c_void_p,
    ctypes.c_size_t,
    ctypes.POINTER(ctypes.c_size_t),
]
kernel32.VirtualProtectEx.argtypes = [
    wt.HANDLE,
    ctypes.c_void_p,
    ctypes.c_size_t,
    wt.DWORD,
    ctypes.POINTER(wt.DWORD),
]
kernel32.FlushInstructionCache.argtypes = [wt.HANDLE, ctypes.c_void_p, ctypes.c_size_t]
kernel32.Wow64GetThreadContext.argtypes = [wt.HANDLE, ctypes.c_void_p]
kernel32.Wow64GetThreadContext.restype = wt.BOOL
kernel32.Wow64SetThreadContext.argtypes = [wt.HANDLE, ctypes.c_void_p]
kernel32.Wow64SetThreadContext.restype = wt.BOOL
kernel32.OpenThread.argtypes = [wt.DWORD, wt.BOOL, wt.DWORD]
kernel32.OpenThread.restype = wt.HANDLE

THREAD_GET_CONTEXT = 0x0008
THREAD_SET_CONTEXT = 0x0010
THREAD_SUSPEND_RESUME = 0x0002

_thread_handles: dict[int, int] = {}


def thread_handle(tid: int) -> int:
    handle = _thread_handles.get(tid)
    if handle is None:
        handle = kernel32.OpenThread(
            THREAD_GET_CONTEXT | THREAD_SET_CONTEXT | THREAD_SUSPEND_RESUME, False, tid
        )
        if handle:
            _thread_handles[tid] = int(handle)
    return int(handle or 0)


def read_memory(process: int, address: int, size: int) -> bytes:
    buffer = ctypes.create_string_buffer(size)
    read = ctypes.c_size_t()
    ok = kernel32.ReadProcessMemory(
        process, ctypes.c_void_p(address), buffer, size, ctypes.byref(read)
    )
    if not ok:
        return b""
    return buffer.raw[: read.value]


def write_memory(process: int, address: int, data: bytes) -> bool:
    old = wt.DWORD()
    kernel32.VirtualProtectEx(
        process,
        ctypes.c_void_p(address),
        len(data),
        PAGE_EXECUTE_READWRITE,
        ctypes.byref(old),
    )
    written = ctypes.c_size_t()
    ok = kernel32.WriteProcessMemory(
        process,
        ctypes.c_void_p(address),
        data,
        len(data),
        ctypes.byref(written),
    )
    kernel32.VirtualProtectEx(
        process, ctypes.c_void_p(address), len(data), old.value, ctypes.byref(old)
    )
    kernel32.FlushInstructionCache(process, ctypes.c_void_p(address), len(data))
    return bool(ok) and written.value == len(data)


class Wow64Context:
    def __init__(self) -> None:
        self.buffer = ctypes.create_string_buffer(WOW64_CONTEXT_SIZE)
        struct.pack_into("<I", self.buffer, 0, WOW64_CONTEXT_ALL)

    def get(self, thread: int) -> bool:
        struct.pack_into("<I", self.buffer, 0, WOW64_CONTEXT_ALL)
        return bool(kernel32.Wow64GetThreadContext(thread, self.buffer))

    def set(self, thread: int) -> bool:
        return bool(kernel32.Wow64SetThreadContext(thread, self.buffer))

    def u32(self, offset: int) -> int:
        return struct.unpack_from("<I", self.buffer, offset)[0]

    def put_u32(self, offset: int, value: int) -> None:
        struct.pack_into("<I", self.buffer, offset, value & 0xFFFFFFFF)


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


kernel32.VirtualQueryEx.argtypes = [
    wt.HANDLE,
    ctypes.c_void_p,
    ctypes.POINTER(MEMORY_BASIC_INFORMATION64),
    ctypes.c_size_t,
]
kernel32.VirtualQueryEx.restype = ctypes.c_size_t

EXEC_PROTECTS = {0x10, 0x20, 0x40, 0x80}  # EXECUTE, EXECUTE_READ, EXECUTE_READWRITE, EXECUTE_WRITECOPY

# Distinctive, address-independent fragments of the two routines.
LOOP_SIGNATURE = bytes.fromhex("c1e8088d7601324433ff8846ff")  # cipher0 xor loop
FACTORY_SIGNATURE_32 = bytes.fromhex("83ff0677")  # cmp edi, 6 / ja
FACTORY_TAIL = bytes.fromhex("ff24bd")  # jmp [edi*4+imm32]


def scan_process(process: int, pattern: bytes, limit: int = 0x80000000) -> list[int]:
    hits: list[int] = []
    address = 0
    info = MEMORY_BASIC_INFORMATION64()
    while address < limit:
        if not kernel32.VirtualQueryEx(
            process, ctypes.c_void_p(address), ctypes.byref(info), ctypes.sizeof(info)
        ):
            break
        size = info.RegionSize
        if info.State == 0x1000 and info.Protect in EXEC_PROTECTS and size < 0x4000000:
            data = read_memory(process, address, size)
            start = 0
            while True:
                index = data.find(pattern, start)
                if index < 0:
                    break
                hits.append(address + index)
                start = index + 1
        address += size or 0x1000
    return hits


def read_cstr(process: int, address: int, limit: int = 64) -> str:
    data = read_memory(process, address, limit)
    end = data.find(b"\0")
    return data[: end if end >= 0 else len(data)].decode("latin1", "replace")


def find_export(process: int, base: int, name: str) -> int | None:
    dos = read_memory(process, base, 0x40)
    if len(dos) != 0x40 or dos[:2] != b"MZ":
        return None
    pe = struct.unpack_from("<I", dos, 0x3C)[0]
    nt = read_memory(process, base + pe, 0x18)
    if len(nt) != 0x18 or nt[:4] != b"PE\0\0":
        return None
    opt_size = struct.unpack_from("<H", nt, 20)[0]
    opt = read_memory(process, base + pe + 24, opt_size)
    if len(opt) < 0x60:
        return None
    magic = struct.unpack_from("<H", opt, 0)[0]
    dd = 96 if magic == 0x10B else 112
    exp_rva, exp_size = struct.unpack_from("<II", opt, dd)
    if not exp_rva or not exp_size:
        return None
    exp = read_memory(process, base + exp_rva, 40)
    if len(exp) != 40:
        return None
    n_names = struct.unpack_from("<I", exp, 24)[0]
    if n_names > 20000:
        return None
    funcs_rva = struct.unpack_from("<I", exp, 28)[0]
    names_rva = struct.unpack_from("<I", exp, 32)[0]
    ords_rva = struct.unpack_from("<I", exp, 36)[0]
    names = read_memory(process, base + names_rva, n_names * 4)
    if len(names) != n_names * 4:
        return None
    for index in range(n_names):
        name_rva = struct.unpack_from("<I", names, index * 4)[0]
        if read_cstr(process, base + name_rva) == name:
            ordinal = struct.unpack_from(
                "<H", read_memory(process, base + ords_rva + index * 2, 2), 0
            )[0]
            func_rva = struct.unpack_from(
                "<I", read_memory(process, base + funcs_rva + ordinal * 4, 4), 0
            )[0]
            return base + func_rva
    return None


def dump_hex(process: int, address: int, size: int) -> str:
    if not address:
        return ""
    data = read_memory(process, address, size)
    return data.hex()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--php", required=True, type=Path)
    parser.add_argument("--loader", required=True, type=Path)
    parser.add_argument("--target", required=True, type=Path)
    parser.add_argument(
        "--include",
        action="store_true",
        help="include the file instead of linting it (lint does not run the decoder)",
    )
    parser.add_argument("--log", type=Path, default=Path("scratch/ic72_cipher_trace.jsonl"))
    parser.add_argument("--timeout", type=float, default=90.0)
    parser.add_argument("--diagnose", action="store_true")
    parser.add_argument("--show-output", action="store_true")
    args = parser.parse_args()

    ini = Path(tempfile.gettempdir()) / "ic72_cipher_trace.ini"
    ini.write_text(
        "[PHP]\r\n"
        "error_reporting = 0\r\n"
        "display_errors = On\r\n"
        f'zend_extension = "{args.loader.resolve()}"\r\n',
        encoding="utf-8",
    )

    if args.include:
        command = (
            f'"{args.php.resolve()}" -c "{ini}" -r "include $argv[1];" -- '
            f'"{args.target.resolve()}"'
        )
    else:
        command = f'"{args.php.resolve()}" -c "{ini}" -l "{args.target.resolve()}"'
    startup = STARTUPINFOW()
    startup.cb = ctypes.sizeof(STARTUPINFOW)
    info = PROCESS_INFORMATION()
    if not kernel32.CreateProcessW(
        None,
        ctypes.create_unicode_buffer(command),
        None,
        None,
        bool(args.show_output),
        DEBUG_ONLY_THIS_PROCESS | (0 if args.show_output else CREATE_NO_WINDOW),
        None,
        str(args.php.resolve().parent),
        ctypes.byref(startup),
        ctypes.byref(info),
    ):
        raise SystemExit(f"CreateProcess failed: {ctypes.get_last_error()}")

    process = int(info.hProcess)
    event = ctypes.create_string_buffer(0x120)
    context = Wow64Context()
    breakpoints: dict[int, dict[str, object]] = {}
    original_bytes: dict[int, bytes] = {}
    pending_reinsert: dict[int, int] = {}
    module_base: int | None = None
    compile_hook: int | None = None
    dll_bases: list[int] = []
    symbol_pass = False
    guarded_pages: list[int] = []
    guard_hits = [0]

    guard_thread_started = [False]

    def start_guard_watch() -> None:
        """Guard offset 0x5E000 of every 2 MiB Zend MM chunk as it appears."""
        if guard_thread_started[0]:
            return
        guard_thread_started[0] = True

        def worker() -> None:
            deadline = time.monotonic() + 30
            while time.monotonic() < deadline and not done:
                info = MEMORY_BASIC_INFORMATION64()
                address = 0
                armed_here = []
                while address < 0x7FFF0000:
                    if not kernel32.VirtualQueryEx(
                        process,
                        ctypes.c_void_p(address),
                        ctypes.byref(info),
                        ctypes.sizeof(info),
                    ):
                        break
                    size = info.RegionSize
                    if (
                        info.State == 0x1000
                        and size == GUARD_REGION_SIZE
                        and info.Protect == PAGE_READWRITE
                    ):
                        page = info.BaseAddress + GUARD_OFFSET
                        if page not in guarded_pages:
                            old = wt.DWORD()
                            if kernel32.VirtualProtectEx(
                                process,
                                ctypes.c_void_p(page),
                                0x1000,
                                PAGE_READWRITE | PAGE_GUARD,
                                ctypes.byref(old),
                            ):
                                guarded_pages.append(page)
                                armed_here.append(page)
                    address += size or 0x1000
                if armed_here:
                    records.append(
                        {"event": "guard-armed", "pages": [hex(p) for p in armed_here]}
                    )
                time.sleep(0.01)

        threading.Thread(target=worker, daemon=True).start()
    records: list[dict[str, object]] = []
    done = False
    scan_attempts = 0

    import threading

    def watch_hook(symbol: int, known: int | None) -> None:
        """Arm the compile hook once PHP initialises the pointer at request start."""

        def worker() -> None:
            deadline = time.monotonic() + 25
            while time.monotonic() < deadline:
                address = known
                if address is None:
                    pointer = read_memory(process, symbol, 4)
                    if len(pointer) != 4:
                        time.sleep(0.01)
                        continue
                    address = struct.unpack_from("<I", pointer, 0)[0]
                    if not module_base or not (
                        module_base <= address < module_base + 0x100000
                    ):
                        time.sleep(0.005)
                        continue
                original = read_memory(process, address, 1)
                if original and write_memory(process, address, b"\xcc"):
                    breakpoints[address] = {"name": "compile-hook", "rva": address}
                    original_bytes[address] = original
                    records.append(
                        {"event": "compile-hook-armed", "address": hex(address)}
                    )
                return

        threading.Thread(target=worker, daemon=True).start()

    def arm_scanned() -> bool:
        if not module_base:
            return False
        loop_hits = scan_process(process, LOOP_SIGNATURE)
        factory_hits = []
        for hit in scan_process(process, FACTORY_SIGNATURE_32):
            window = read_memory(process, hit + 4, 12)
            if len(window) >= 4 and window[1:4] == FACTORY_TAIL:
                factory_hits.append(hit)
        records.append(
            {
                "event": "scan",
                "loop": [hex(h) for h in loop_hits],
                "factory": [hex(h) for h in factory_hits],
                "factory_bytes": [
                    read_memory(process, h - 0x1D, 0x28).hex() for h in factory_hits
                ],
            }
        )
        armed = 0
        candidates = [(hit, 0x5E, "cipher0") for hit in loop_hits]
        candidates += [(hit, 0x1D, "factory") for hit in factory_hits]
        for hit, delta, name in candidates:
            address = hit - delta
            if address in breakpoints:
                continue
            original = read_memory(process, address, 1)
            if original and write_memory(process, address, b"\xcc"):
                breakpoints[address] = {"name": name, "rva": address - module_base}
                original_bytes[address] = original
                armed += 1
        return armed > 0

    import time

    deadline = time.monotonic() + args.timeout
    while not done and time.monotonic() < deadline:
        if not kernel32.WaitForDebugEvent(ctypes.byref(event), 200):
            continue
        code = struct.unpack_from("<I", event, 0)[0]
        pid = struct.unpack_from("<I", event, 4)[0]
        tid = struct.unpack_from("<I", event, 8)[0]
        base_off = 0x10
        status = DBG_CONTINUE

        if code == LOAD_DLL_DEBUG_EVENT:
            dll_base = struct.unpack_from("<Q", event, base_off + 8)[0]
            if dll_base not in dll_bases:
                dll_bases.append(dll_base)
            if args.diagnose:
                name_buffer = ctypes.create_unicode_buffer(260)
                psapi.GetModuleFileNameExW(
                    process, wt.HMODULE(dll_base), name_buffer, 260
                )
                probe = read_memory(process, dll_base + RVA_FACTORY, 8)
                header = read_memory(process, dll_base, 0x40)
                image_base = None
                if len(header) == 0x40 and header[:2] == b"MZ":
                    pe_off = struct.unpack_from("<I", header, 0x3C)[0]
                    optional = read_memory(process, dll_base + pe_off + 0x18, 0x40)
                    if len(optional) == 0x40:
                        image_base = struct.unpack_from("<I", optional, 0x1C)[0]
                records.append(
                    {
                        "event": "dll",
                        "base": hex(dll_base),
                        "name": name_buffer.value,
                        "probe": probe.hex(),
                        "image_base": hex(image_base) if image_base else None,
                    }
                )
            if compile_hook is None:
                try:
                    symbol = find_export(process, dll_base, "zend_compile_file")
                except (struct.error, ValueError):
                    symbol = None
                if symbol:
                    pointer = read_memory(process, symbol, 4)
                    if len(pointer) == 4:
                        hook = struct.unpack_from("<I", pointer, 0)[0]
                        if hook and hook not in (0, 0xFFFFFFFF):
                            compile_hook = hook
                            records.append(
                                {
                                    "event": "compile-hook",
                                    "symbol": hex(symbol),
                                    "hook": hex(hook),
                                    "in_loader": module_base is not None
                                    and module_base <= hook < module_base + 0x100000,
                                }
                            )
                            original = read_memory(process, hook, 1)
                            if original and write_memory(process, hook, b"\xcc"):
                                breakpoints[hook] = {"name": "compile-hook", "rva": hook}
                                original_bytes[hook] = original
            if module_base is None:
                probe = read_memory(process, dll_base + RVA_FACTORY, 5)
                relocated = (
                    len(probe) == 5
                    and probe[0] == 0xA1
                    and struct.unpack_from("<I", probe, 1)[0] == (dll_base + 0xBCBA0) & 0xFFFFFFFF
                )
                if relocated or probe == FACTORY_SIGNATURE:
                    module_base = dll_base
                    start_guard_watch()
                    preferred = 0x10000000
                    records.append(
                        {
                            "event": "preferred-map",
                            "probe": read_memory(
                                process, preferred + RVA_FACTORY, 8
                            ).hex(),
                        }
                    )
                    header = read_memory(process, dll_base, 0x40)
                    if len(header) == 0x40 and header[:2] == b"MZ":
                        pe_off = struct.unpack_from("<I", header, 0x3C)[0]
                        optional = read_memory(process, dll_base + pe_off + 0x18, 0x40)
                        if len(optional) == 0x40:
                            entry = dll_base + struct.unpack_from("<I", optional, 0x10)[0]
                            original = read_memory(process, entry, 1)
                            if original and write_memory(process, entry, b"\xcc"):
                                breakpoints[entry] = {
                                    "name": "loader-entry",
                                    "rva": entry - dll_base,
                                }
                                original_bytes[entry] = original
                    arm_scanned()
        elif code == CREATE_PROCESS_DEBUG_EVENT:
            image = struct.unpack_from("<Q", event, base_off + 0x18)[0]
            header = read_memory(process, image, 0x40)
            if len(header) == 0x40 and header[:2] == b"MZ":
                pe_off = struct.unpack_from("<I", header, 0x3C)[0]
                optional = read_memory(process, image + pe_off + 0x18, 0x40)
                if len(optional) == 0x40:
                    entry = image + struct.unpack_from("<I", optional, 0x10)[0]
                    original = read_memory(process, entry, 1)
                    if original and write_memory(process, entry, b"\xcc"):
                        breakpoints[entry] = {"name": "entry", "rva": entry - image}
                        original_bytes[entry] = original
                        records.append({"event": "entry-armed", "address": hex(entry)})
        elif code == EXCEPTION_DEBUG_EVENT:
            exception_code = struct.unpack_from("<I", event, base_off)[0]
            exception_address = struct.unpack_from("<Q", event, base_off + 0x10)[0]
            low = exception_address & 0xFFFFFFFF
            if len(records) < 200:
                records.append(
                    {
                        "event": "exception",
                        "code": f"0x{exception_code & 0xFFFFFFFF:08X}",
                        "address": hex(low),
                    }
                )
            if not symbol_pass and len(dll_bases) > 6:
                symbol_pass = True
                for base in dll_bases:
                    try:
                        symbol = find_export(process, base, "zend_compile_file")
                    except (struct.error, ValueError):
                        symbol = None
                    if not symbol:
                        continue
                    pointer = read_memory(process, symbol, 4)
                    if len(pointer) != 4:
                        continue
                    hook = struct.unpack_from("<I", pointer, 0)[0]
                    records.append(
                        {
                            "event": "symbol",
                            "base": hex(base),
                            "symbol": hex(symbol),
                            "hook": hex(hook),
                            "in_loader": bool(
                                module_base and module_base <= hook < module_base + 0x100000
                            ),
                        }
                    )
                    if hook and module_base and module_base <= hook < module_base + 0x100000:
                        watch_hook(symbol, hook)
                    elif not hook:
                        watch_hook(symbol, None)
            if module_base and scan_attempts < 4:
                scan_attempts += 1
                if arm_scanned():
                    scan_attempts = 4
            if exception_code == STATUS_GUARD_PAGE_VIOLATION:
                fault = struct.unpack_from("<Q", event, base_off + 0x28)[0] & ~0xFFF
                if fault in guarded_pages:
                    handle = thread_handle(tid)
                    detail: dict[str, object] = {"page": hex(fault)}
                    if handle and context.get(handle):
                        detail.update(
                            {
                                "eip": hex(context.u32(CTX_EIP)),
                                "eax": hex(context.u32(CTX_EAX)),
                                "ecx": hex(context.u32(CTX_ECX)),
                                "edx": hex(context.u32(CTX_EDX)),
                                "esi": hex(context.u32(CTX_ESI)),
                                "edi": hex(context.u32(CTX_EDI)),
                                "ebp": hex(context.u32(CTX_EBP)),
                                "esp": hex(context.u32(CTX_ESP)),
                            }
                        )
                    stack = read_memory(process, context.u32(CTX_ESP), 32)
                    if len(stack) == 32:
                        detail["stack"] = [
                            hex(v) for v in struct.unpack("<8I", stack)
                        ]
                        detail["caller"] = detail["stack"][0]
                    records.append({"event": "guard-write", **detail})
                    guard_hits[0] += 1
                    old = wt.DWORD()
                    kernel32.VirtualProtectEx(
                        process,
                        ctypes.c_void_p(fault),
                        0x1000,
                        PAGE_READWRITE,
                        ctypes.byref(old),
                    )
                    if guard_hits[0] < 60:
                        kernel32.VirtualProtectEx(
                            process,
                            ctypes.c_void_p(fault),
                            0x1000,
                            PAGE_READWRITE | PAGE_GUARD,
                            ctypes.byref(old),
                        )
                    else:
                        guarded_pages.remove(fault)
            elif exception_code in BREAKPOINT_CODES and low in breakpoints:
                handle = thread_handle(tid)
                if not handle or not context.get(handle):
                    records.append({"event": "context-failed", "address": hex(low)})
                else:
                    entry: dict[str, object] = {
                        "event": breakpoints[low]["name"],
                        "address": hex(low),
                        "ecx": context.u32(CTX_ECX),
                        "edx": context.u32(CTX_EDX),
                        "eax": context.u32(CTX_EAX),
                        "esp": hex(context.u32(CTX_ESP)),
                        "ebp": hex(context.u32(CTX_EBP)),
                        "caller": hex(
                            struct.unpack_from(
                                "<I", read_memory(process, context.u32(CTX_ESP), 4), 0
                            )[0]
                        )
                        if read_memory(process, context.u32(CTX_ESP), 4)
                        else None,
                    }
                    if breakpoints[low]["name"] == "compile-hook":
                        start_guard_watch()
                    if breakpoints[low]["name"] == "cipher0":
                        esp = context.u32(CTX_ESP)
                        stack = read_memory(process, esp + 4, 0x18)
                        if len(stack) == 0x18:
                            source, _ret, _retval, key, length, target = struct.unpack(
                                "<6I", stack
                            )
                            entry.update(
                                {
                                    "source": hex(source),
                                    "key_ptr": hex(key),
                                    "length": length,
                                    "target": hex(target),
                                    "key_hex": dump_hex(process, key, min(length, 64)),
                                    "source_hex": dump_hex(process, source, min(length, 32)),
                                }
                            )
                    records.append(entry)
                # Single-step over the restored instruction, then re-arm.
                if write_memory(process, low, original_bytes[low]):
                    context.put_u32(CTX_EIP, low)
                    context.put_u32(
                        CTX_EFLAGS, context.u32(CTX_EFLAGS) | EFLAGS_TRAP
                    )
                    context.set(handle)
                    pending_reinsert[low] = tid
            elif exception_code in SINGLE_STEP_CODES and low in pending_reinsert:
                if low in breakpoints:
                    write_memory(process, low, b"\xcc")
                handle = thread_handle(tid)
                if handle:
                    context.get(handle)
                    context.put_u32(CTX_EFLAGS, context.u32(CTX_EFLAGS) & ~EFLAGS_TRAP)
                    context.set(handle)
                pending_reinsert.pop(low, None)
            elif exception_code not in (BREAKPOINT_CODES | SINGLE_STEP_CODES | {0x4000001F}):
                status = DBG_EXCEPTION_NOT_HANDLED
        elif code == EXIT_PROCESS_DEBUG_EVENT:
            exit_code = struct.unpack_from("<I", event, base_off)[0]
            records.append({"event": "exit", "code": exit_code})
            done = True

        kernel32.ContinueDebugEvent(pid, tid, status)

    args.log.parent.mkdir(parents=True, exist_ok=True)
    with args.log.open("w", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(record) + "\n")
    print(json.dumps({"module_base": hex(module_base) if module_base else None,
                      "breakpoints": sorted(hex(a) for a in breakpoints),
                      "records": len(records)}, indent=2))
    for record in records[:16]:
        print(json.dumps(record))
    return 0


if __name__ == "__main__":
    sys.exit(main())
