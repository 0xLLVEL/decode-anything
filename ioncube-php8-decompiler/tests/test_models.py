"""Milestone 1: Opcode/Operand model normalization."""

from conftest import const, cv, tmp, unused
from php_reconstructor.opcode import Opcode, Operand, OperandKind


class TestOperand:
    def test_kinds(self):
        assert Operand.from_json(unused()).kind is OperandKind.UNUSED
        assert Operand.from_json(const(1)).kind is OperandKind.CONST
        assert Operand.from_json(cv(0, "x")).kind is OperandKind.CV
        assert Operand.from_json(tmp(96)).kind is OperandKind.TMP

    def test_kind_from_numeric_mask_when_type_name_missing(self):
        # ionCube semantic-resolved opcodes: type 18 = flag bit | IS_TMP_VAR.
        raw = {"type": 18, "type_name": None, "var": 752}
        operand = Operand.from_json(raw)
        assert operand.kind is OperandKind.TMP
        assert operand.temp_key == 752

    def test_unused_garbage_is_not_a_temp(self):
        raw = dict(unused(), var=1022, num=1022)
        operand = Operand.from_json(raw)
        assert operand.temp_key is None
        assert operand.is_unused

    def test_literal_unwrapped(self):
        operand = Operand.from_json(const("hello"))
        assert operand.const_value() == "hello"

    def test_resolved_literal_wins(self):
        raw = const("raw_name")
        raw["resolved_literal"] = {"type": "string", "printable": True, "value": "real_name"}
        assert Operand.from_json(raw).const_value() == "real_name"

    def test_missing_operand(self):
        operand = Operand.from_json(None)
        assert operand.is_unused or operand.kind is OperandKind.UNUSED


class TestOpcode:
    def test_basic_fields(self):
        raw = {
            "index": 5,
            "opcode_name": "ZEND_ASSIGN",
            "opcode": 22,
            "extended_value": 0,
            "op1": cv(0, "x"),
            "op2": const(1),
            "result": unused(),
            "jump_targets": [],
        }
        opcode = Opcode.from_json(raw, 5)
        assert opcode.name == "ZEND_ASSIGN"
        assert opcode.number == 22
        assert opcode.short_name == "ASSIGN"
        assert opcode.op1.cv_name == "x"

    def test_jump_targets(self):
        raw = {"opcode_name": "ZEND_JMP", "jump_targets": [7]}
        assert Opcode.from_json(raw, 0).jump_targets == (7,)

    def test_invalid_payload(self):
        opcode = Opcode.from_json("garbage", 3)
        assert opcode.decode_failed
        assert opcode.index == 3
