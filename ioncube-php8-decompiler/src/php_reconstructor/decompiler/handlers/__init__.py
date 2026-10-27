"""Opcode handler registry.

Each handler is an isolated function registered for one or more opcode
names via :func:`opcode_handler`.  Handlers receive the active
:class:`~php_reconstructor.decompiler.context.DecompileContext` and the
current :class:`~php_reconstructor.opcode.Opcode`; they update temps /
emit statements and may return the number of opcodes consumed (default 1,
e.g. 2 when swallowing a trailing ``ZEND_OP_DATA``).
"""

from __future__ import annotations

from typing import Callable

from ...decompiler.context import DecompileContext
from ...opcode import Opcode

Handler = Callable[[DecompileContext, Opcode], int | None]

HANDLERS: dict[str, Handler] = {}


def opcode_handler(*names: str) -> Callable[[Handler], Handler]:
    def register(func: Handler) -> Handler:
        for name in names:
            if name in HANDLERS:
                raise ValueError(f"duplicate handler for {name}")
            HANDLERS[name] = func
        return func

    return register


def get_handler(name: str) -> Handler | None:
    return HANDLERS.get(name)


# Importing the modules below populates the registry.
from . import basic, calls, fetch, arrays, misc  # noqa: E402,F401

__all__ = ["HANDLERS", "Handler", "get_handler", "opcode_handler"]
