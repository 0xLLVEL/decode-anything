"""Spawn the vendored PHP 7.2 under Frida and log the opcode-mask seeds.

The sample loads on this machine, so the mask is generated here. This driver
runs the loader under tools/ic72_mask_hook.js and prints the generator context.
"""

import sys
import time
from pathlib import Path

import frida

RUNTIME = Path(r"C:\Users\ezan\Documents\decode-anything\scratch\refs\ic72dump-opcodes\runtime")
SAMPLE = Path(r"C:\Users\ezan\Documents\samples\binancepay_asli.php")
HOOK = Path(r"C:\Users\ezan\Documents\decode-anything\tools\ic72_mask_hook.js")


def main():
    device = frida.get_local_device()
    argv = [str(RUNTIME / "php.exe"), "-n", "-c", "php.ini", r"C:\Users\ezan\Documents\decode-anything\scratch\hook_wrapper.php"]
    pid = device.spawn(argv, cwd=str(RUNTIME))
    print("spawned pid", pid)

    session = device.attach(pid)
    script = session.create_script(HOOK.read_text(encoding="utf-8"))

    def on_message(message, data):
        if message.get("type") == "log":
            print("LOG:", message["payload"])
        elif message.get("type") == "error":
            print("ERR:", message.get("stack") or message.get("description"))

    script.on("message", on_message)
    script.load()
    device.resume(pid)
    time.sleep(8)
    try:
        session.detach()
    except Exception:
        pass
    print("done")


if __name__ == "__main__":
    sys.exit(main())

