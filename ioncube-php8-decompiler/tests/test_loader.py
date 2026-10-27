"""Milestone 1: loader and safe_value unwrapping."""

import pytest

from conftest import const, cv, dump, op, op_array, sv
from php_reconstructor.loader import DumpFormatError, parse_dump
from php_reconstructor.utils import unwrap_safe_value
from php_reconstructor.utils.php_values import PhpBytes


class TestSafeValue:
    def test_scalars(self):
        assert unwrap_safe_value(sv(None)) is None
        assert unwrap_safe_value(sv(True)) is True
        assert unwrap_safe_value(sv(42)) == 42
        assert unwrap_safe_value(sv(1.5)) == 1.5
        assert unwrap_safe_value(sv("hello")) == "hello"

    def test_non_printable_string_recovered_from_hex(self):
        node = {"type": "string", "length": 3, "printable": False, "value": None, "hex": "001122"}
        result = unwrap_safe_value(node)
        assert isinstance(result, PhpBytes)
        assert bytes(result) == b"\x00\x11\x22"

    def test_nested_array(self):
        node = sv({"a": 1, "b": [2, 3]})
        assert unwrap_safe_value(node) == {"a": 1, "b": {0: 2, 1: 3}}

    def test_passthrough_for_plain_values(self):
        assert unwrap_safe_value(7) == 7
        assert unwrap_safe_value("raw") == "raw"


class TestParseDump:
    def test_minimal_dump(self):
        program = parse_dump(dump(main_ops=[op("ZEND_RETURN", op1=const(1))]))
        assert program.dump_format == "icdump-ir-v1"
        assert program.main is not None
        assert program.main.kind == "main"
        assert len(program.main.opcodes) == 1
        assert program.main.opcodes[0].name == "ZEND_RETURN"

    def test_rejects_non_object(self):
        with pytest.raises(DumpFormatError):
            parse_dump([1, 2, 3])

    def test_rejects_missing_op_arrays(self):
        with pytest.raises(DumpFormatError):
            parse_dump({"format": "icdump-ir-v1"})

    def test_function_and_vars(self):
        oa = op_array(
            [op("ZEND_RETURN", op1=cv(0, "x"))],
            name="myFunc",
            cvs=["x"],
        )
        program = parse_dump(dump(main_ops=[], functions={"myfunc": oa}))
        funcs = program.functions()
        assert len(funcs) == 1
        assert funcs[0].function_name == "myFunc"
        assert funcs[0].vars == ["x"]

    def test_class_index_parsed(self):
        class_raw = {
            "name": sv("Foo"),
            "parent": sv("Bar"),
            "interfaces": ["Countable"],
            "ce_flags_decoded": {"is_final": True},
            "constants_table": {"VERSION": {"value": sv("1.0")}},
            "properties_merged": {
                "items": {
                    "name": "items",
                    "flags_decoded": {"visibility": "private"},
                    "is_static": False,
                    "has_default_value": True,
                    "default_value": sv([]),
                }
            },
            "methods": {},
        }
        program = parse_dump(dump(main_ops=[], class_index={"class:466f6f": class_raw}))
        cls = program.classes["class:466f6f"]
        assert cls.name == "Foo"
        assert cls.parent == "Bar"
        assert cls.interfaces == ["Countable"]
        assert cls.is_final
        assert cls.constants == {"VERSION": "1.0"}
        assert cls.properties[0].visibility == "private"
        assert cls.properties[0].has_default
