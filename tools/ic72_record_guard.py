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
    parser.add_argument("--log", type=Path, default=Path("scratch/ic72_record_guard.jsonl"))
    parser.add_argument("--timeout", type=float, default=60.0)
    parser.add_argument("--show-output", action="store_true")
    args = parser.parse_args()

    marker = bytes.fromhex(args.marker)
    ini = Path(tempfile.gettempdir()) / "ic72_record_guard.ini"
    ini.write_text(
        "[PHP]\r\n"
        "error_reporting = 0\r\n"
        "display_errors = On\r\n"
        f'zend_extension = "{args.loader.resolve()}"\r\n',
        encoding="utf-8",
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
    state = {"watch_address": 0, "hits": 0, "done": False, "guarded": 0}

    def log(entry: dict[str, object]) -> None:
        entry["t"] = round(time.monotonic() - started, 4)
        records.append(entry)
        print(json.dumps(entry), flush=True)

    def guard_worker() -> None:
        deadline = time.monotonic() + args.timeout
        while time.monotonic() < deadline and not state["done"]:
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
        while time.monotonic() < deadline and not state["done"] and module_base:
            for target in list(breakpoints):
                if target in pending:
                    continue
                if read_memory(process, target, 1) != INT3:
                    write_memory(process, target, INT3)
            time.sleep(0.002)

    if args.guard:
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
