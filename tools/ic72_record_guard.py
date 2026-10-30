"""Catch the ionCube 7.2 record reader by guarding the page it lands on.

The decompressed body lives in a private region of ~0xB7000 bytes and the
record starts near the end of it, at ``region + 0xAD6D4`` (+0xAD87C on other
runs).  Polling for the finished record loses the race by microseconds, so
this tool arms ``PAGE_GUARD`` on the page that holds it as soon as the region
appears.  Every write into that page faults, which freezes the thread while
the body is still inflating; as soon as the record signature is fully present
the tool arms Dr0..Dr3 over it.  The next access is the loader's record
decode, reported with EIP, stack and registers.

All target registers are 32-bit, so ``Wow64GetThreadContext`` is used.
"""

from __future__ import annotations

import argparse
import ctypes
import ctypes.wintypes as wt
import json
import struct
import tempfile
import threading
import time
from pathlib import Path

kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
psapi = ctypes.WinDLL("psapi", use_last_error=True)
psapi.GetModuleFileNameExW.argtypes = [wt.HANDLE, wt.HMODULE, wt.LPWSTR, wt.DWORD]

DEBUG_ONLY_THIS_PROCESS = 0x00000002
CREATE_NO_WINDOW = 0x08000000
DBG_CONTINUE = 0x00010002
DBG_EXCEPTION_NOT_HANDLED = 0x80010001

EXCEPTION_DEBUG_EVENT = 1
CREATE_PROCESS_DEBUG_EVENT = 3
EXIT_PROCESS_DEBUG_EVENT = 5
LOAD_DLL_DEBUG_EVENT = 6

BREAKPOINT_CODES = {0x80000003, 0x4000001F}
SINGLE_STEP_CODES = {0x80000004, 0x4000001E}
STATUS_GUARD_PAGE_VIOLATION = 0x80000001

PAGE_READWRITE = 0x04
PAGE_EXECUTE_READWRITE = 0x40
PAGE_GUARD = 0x100

WOW64_CONTEXT_CONTROL = 0x00010001
WOW64_CONTEXT_INTEGER = 0x00010002
WOW64_CONTEXT_SEGMENTS = 0x00010004
WOW64_CONTEXT_ALL = (
    WOW64_CONTEXT_CONTROL | WOW64_CONTEXT_INTEGER | WOW64_CONTEXT_SEGMENTS
)
WOW64_CONTEXT_SIZE = 0x2CC

CTX_DR0 = 0x04
CTX_DR6 = 0x14
CTX_DR7 = 0x18
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

FACTORY_SIGNATURE = bytes.fromhex("a1a0cb0b10")
INT3 = bytes([0xCC])
DEFAULT_MARKER = "ffffffff68020000f885d77d18f94c83"


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
kernel32.VirtualQueryEx.argtypes = [
    wt.HANDLE,
    ctypes.c_void_p,
    ctypes.POINTER(MEMORY_BASIC_INFORMATION64),
    ctypes.c_size_t,
]
kernel32.VirtualQueryEx.restype = ctypes.c_size_t
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


class Wow64Context:
    def __init__(self) -> None:
        self.buffer = ctypes.create_string_buffer(WOW64_CONTEXT_SIZE)

    def get(self, thread: int) -> bool:
        struct.pack_into("<I", self.buffer, 0, WOW64_CONTEXT_ALL)
        return bool(kernel32.Wow64GetThreadContext(thread, self.buffer))

    def set(self, thread: int) -> bool:
        return bool(kernel32.Wow64SetThreadContext(thread, self.buffer))

    def u32(self, offset: int) -> int:
        return struct.unpack_from("<I", self.buffer, offset)[0]

    def put_u32(self, offset: int, value: int) -> None:
        struct.pack_into("<I", self.buffer, offset, value & 0xFFFFFFFF)

    def arm(self, address: int) -> None:
        base = address & ~0x3
        for slot in range(4):
            self.put_u32(CTX_DR0 + 4 * slot, base + 4 * slot)
        dr7 = 0
        for slot in range(4):
            dr7 |= 1 << (2 * slot)
            dr7 |= 0b11 << (16 + 4 * slot)
            dr7 |= 0b11 << (18 + 4 * slot)
        self.put_u32(CTX_DR7, dr7)
        self.put_u32(CTX_DR6, 0)

    def disarm(self) -> None:
        for slot in range(4):
            self.put_u32(CTX_DR0 + 4 * slot, 0)
        self.put_u32(CTX_DR7, 0)
        self.put_u32(CTX_DR6, 0)


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
        process, ctypes.c_void_p(address), data, len(data), ctypes.byref(written)
    )
    kernel32.VirtualProtectEx(
        process, ctypes.c_void_p(address), len(data), old.value, ctypes.byref(old)
    )
    kernel32.FlushInstructionCache(process, ctypes.c_void_p(address), len(data))
    return bool(ok) and written.value == len(data)


def protect(process: int, address: int, size: int, flags: int) -> bool:
    old = wt.DWORD()
    return bool(
        kernel32.VirtualProtectEx(
            process, ctypes.c_void_p(address), size, flags, ctypes.byref(old)
        )
    )


def read_c_string(process: int, pointer: int, limit: int = 260) -> str:
    if not pointer:
        return ""
    raw = read_memory(process, pointer, limit)
    end = raw.find(b"\0")
    return raw[: end if end >= 0 else len(raw)].decode("latin1", "replace")


def read_zend_string(process: int, pointer: int, limit: int = 260) -> str:
    if not pointer:
        return ""
    length = read_memory(process, pointer + 0x0C, 4)
    if len(length) != 4:
        return ""
    size = min(struct.unpack_from("<I", length, 0)[0], limit)
    return read_memory(process, pointer + 0x10, size).decode("latin1", "replace")


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
    funcs_rva = struct.unpack_from("<I", exp, 28)[0]
    names_rva = struct.unpack_from("<I", exp, 32)[0]
    ords_rva = struct.unpack_from("<I", exp, 36)[0]
    names = read_memory(process, base + names_rva, n_names * 4)
    if len(names) != n_names * 4:
        return None
    for index in range(n_names):
        name_rva = struct.unpack_from("<I", names, index * 4)[0]
        raw = read_memory(process, base + name_rva, 64)
        end = raw.find(b"\0")
        if end < 0 or raw[:end].decode("latin1") != name:
            continue
        ordinal = struct.unpack_from(
            "<H", read_memory(process, base + ords_rva + index * 2, 2), 0
        )[0]
        return base + struct.unpack_from(
            "<I", read_memory(process, base + funcs_rva + ordinal * 4, 4), 0
        )[0]
    return None


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--php", required=True, type=Path)
    parser.add_argument("--loader", required=True, type=Path)
    parser.add_argument("--target", required=True, type=Path)
    parser.add_argument("--marker", default=DEFAULT_MARKER)
    parser.add_argument(
        "--guard-offset",
        type=lambda v: int(v, 0),
        default=0xAD000,
        help="page offset inside the body region that holds the record",
    )
    parser.add_argument(
        "--region-min", type=lambda v: int(v, 0), default=0x80000
    )
    parser.add_argument(
        "--region-max", type=lambda v: int(v, 0), default=0x100000
    )
    parser.add_argument(
        "--guard",
        action="store_true",
        help="enable the page-guard worker (off by default: it perturbs the target)",
    )
    parser.add_argument(
        "--fixed",
        action="store_true",
        help="guard region base + guard-offset instead of the write frontier",
    )
    parser.add_argument("--bp", action="append", default=[])
    parser.add_argument(
        "--dump-bp",
        action="append",
        default=[],
        help="RVA whose hit dumps ecx[0..edx) to --dump-to",
    )
    parser.add_argument("--dump-to", type=Path, default=None)
    parser.add_argument(
        "--oparray-bp",
        action="append",
        default=[],
        help="RVA whose hit treats eax as a zend_op_array and dumps it",
    )
    parser.add_argument("--log", type=Path, default=Path("scratch/ic72_record_guard.jsonl"))
    parser.add_argument("--timeout", type=float, default=60.0)
    parser.add_argument("--show-output", action="store_true")
    parser.add_argument(
        "--auto",
        action="store_true",
        help="start guarding when zend_compile_file is entered",
    )
    args = parser.parse_args()

    marker = bytes.fromhex(args.marker)
    ini = Path(tempfile.gettempdir()) / "ic72_record_guard.ini"
    ini.write_text(
        "[PHP]\n"
        "error_reporting = 0\n"
        "display_errors = On\n"
        f'zend_extension = "{args.loader.resolve()}"\n',
        encoding="utf-8",
        newline="\r\n",
    )
    command = (
        f'"{args.php.resolve()}" -c "{ini}" -r "include $argv[1];" -- '
        f'"{args.target.resolve()}"'
    )

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
    pid = int(info.dwProcessId)
    event = ctypes.create_string_buffer(0x120)
    context = Wow64Context()
    records: list[dict[str, object]] = []
    breakpoints: dict[int, bytes] = {}
    pending: dict[int, int] = {}
    module_base: int | None = None
    known_bases: set[int] = set()
    guarded: dict[int, bool] = {}
    started = time.monotonic()
    state = {
        "watch_address": 0,
        "hits": 0,
        "done": False,
        "guarded": 0,
        "guard_start": not args.auto,
        "compile_hook": 0,
        "compile_symbol": 0,
        "hook_filter": 0,
        "hook_decoder": 0,
        "dump_sites": {int(spec, 0) for spec in args.dump_bp},
        "oparray_sites": {int(spec, 0) for spec in args.oparray_bp},
    }

    def log(entry: dict[str, object]) -> None:
        entry["t"] = round(time.monotonic() - started, 4)
        records.append(entry)
        print(json.dumps(entry), flush=True)

    def guard_worker() -> None:
        deadline = time.monotonic() + args.timeout
        while time.monotonic() < deadline and not state["done"]:
            if not state["guard_start"]:
                time.sleep(0.0005)
                continue
            region = MEMORY_BASIC_INFORMATION64()
            address = 0
            while address < 0x7FFF0000:
                if not kernel32.VirtualQueryEx(
                    process,
                    ctypes.c_void_p(address),
                    ctypes.byref(region),
                    ctypes.sizeof(region),
                ):
                    break
                size = region.RegionSize
                if (
                    region.State == 0x1000
                    and region.Protect in (PAGE_READWRITE, 0x08)
                    and args.region_min <= size <= args.region_max
                ):
                    # The body region grows page by page, so guard the current
                    # write frontier; the fault handler walks it forward.
                    page = (
                        region.BaseAddress + args.guard_offset
                        if args.fixed
                        else region.BaseAddress + size - 0x1000
                    ) & ~0xFFF
                    if page not in guarded:
                        if protect(process, page, 0x1000, PAGE_READWRITE | PAGE_GUARD):
                            guarded[page] = True
                            state["guarded"] += 1
                            log(
                                {
                                    "event": "guard-armed",
                                    "page": hex(page),
                                    "region": hex(region.BaseAddress),
                                    "size": hex(size),
                                }
                            )
                address += size or 0x1000
            time.sleep(0.001)

    def bp_worker() -> None:
        """Keep the int3 bytes in place: the loader unpacks over them early."""

        deadline = time.monotonic() + args.timeout
        while time.monotonic() < deadline and not state["done"]:
            if not module_base:
                time.sleep(0.001)
                continue
            # The loader installs its zend_compile_file shim after DLL load,
            # so poll the export slot instead of arming once at load time.
            if (
                args.auto
                and state["compile_symbol"]
                and not state["compile_hook"]
            ):
                pointer = read_memory(process, state["compile_symbol"], 4)
                if len(pointer) == 4:
                    hook = struct.unpack_from("<I", pointer, 0)[0]
                    if hook != state.get("last_pointer"):
                        state["last_pointer"] = hook
                        log(
                            {
                                "event": "compile-pointer",
                                "value": hex(hook),
                                "in_loader": bool(
                                    module_base
                                    and module_base <= hook < module_base + 0x100000
                                ),
                            }
                        )
                    if module_base <= hook < module_base + 0x100000:
                        original = read_memory(process, hook, 1)
                        if original and write_memory(process, hook, INT3):
                            breakpoints[hook] = original
                            state["compile_hook"] = hook
                            log(
                                {
                                    "event": "bp-armed",
                                    "rva": hex(hook - module_base),
                                    "role": "zend_compile_file",
                                    "polled": True,
                                }
                            )
            for target in list(breakpoints):
                if target in pending:
                    continue
                if read_memory(process, target, 1) != INT3:
                    write_memory(process, target, INT3)
            time.sleep(0.002)

    if args.guard or args.auto:
        threading.Thread(target=guard_worker, daemon=True).start()
    threading.Thread(target=bp_worker, daemon=True).start()

    deadline = time.monotonic() + args.timeout
    while time.monotonic() < deadline and not state["done"]:
        if not kernel32.WaitForDebugEvent(ctypes.byref(event), 200):
            continue
        code = struct.unpack_from("<I", event, 0)[0]
        ev_pid = struct.unpack_from("<I", event, 4)[0]
        tid = struct.unpack_from("<I", event, 8)[0]
        base_off = 0x10
        status = DBG_CONTINUE

        if code == LOAD_DLL_DEBUG_EVENT:
            dll_base = struct.unpack_from("<Q", event, base_off + 8)[0]
            if dll_base not in known_bases:
                known_bases.add(dll_base)
                probe = read_memory(process, dll_base + 0x1C40, 5)
                if len(probe) == 5 and probe[0] == 0xA1 and (
                    probe == FACTORY_SIGNATURE
                    or struct.unpack_from("<I", probe, 1)[0]
                    == (dll_base + 0xBCBA0) & 0xFFFFFFFF
                ):
                    module_base = module_base or dll_base
                    name = ctypes.create_unicode_buffer(260)
                    psapi.GetModuleFileNameExW(
                        wt.HANDLE(process), wt.HMODULE(dll_base), name, 260
                    )
                    log(
                        {
                            "event": "loader-base",
                            "base": hex(dll_base),
                            "name": name.value,
                            "mz": read_memory(process, dll_base, 2).hex(),
                        }
                    )
                    if args.auto:
                        for known in list(known_bases):
                            symbol = find_export(process, known, "zend_compile_file")
                            if not symbol:
                                continue
                            pointer = read_memory(process, symbol, 4)
                            if len(pointer) != 4:
                                continue
                            hook = struct.unpack_from("<I", pointer, 0)[0]
                            log(
                                {
                                    "event": "compile-hook",
                                    "dll": hex(known),
                                    "pointer": hex(hook),
                                    "rva": hex(hook - dll_base)
                                    if dll_base <= hook < dll_base + 0x100000
                                    else None,
                                }
                            )
                            if state["compile_symbol"] == 0:
                                state["compile_symbol"] = symbol
                            if (
                                dll_base <= hook < dll_base + 0x100000
                                and hook not in breakpoints
                            ):
                                original = read_memory(process, hook, 1)
                                if original and write_memory(process, hook, INT3):
                                    breakpoints[hook] = original
                                    state["compile_hook"] = hook
                                    log(
                                        {
                                            "event": "bp-armed",
                                            "rva": hex(hook - dll_base),
                                            "role": "zend_compile_file",
                                        }
                                    )
                    for spec in args.bp:
                        target = dll_base + int(spec, 0)
                        if target in breakpoints:
                            continue
                        original = read_memory(process, target, 1)
                        if original and write_memory(process, target, INT3):
                            breakpoints[target] = original
                            log(
                                {
                                    "event": "bp-armed",
                                    "rva": hex(target - dll_base),
                                }
                            )
        elif code == EXCEPTION_DEBUG_EVENT:
            exception_code = struct.unpack_from("<I", event, base_off)[0]
            fault = struct.unpack_from("<Q", event, base_off + 0x10)[0] & 0xFFFFFFFF
            handle = kernel32.OpenThread(
                THREAD_GET_CONTEXT | THREAD_SET_CONTEXT | THREAD_SUSPEND_RESUME,
                False,
                tid,
            )
            try:
                if exception_code == STATUS_GUARD_PAGE_VIOLATION:
                    page = fault & ~0xFFF
                    if page not in guarded:
                        status = DBG_EXCEPTION_NOT_HANDLED
                        kernel32.ContinueDebugEvent(ev_pid, tid, status)
                        continue
                    data = read_memory(process, page, 0x1000)
                    index = data.find(marker) if data else -1
                    if index >= 0 and not state["watch_address"]:
                        if handle and context.get(handle):
                            target = page + index
                            state["watch_address"] = target
                            context.arm(target)
                            if context.set(handle):
                                log(
                                    {
                                        "event": "watch-armed",
                                        "address": hex(target),
                                        "page": hex(page),
                                        "offset": hex(index),
                                        "eip": hex(context.u32(CTX_EIP)),
                                        "record_hex": data[index : index + 64].hex(),
                                    }
                                )
                        protect(process, page, 0x1000, PAGE_READWRITE)
                    else:
                        # Walk the guard forward to the region's write frontier.
                        info_region = MEMORY_BASIC_INFORMATION64()
                        kernel32.VirtualQueryEx(
                            process,
                            ctypes.c_void_p(page),
                            ctypes.byref(info_region),
                            ctypes.sizeof(info_region),
                        )
                        frontier = (
                            info_region.BaseAddress + info_region.RegionSize - 0x1000
                        ) & ~0xFFF
                        if args.fixed:
                            protect(process, page, 0x1000, PAGE_READWRITE | PAGE_GUARD)
                        else:
                            guarded.pop(page, None)
                            if frontier != page and not state["watch_address"]:
                                if protect(
                                    process,
                                    frontier,
                                    0x1000,
                                    PAGE_READWRITE | PAGE_GUARD,
                                ):
                                    guarded[frontier] = True
                            else:
                                protect(
                                    process, page, 0x1000, PAGE_READWRITE | PAGE_GUARD
                                )
                        if state["guarded"] < 6:
                            entry = {
                                "event": "guard-write",
                                "page": hex(page),
                                "frontier": hex(frontier),
                                "eip": hex(context.u32(CTX_EIP))
                                if handle and context.get(handle)
                                else None,
                                "found": index,
                            }
                            if handle and module_base:
                                esp = context.u32(CTX_ESP)
                                frame = read_memory(process, esp, 0x800)
                                chain = []
                                for off in range(0, len(frame) - 3, 4):
                                    value = struct.unpack_from("<I", frame, off)[0]
                                    if module_base <= value < module_base + 0x100000:
                                        chain.append(hex(value - module_base))
                                entry["loader_chain"] = chain[:24]
                            log(entry)
                        state["guarded"] += 1
                elif exception_code in SINGLE_STEP_CODES:
                    dr6 = context.u32(CTX_DR6) if handle and context.get(handle) else 0
                    if dr6 & 0xF:
                        state["hits"] += 1
                        entry = {
                            "event": "watch-hit",
                            "dr6": hex(dr6),
                            "eip": hex(context.u32(CTX_EIP)),
                            "rva": hex(context.u32(CTX_EIP) - module_base)
                            if module_base
                            else None,
                            "eax": hex(context.u32(CTX_EAX)),
                            "ecx": hex(context.u32(CTX_ECX)),
                            "edx": hex(context.u32(CTX_EDX)),
                            "esi": hex(context.u32(CTX_ESI)),
                            "edi": hex(context.u32(CTX_EDI)),
                            "ebp": hex(context.u32(CTX_EBP)),
                            "esp": hex(context.u32(CTX_ESP)),
                        }
                        stack = read_memory(process, context.u32(CTX_ESP), 40)
                        if len(stack) == 40:
                            entry["stack"] = [hex(v) for v in struct.unpack("<10I", stack)]
                        entry["bytes"] = read_memory(
                            process, state["watch_address"], 32
                        ).hex()
                        log(entry)
                        context.disarm()
                        context.set(handle)
                    elif fault in pending:
                        if fault in breakpoints:
                            write_memory(process, fault, b"\xcc")
                        if handle and context.get(handle):
                            context.put_u32(
                                CTX_EFLAGS, context.u32(CTX_EFLAGS) & ~EFLAGS_TRAP
                            )
                            context.set(handle)
                        pending.pop(fault, None)
                elif exception_code in BREAKPOINT_CODES and fault in breakpoints:
                    if handle and context.get(handle) and fault in (
                        state.get("hook_filter"),
                        state.get("hook_decoder"),
                    ):
                        file_handle = context.u32(CTX_ECX)
                        raw = read_memory(process, file_handle + 0x2C, 4)
                        log(
                            {
                                "event": "compile-body",
                                "eip": hex(fault),
                                "rva": hex(fault - (module_base or 0)),
                                "zend_file_handle": hex(file_handle),
                                "path": read_c_string(
                                    process,
                                    struct.unpack_from("<I", raw, 0)[0]
                                    if len(raw) == 4
                                    else 0,
                                ),
                                "esp": hex(context.u32(CTX_ESP)),
                                "ret": hex(
                                    struct.unpack_from(
                                        "<I",
                                        read_memory(
                                            process, context.u32(CTX_ESP), 4
                                        ),
                                        0,
                                    )[0]
                                ),
                            }
                        )
                    if handle and context.get(handle) and fault == state["compile_hook"]:
                        handle_ptr = context.u32(CTX_ECX)
                        path = ""
                        string_ptr = read_memory(process, handle_ptr, 4)
                        if len(string_ptr) == 4:
                            string = struct.unpack_from("<I", string_ptr, 0)[0]
                            length = read_memory(process, string + 0x0C, 4)
                            if len(length) == 4:
                                size = min(struct.unpack_from("<I", length, 0)[0], 260)
                                raw = read_memory(process, string + 0x10, size)
                                path = raw.decode("latin1", "replace")
                        file_handle = context.u32(CTX_EDI)
                        path = read_c_string(
                            process,
                            struct.unpack_from(
                                "<I", read_memory(process, file_handle + 0x2C, 4), 0
                            )[0]
                            if len(read_memory(process, file_handle + 0x2C, 4)) == 4
                            else 0,
                        )
                        log(
                            {
                                "event": "compile-hit",
                                "eip": hex(fault),
                                "zend_file_handle": hex(file_handle),
                                "path": path,
                            }
                        )
                        # 0x62F30 does a filename filter at 0x62E80, then hands
                        # the handle to the real decoder at 0x6D970.
                        for delta, role in ((0xAA40, "decoder"), (-0xB0, "filter")):
                            body = fault + delta
                            if body in breakpoints:
                                continue
                            original = read_memory(process, body, 1)
                            if original and write_memory(process, body, INT3):
                                breakpoints[body] = original
                                state[f"hook_{role}"] = body
                                log(
                                    {
                                        "event": "bp-armed",
                                        "rva": hex(body - (module_base or 0)),
                                        "role": role,
                                    }
                                )
                        if args.guard:
                            state["guard_start"] = True
                    if handle and context.get(handle):
                        log(
                            {
                                "event": "bp-hit",
                                "rva": hex(fault - (module_base or 0)),
                                "eip": hex(fault),
                                "eax": hex(context.u32(CTX_EAX)),
                                "ecx": hex(context.u32(CTX_ECX)),
                                "edx": hex(context.u32(CTX_EDX)),
                                "esp": hex(context.u32(CTX_ESP)),
                                "ecx_mem": read_memory(
                                    process, context.u32(CTX_ECX), 16
                                ).hex(),
                            }
                        )
                        write_memory(process, fault, breakpoints[fault])
                        context.put_u32(CTX_EIP, fault)
                        context.put_u32(
                            CTX_EFLAGS, context.u32(CTX_EFLAGS) | EFLAGS_TRAP
                        )
                        context.set(handle)
                        pending[fault] = tid
                        if fault - (module_base or 0) in state["oparray_sites"]:
                            # 0x63048 is `pop edi`; the op_array is still in esi.
                            op_array = context.u32(CTX_ESI)
                            raw = read_memory(process, op_array, 0x80)
                            words = (
                                [hex(v) for v in struct.unpack("<32I", raw)]
                                if len(raw) == 0x80
                                else []
                            )
                            last = (
                                struct.unpack_from("<I", raw, 32)[0]
                                if len(raw) == 0x80
                                else 0
                            )
                            opcodes = (
                                struct.unpack_from("<I", raw, 36)[0]
                                if len(raw) == 0x80
                                else 0
                            )
                            body = read_memory(process, opcodes, 0x200) if opcodes else b""
                            if args.dump_to and raw:
                                args.dump_to.parent.mkdir(
                                    parents=True, exist_ok=True
                                )
                                args.dump_to.write_bytes(
                                    raw + (b"\n" + body if body else b"")
                                )
                            log(
                                {
                                    "event": "oparray",
                                    "rva": hex(fault - (module_base or 0)),
                                    "op_array": hex(op_array),
                                    "words": words,
                                    "last": last,
                                    "opcodes": hex(opcodes),
                                    "ops_head": body[:96].hex(),
                                    "saved": str(args.dump_to) if raw else None,
                                }
                            )
                        if fault - (module_base or 0) in state["dump_sites"]:
                            buffer = context.u32(CTX_ECX)
                            length = context.u32(CTX_EDX)
                            payload = (
                                read_memory(process, buffer, length)
                                if length < 0x400000
                                else b""
                            )
                            if args.dump_to and payload:
                                args.dump_to.parent.mkdir(
                                    parents=True, exist_ok=True
                                )
                                args.dump_to.write_bytes(payload)
                            log(
                                {
                                    "event": "dump-buffer",
                                    "rva": hex(fault - (module_base or 0)),
                                    "buffer": hex(buffer),
                                    "length": length,
                                    "saved": str(args.dump_to) if payload else None,
                                    "head": payload[:64].hex(),
                                }
                            )
                else:
                    status = DBG_EXCEPTION_NOT_HANDLED
            finally:
                if handle:
                    kernel32.CloseHandle(handle)
        elif code == EXIT_PROCESS_DEBUG_EVENT:
            log({"event": "exit", "code": struct.unpack_from("<I", event, base_off)[0]})
            state["done"] = True

        kernel32.ContinueDebugEvent(ev_pid, tid, status)

    args.log.parent.mkdir(parents=True, exist_ok=True)
    args.log.write_text(
        "\n".join(json.dumps(record) for record in records) + "\n", encoding="utf-8"
    )
    print(
        json.dumps(
            {
                "records": len(records),
                "watch_address": hex(state["watch_address"]),
                "hits": state["hits"],
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
