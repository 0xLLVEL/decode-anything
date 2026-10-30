"""Regression tests for the ionCube class-tail parser.

PHP 8.4 changed the property record: an explicit default-value index precedes
the flags and a property-hook count follows the type.  The class-tail parser
must consume that layout byte-for-byte so the next class record stays aligned,
and the recovered properties must reach the emitter.
"""

import struct
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1] / "ioncube-php8-decompiler" / "src"))

from engines.ioncube.dumper import _consume_class_tail
from php_reconstructor.decompiler.optimize import optimize
from php_reconstructor.decompiler.program import decompile_program
from php_reconstructor.emitter.php_emitter import emit_php
from php_reconstructor.loader import parse_dump


def _u32(value):
    return struct.pack("<I", value)


def _buffer(payload):
    if payload is None:
        return _u32(0x80000000)
    return _u32(0x20000000 | len(payload)) + payload


def _sstring(payload):
    if payload is None:
        return _u32(0x80000000)
    return _u32(0x20000000 | len(payload)) + payload


def _value_table(values):
    return _u32(len(values)) + b"".join(_buffer(value) for value in values)


def _property_84(name, default_index, flags, doc=None):
    return b"".join(
        [
            _buffer(name.encode("ascii")),
            _u32(default_index),
            _u32(flags),
            _sstring(doc.encode("utf-8") if doc else None),
            _u32(0x80000000),  # no attributes
            _u32(0),           # no type
            _u32(0),           # no property hooks
        ]
    )


def _property_83(name, flags, doc=None):
    return b"".join(
        [
            _buffer(name.encode("ascii")),
            _u32(flags),
            _sstring(doc.encode("utf-8") if doc else None),
            _u32(0x80000000),
            _u32(0),
        ]
    )


def _tail_epilogue():
    return b"".join(
        [
            _u32(0),           # class constants
            _u32(0), _u32(0), _u32(0),  # trait names / aliases / insteadof
            _u32(0x80000000),  # class attributes
            _u32(0),           # info buffer absent
            _u32(0), _u32(0),  # metadata words
            _u32(0x80000000),  # class doc-comment
        ]
    )


def test_php84_property_table_uses_default_index_and_hook_count():
    buf = b"".join(
        [
            _value_table([b"\x81i7;4;0;"]),   # instance default: 7
            _value_table([b"\x81t3;0;"]),      # static default: true
            _u32(0), _u32(0),                  # 8.4 class-level counts
            _u32(2),                           # two properties
            _property_84("count", 0, 0x04, "/** @var int $count */"),
            _property_84("answer", 0, 0x11, "/** @var bool $answer */"),
        ]
    ) + _tail_epilogue()

    tail = _consume_class_tail(buf, 0, php_version=84)

    assert tail["next_offset"] == len(buf)
    count, answer = tail["properties"]
    assert count["name"] == "count"
    assert count["visibility"] == "private"
    assert count["is_static"] is False
    assert count["has_default"] is True
    assert count["default"] == 7
    assert count["doc_comment"] == "/** @var int $count */"
    assert answer["name"] == "answer"
    assert answer["visibility"] == "public"
    assert answer["is_static"] is True
    assert answer["default"] is True


def test_php83_property_table_keeps_declaration_order_defaults():
    buf = b"".join(
        [
            _value_table([b"\x81i7;4;0;"]),
            _value_table([b"\x81t3;0;"]),
            _u32(2),
            _property_83("count", 0x04),
            _property_83("answer", 0x11),
        ]
    ) + _tail_epilogue()

    tail = _consume_class_tail(buf, 0, php_version=83)

    assert tail["next_offset"] == len(buf)
    count, answer = tail["properties"]
    assert count["default"] == 7
    assert answer["default"] is True


def test_php84_properties_reach_the_emitted_class():
    dump = {
        "format": "icdump-ir-v1",
        "source_file": "tail.php",
        "entry": "main",
        "op_arrays": {},
        "class_index": {
            "class:x": {
                "id": "class:x",
                "name": "X",
                "properties_info": {
                    "count": {
                        "flags_decoded": {"visibility": "private", "is_static": False},
                        "is_static": False,
                        "has_default_value": True,
                        "default_value": {"type": "int", "value": 7},
                    },
                    "answer": {
                        "flags_decoded": {"visibility": "public", "is_static": True},
                        "is_static": True,
                        "has_default_value": True,
                        "default_value": {"type": "bool", "value": True},
                    },
                },
            }
        },
    }

    code = emit_php(optimize(decompile_program(parse_dump(dump))))

    assert "private $count = 7;" in code
    assert "public static $answer = true;" in code
