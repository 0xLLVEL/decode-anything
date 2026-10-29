"""IonCube PHP 8.1 - 8.4 static bytecode decoder engine."""

from .header import (
    decode_file as decode_hrc_file,
    decode_payload_body,
    read_encoded_payload,
)
from .body import (
    LoaderHandlerTables,
    LoaderInternedStringResolver,
)
from .adapter import (
    build_op_array_entry,
    resolve_function_calls,
    safe_value,
)
from .dumper import (
    dump_file_to_ir,
    deobfuscate_cfg,
)

__all__ = [
    "decode_hrc_file",
    "decode_payload_body",
    "read_encoded_payload",
    "LoaderHandlerTables",
    "LoaderInternedStringResolver",
    "build_op_array_entry",
    "resolve_function_calls",
    "safe_value",
    "dump_file_to_ir",
    "deobfuscate_cfg",
]
