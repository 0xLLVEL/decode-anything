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

from engines.ioncube.dumper import _constant_ref_name, _consume_class_tail
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


def _property_84(name, default_index, flags, doc=None, type_bytes=b"\0\0\0\0"):
    return b"".join(
        [
            _buffer(name.encode("ascii")),
            _u32(default_index),
            _u32(flags),
            _sstring(doc.encode("utf-8") if doc else None),
            _u32(0x80000000),  # no attributes
            type_bytes,
            _u32(0),           # no property hooks
        ]
    )


def _property_83(name, flags, doc=None, type_bytes=b"\0\0\0\0"):
    return b"".join(
        [
            _buffer(name.encode("ascii")),
            _u32(flags),
            _sstring(doc.encode("utf-8") if doc else None),
            _u32(0x80000000),
            type_bytes,
        ]
    )


def _constant_84(name, payload, type_bytes=b"\0\0\0\0"):
    return b"".join(
        [
            _sstring(name.encode("ascii")),
            _buffer(payload),
            _sstring(None),              # constant doc-comment
            _u32(0x80000000),            # no attributes
            type_bytes,
        ]
    )


def _tail_after_constants():
    return b"".join(
        [
            _u32(0), _u32(0), _u32(0),  # trait names / aliases / insteadof
            _u32(0x80000000),  # class attributes
            _u32(0),           # info buffer absent
            _u32(0), _u32(0),  # metadata words
            _u32(0x80000000),  # class doc-comment
        ]
    )


def _tail_epilogue():
    return _u32(0) + _tail_after_constants()  # no class constants


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


def test_php84_property_types_keep_nullable_and_union_members():
    nullable_int = _u32((1 << 4) | (1 << 1))           # ?int
    int_or_string = _u32((1 << 4) | (1 << 6))          # int|string
    nullable_foo = _u32(0x01000000 | (1 << 1)) + _sstring(b"Foo")
    foo_or_bar = b"".join(
        [
            _u32(0x00400000),
            _u32(2),
            _u32(0x01000000) + _sstring(b"Foo"),
            _u32(0x01000000) + _sstring(b"Bar"),
        ]
    )
    buf = b"".join(
        [
            _value_table([]),
            _value_table([]),
            _u32(0), _u32(0),
            _u32(4),
            _property_84("count", 0, 0x04, type_bytes=nullable_int),
            _property_84("label", 0, 0x01, type_bytes=int_or_string),
            _property_84("foo", 0, 0x01, type_bytes=nullable_foo),
            _property_84("pair", 0, 0x01, type_bytes=foo_or_bar),
        ]
    ) + _tail_epilogue()

    tail = _consume_class_tail(buf, 0, php_version=84)

    assert tail["next_offset"] == len(buf)
    count, label, foo, pair = tail["properties"]
    assert (count["type_name"], count["allow_null"]) == ("int", True)
    assert (label["type_name"], label["allow_null"]) == ("int|string", False)
    assert (foo["type_name"], foo["allow_null"]) == ("Foo", True)
    assert (pair["type_name"], pair["allow_null"]) == ("Foo|Bar", False)


def test_php84_constants_keep_values_including_explicit_null():
    buf = b"".join(
        [
            _value_table([]),
            _value_table([]),
            _u32(0), _u32(0),
            _u32(0),                     # no properties
            _u32(2),                     # two constants
            _constant_84("FLAG", b"\x81i1;4;1;"),
            _constant_84("NOTHING", b"\x81n0;0;"),
        ]
    ) + _tail_after_constants()

    tail = _consume_class_tail(buf, 0, php_version=84)

    assert tail["next_offset"] == len(buf)
    flag, nothing = tail["constants"]
    assert (flag["name"], flag["has_value"], flag["value"]) == ("FLAG", True, 1)
    assert (nothing["name"], nothing["has_value"], nothing["value"]) == ("NOTHING", True, None)


def test_php84_constant_expression_ast_is_decoded():
    payload = b"\x81@:65:2048:14;s26'RSThemes\\View\\RSTHEMES_DIR"
    buf = b"".join(
        [
            _value_table([]),
            _value_table([]),
            _u32(0), _u32(0),
            _u32(0),                     # no properties
            _u32(1),                     # one constant
            _constant_84("MODULE_ADDON", payload),
        ]
    ) + _tail_after_constants()

    tail = _consume_class_tail(buf, 0, php_version=84)

    assert tail["next_offset"] == len(buf)
    constant = tail["constants"][0]
    assert constant["has_value"] is False
    assert constant["constant_ref"] == {
        "name": "RSThemes\\View\\RSTHEMES_DIR",
        "unqualified": True,
    }


def test_constant_ref_name_keeps_namespace_semantics():
    assert _constant_ref_name(
        "RSThemes\\View\\RSTHEMES_DIR", True, "RSThemes\\View\\ViewHelper"
    ) == "RSTHEMES_DIR"
    assert _constant_ref_name("RSTHEMES_DIR", True, "ViewHelper") == "RSTHEMES_DIR"
    assert _constant_ref_name("Foo\\BAR", True, "A\\B") == "\\Foo\\BAR"
    assert _constant_ref_name("Foo\\BAR", False, "A\\B") == "\\Foo\\BAR"


def test_php84_constant_expression_reaches_the_emitted_class():
    dump = {
        "format": "icdump-ir-v1",
        "source_file": "tail.php",
        "entry": "main",
        "op_arrays": {},
        "class_index": {
            "class:x": {
                "id": "class:x",
                "name": "RSThemes\\View\\ViewHelper",
                "constants_table": {
                    "MODULE_ADDON": {"value": {"__constant_ref__": "RSTHEMES_DIR"}},
                    "OTHER": {"value": {"__constant_ref__": "\\App\\OTHER"}},
                },
            }
        },
    }

    code = emit_php(optimize(decompile_program(parse_dump(dump))))

    assert "const MODULE_ADDON = RSTHEMES_DIR;" in code
    assert "const OTHER = \\App\\OTHER;" in code


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
                        "type_name": "int",
                        "allow_null": True,
                        "has_default_value": True,
                        "default_value": {"type": "int", "value": 7},
                    },
                    "answer": {
                        "flags_decoded": {"visibility": "public", "is_static": True},
                        "is_static": True,
                        "type_name": "bool",
                        "allow_null": False,
                        "has_default_value": True,
                        "default_value": {"type": "bool", "value": True},
                    },
                    "label": {
                        "flags_decoded": {"visibility": "protected", "is_static": False},
                        "is_static": False,
                        "type_name": "int|string",
                        "allow_null": False,
                        "has_default_value": False,
                    },
                },
                "constants_table": {
                    "FLAG": {"value": {"type": "int", "value": 1}},
                    "NAME": {"value": {"type": "string", "value": "x"}},
                },
            }
        },
    }

    code = emit_php(optimize(decompile_program(parse_dump(dump))))

    assert "const FLAG = 1;" in code
    assert "const NAME = 'x';" in code
    assert "private ?int $count = 7;" in code
    assert "public static bool $answer = true;" in code
    assert "protected int|string $label;" in code
