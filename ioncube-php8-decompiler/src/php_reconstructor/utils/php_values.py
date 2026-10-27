"""Helpers for the `safe_value` wrappers used by icdump-ir-v1 dumps.

The dump never emits raw PHP values directly; every literal / name / table
entry is wrapped as::

    {"type": "string", "length": 5, "printable": true,
     "value": "query", "hex": "...", "base64": "...", "sha1": "..."}

Non-printable strings carry ``"value": null`` and must be recovered from
``hex``.  Arrays nest recursively (``{"type": "array", "value": {...}}``).
"""

from __future__ import annotations

import re
from typing import Any, Optional

_IDENT_RE = re.compile(r"^[A-Za-z_\x80-\xff][A-Za-z0-9_\x80-\xff]*$")


class PhpBytes(bytes):
    """A PHP string whose bytes are not printable text.

    Kept distinct from ``bytes`` so emitters can choose a hex/escape
    representation while ordinary strings stay ``str``.
    """

    def __repr__(self) -> str:  # pragma: no cover - cosmetic
        return f"PhpBytes({bytes.__repr__(self)})"


def is_valid_php_identifier(name: object) -> bool:
    return isinstance(name, str) and bool(_IDENT_RE.match(name))


def unwrap_safe_value(node: Any) -> Any:
    """Convert a safe_value wrapper into a plain Python value.

    Scalars map to int/float/str/bool/None; non-printable strings map to
    :class:`PhpBytes`; arrays map to dict (preserving keys/order).  Values
    that are not safe_value wrappers are returned unchanged so the loader
    can call this defensively.
    """
    if not isinstance(node, dict) or "type" not in node:
        return node

    kind = node.get("type")
    if kind == "array":
        raw = node.get("value")
        if isinstance(raw, dict):
            return {key: unwrap_safe_value(item) for key, item in raw.items()}
        if isinstance(raw, list):
            return {index: unwrap_safe_value(item) for index, item in enumerate(raw)}
        return {}
    if kind == "string":
        value = node.get("value")
        if isinstance(value, str):
            return value
        hex_payload = node.get("hex")
        if isinstance(hex_payload, str) and hex_payload:
            try:
                return PhpBytes(bytes.fromhex(hex_payload))
            except ValueError:
                pass
        return PhpBytes(b"")
    # null / bool / int / integer / float / double and anything scalar-ish.
    return node.get("value")


# ---------------------------------------------------------------------------
# ionCube binary constant-array decoder
# ---------------------------------------------------------------------------
# ionCube compiles PHP array literals with all-constant values into a binary
# format and stores them as IS_CONST string literals.  The format is:
#
#   array    = '[' entry* '}' trailer
#   entry    = str_entry | int_entry
#   str_entry= DIGITS "'" KEY_BYTES type_value metadata
#   int_entry= DIGITS ":" DIGITS type_value [metadata]
#   type_value:
#     's' DIGITS "'" VALUE_BYTES   → str (4 metadata fields)
#     'i' DIGITS ";"               → int (2 metadata fields)
#     'd' DIGITS ";"               → float (2 metadata fields)
#     'b' DIGITS ";"               → bool (2 metadata fields)
#     '[' entry* '}' trailer       → sub-array (0 extra metadata fields)
#   trailer  = 5× (DIGITS ";")
#   metadata = N× (DIGITS ";")     (N given by type_value)


class _IonCubeArrayParser:
    __slots__ = ('_d', '_p')

    def __init__(self, data: bytes) -> None:
        self._d = data
        self._p = 0

    def _read_byte(self) -> int:
        b = self._d[self._p]
        self._p += 1
        return b

    def _expect(self, ch: str) -> None:
        b = self._read_byte()
        if b != ord(ch):
            raise ValueError(f"expected {ch!r}, got {chr(b)!r} at pos {self._p - 1}")

    def _read_digits(self) -> str:
        start = self._p
        while self._p < len(self._d) and 48 <= self._d[self._p] <= 57:
            self._p += 1
        if self._p == start:
            raise ValueError(f"expected digits at pos {self._p}")
        return self._d[start:self._p].decode('ascii')

    def _read_until_semi(self) -> str:
        start = self._p
        while self._p < len(self._d) and self._d[self._p] != 59:  # ord(';')
            self._p += 1
        result = self._d[start:self._p].decode('ascii')
        self._p += 1  # skip ';'
        return result

    def _skip_fields(self, n: int) -> None:
        for _ in range(n):
            self._read_until_semi()

    def _read_n_bytes(self, n: int) -> bytes:
        chunk = self._d[self._p:self._p + n]
        if len(chunk) < n:
            raise ValueError("truncated payload")
        self._p += n
        return chunk

    def read_array(self) -> list:
        self._expect('[')
        entries: list = []
        while self._p < len(self._d):
            b = self._d[self._p]
            if b == 125:  # ord('}')
                self._p += 1
                self._skip_fields(5)  # fixed-size array trailer
                break
            if 48 <= b <= 57:  # digit → start of an entry
                entries.append(self._read_entry())
            else:
                raise ValueError(f"unexpected 0x{b:02x} in array at pos {self._p}")
        return entries

    def _read_entry(self) -> tuple:
        num_str = self._read_digits()
        nxt = self._d[self._p] if self._p < len(self._d) else 0

        if nxt == 58:  # ord(':') → integer-keyed entry
            self._p += 1
            key = int(self._read_digits())
            value, meta = self._read_typed_value()
            if meta:
                self._skip_fields(meta)
            return (key, value)

        if nxt == 39:  # ord("'") → string-keyed entry
            key_len = int(num_str)
            self._p += 1  # skip "'"
            raw_key = self._read_n_bytes(key_len)
            try:
                key: Any = raw_key.decode('utf-8')
            except UnicodeDecodeError:
                key = raw_key.decode('latin-1')
            value, meta = self._read_typed_value()
            if meta:
                self._skip_fields(meta)
            return (key, value)

        raise ValueError(f"expected ':' or \"'\" after digits, got 0x{nxt:02x}")

    def _read_typed_value(self) -> tuple:
        """Return (value, metadata_field_count)."""
        b = self._read_byte()
        ch = chr(b)

        if ch == 's':
            n = int(self._read_digits())
            self._expect("'")
            raw = self._read_n_bytes(n)
            try:
                return raw.decode('utf-8'), 4
            except UnicodeDecodeError:
                return PhpBytes(raw), 4

        if ch == 'i':
            return int(self._read_until_semi()), 2

        if ch == 'd':
            return float(self._read_until_semi()), 2

        if ch == 'b':
            return bool(int(self._read_until_semi())), 2

        if ch == '[':
            self._p -= 1  # put '[' back; read_array() will consume it
            return self.read_array(), 0

        raise ValueError(f"unknown value type {ch!r} at pos {self._p - 1}")


def try_decode_ioncube_array(data: bytes) -> Optional[list]:
    """Try to parse *data* as ionCube's binary constant-array format.

    Returns a list of ``(key, value)`` pairs on success, or *None* if the
    data does not look like this format.  Keys are ``int`` or ``str``; values
    are ``int``, ``float``, ``str``, ``bool``, :class:`PhpBytes`, or a nested
    list of ``(key, value)`` pairs.
    """
    if not data or data[0:1] != b'[':
        return None
    try:
        parser = _IonCubeArrayParser(data)
        result = parser.read_array()
        return result
    except Exception:
        return None
