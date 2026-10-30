"""Arm a hardware watchpoint on the ionCube 7.2 record and catch its reader.

The loader writes the decompressed body into a fresh private region; the record
inside it always starts with ``FF FF FF FF <len>`` and a per-file ciphertext
block.  A poller watches for that signature, then arms Dr0..Dr3 over the
record's first 16 bytes on every thread of the target.  Dr6 tells us the first
instruction that touches those bytes, which is the record decode routine.

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

PAGE_READWRITE = 0x04
PAGE_EXECUTE_READWRITE = 0x40

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

THREAD_GET_CONTEXT = 0x0008
THREAD_SET_CONTEXT = 0x0010
THREAD_SUSPEND_RESUME = 0x0002
TH32CS_SNAPTHREAD = 0x00000004
FACTORY_SIGNATURE = bytes.fromhex("a1a0cb0b10")


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


class THREADENTRY32(ctypes.Structure):
    _fields_ = [
        ("dwSize", wt.DWORD),
        ("cntUsage", wt.DWORD),
        ("th32ThreadID", wt.DWORD),
        ("th32OwnerProcessID", wt.DWORD),
        ("tpBasePri", wt.LONG),
        ("tpDeltaPri", wt.LONG),
        ("dwFlags", wt.DWORD),
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
kernel32.SuspendThread.argtypes = [wt.HANDLE]
kernel32.ResumeThread.argtypes = [wt.HANDLE]
kernel32.CreateToolhelp32Snapshot.argtypes = [wt.DWORD, wt.DWORD]
kernel32.CreateToolhelp32Snapshot.restype = wt.HANDLE
kernel32.Thread32First.argtypes = [wt.HANDLE, ctypes.POINTER(THREADENTRY32)]
kernel32.Thread32First.restype = wt.BOOL
kernel32.Thread32Next.argtypes = [wt.HANDLE, ctypes.POINTER(THREADENTRY32)]
kernel32.Thread32Next.restype = wt.BOOL
kernel32.CloseHandle.argtypes = [wt.HANDLE]


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


def thread_ids(pid: int) -> list[int]:
    snapshot = kernel32.CreateToolhelp32Snapshot(TH32CS_SNAPTHREAD, 0)
    if not snapshot or snapshot == -1:
        return []
    entry = THREADENTRY32()
    entry.dwSize = ctypes.sizeof(THREADENTRY32)
    found: list[int] = []
    try:
        if kernel32.Thread32First(snapshot, ctypes.byref(entry)):
            while True:
                if entry.th32OwnerProcessID == pid:
                    found.append(int(entry.th32ThreadID))
                if not kernel32.Thread32Next(snapshot, ctypes.byref(entry)):
                    break
    finally:
        kernel32.CloseHandle(snapshot)
    return found


def arm_thread(tid: int, address: int) -> bool:
    handle = kernel32.OpenThread(
        THREAD_GET_CONTEXT | THREAD_SET_CONTEXT | THREAD_SUSPEND_RESUME, False, tid
    )
    if not handle:
        return False
    context = Wow64Context()
    try:
        kernel32.SuspendThread(handle)
        try:
            if not context.get(handle):
                return False
            context.arm(address)
            return context.set(handle)
        finally:
            kernel32.ResumeThread(handle)
    finally:
        kernel32.CloseHandle(handle)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--php", required=True, type=Path)
    parser.add_argument("--loader", required=True, type=Path)
    parser.add_argument("--target", required=True, type=Path)
    parser.add_argument(
        "--marker",
        default="ffffffff68020000f885d77d18f94c83",
        help="first bytes of the encoded record to watch for",
    )
    parser.add_argument("--log", type=Path, default=Path("scratch/ic72_blob_watch.jsonl"))
    parser.add_argument("--timeout", type=float, default=60.0)
    parser.add_argument("--show-output", action="store_true")
    parser.add_argument("--size-min", type=lambda v: int(v, 0), default=0x80000)
    parser.add_argument("--size-max", type=lambda v: int(v, 0), default=0x100000)
    parser.add_argument(
        "--bp",
        action="append",
        default=[],
        help="loader RVA to break on (hex), logged with ecx/esi/ebx/edi",
    )
    args = parser.parse_args()

    marker = bytes.fromhex(args.marker)
    ini = Path(tempfile.gettempdir()) / "ic72_blob_watch.ini"
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
    started = time.monotonic()
    state = {
        "watch_address": 0,
        "hits": 0,
        "stop_polling": False,
        "done": False,
    }

    def log(entry: dict[str, object]) -> None:
        entry["t"] = round(time.monotonic() - started, 4)
        records.append(entry)
        print(json.dumps(entry), flush=True)

    def marker_worker() -> None:
        deadline = time.monotonic() + args.timeout
        while time.monotonic() < deadline and not state["done"]:
            if state["stop_polling"]:
                time.sleep(0.001)
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
                    and args.size_min <= size <= args.size_max
                ):
                    data = read_memory(process, region.BaseAddress, size)
                    index = data.find(marker) if data else -1
                    if index >= 0:
                        target = region.BaseAddress + index
                        state["stop_polling"] = True
                        state["watch_address"] = target
                        armed = [
                            tid for tid in thread_ids(pid) if arm_thread(tid, target)
                        ]
                        log(
                            {
                                "event": "watch-armed",
                                "address": hex(target),
                                "region": hex(region.BaseAddress),
                                "offset": hex(index),
                                "threads": armed,
                                "record_hex": data[index : index + 64].hex(),
                            }
                        )
                        return
                address += size or 0x1000
            time.sleep(0.002)

    threading.Thread(target=marker_worker, daemon=True).start()

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
                    log(
                        {
                            "event": "loader-base",
                            "base": hex(dll_base),
                            "prng_probe": read_memory(
                                process, dll_base + 0x88C40, 16
                            ).hex(),
                            "decode_probe": read_memory(
                                process, dll_base + 0x69C52, 8
                            ).hex(),
                        }
                    )
                    symbol = find_export(process, dll_base, "zend_compile_file")
                    if symbol:
                        pointer = read_memory(process, symbol, 4)
                        hook = struct.unpack_from("<I", pointer, 0)[0] if pointer else 0
                        log(
                            {
                                "event": "compile-hook",
                                "hook": hex(hook),
                                "in_loader": bool(
                                    module_base <= hook < module_base + 0x100000
                                ),
                            }
                        )
                        if module_base <= hook < module_base + 0x100000:
                            original = read_memory(process, hook, 1)
                            if original and write_memory(process, hook, b"\xcc"):
                                breakpoints[hook] = original
                    for spec in args.bp:
                        target = dll_base + int(spec, 0)
                        if target in breakpoints:
                            continue
                        original = read_memory(process, target, 1)
                        if original and write_memory(process, target, b"\xcc"):
                            breakpoints[target] = original
                            log(
                                {
                                    "event": "bp-armed",
                                    "rva": hex(target - dll_base),
                                    "base": hex(dll_base),
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
                if exception_code in SINGLE_STEP_CODES:
                    dr6 = 0
                    if handle and context.get(handle):
                        dr6 = context.u32(CTX_DR6)
                    if dr6 & 0xF:
                        state["hits"] += 1
                        entry: dict[str, object] = {
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
                            entry["stack"] = [
                                hex(v) for v in struct.unpack("<10I", stack)
                            ]
                        entry["bytes"] = read_memory(
                            process, state["watch_address"], 32
                        ).hex()
                        log(entry)
                        context.disarm()
                        context.set(handle)
                        if state["hits"] >= 6:
                            state["stop_polling"] = True
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
                        esp = context.u32(CTX_ESP)
                        stack = read_memory(process, esp, 40)
                        caller = (
                            struct.unpack_from("<I", stack, 0)[0] if len(stack) >= 4 else 0
                        )
                        entry: dict[str, object] = {
                            "event": breakpoints[fault]
                            and f"hit:{hex(fault - module_base)}"
                            or "hit",
                            "eip": hex(fault),
                            "caller": hex(caller),
                            "caller_rva": hex(caller - module_base)
                            if module_base
                            else None,
                            "eax": hex(context.u32(CTX_EAX)),
                            "ecx": hex(context.u32(CTX_ECX)),
                            "edx": hex(context.u32(CTX_EDX)),
                            "esi": hex(context.u32(CTX_ESI)),
                            "edi": hex(context.u32(CTX_EDI)),
                            "ebx": hex(context.u32(CTX_EBX)),
                        }
                        state_ptr = context.u32(CTX_ECX)
                        entry["ecx_mem"] = read_memory(process, state_ptr, 16).hex()
                        entry["esi_mem"] = read_memory(
                            process, context.u32(CTX_ESI), 24
                        ).hex()
                        log(entry)
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
