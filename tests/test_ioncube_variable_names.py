"""ionCube 7.2 local variables arrive as `_obfuscated_<hex>_` placeholders.

The dumper hex-escapes the loader's encrypted 23-byte name blobs.  The encoder
mangled the identifiers before encrypting them, so the placeholder carries no
original name; it must at least be replaced consistently in the variable table
and in every CV operand, or the emitted PHP refers to variables it never sets.
"""

from __future__ import annotations

from engines.ioncube.adapter import build_op_array_entry

HEX = "_obfuscated_0D3718191A291940170D13174007222F3E343D23163501_"
HEX_2 = "_obfuscated_0D2101403936270F320C1211392B2C342F390F2B1A1622_"


def _cv(name: str, index: int) -> dict:
    return {
        "type": 8, "type_name": "IS_CV", "num": 32 + index * 16,
        "variable_name": name, "variable_index": index,
    }


def _const(index: int) -> dict:
    return {"type": 1, "type_name": "IS_CONST", "num": index, "constant": index}


RAW = {
    "method": "addNewsletters",
    "metadata": {"variables": ["group_id", HEX, HEX_2], "num_args": 1, "required_num_args": 1},
    "literals": [],
    "opcodes": [
        {"index": 0, "opcode_name": "ZEND_RECV", "op1": {"type": 8, "type_name": "IS_UNUSED"},
         "op2": {"type": 8, "type_name": "IS_UNUSED"}, "result": _cv("group_id", 0), "jump_targets": []},
        {"index": 1, "opcode_name": "ZEND_ASSIGN", "op1": _cv(HEX, 1), "op2": _const(0),
         "result": {"type": 8, "type_name": "IS_UNUSED"}, "jump_targets": []},
        {"index": 2, "opcode_name": "ZEND_ASSIGN", "op1": _cv(HEX_2, 2), "op2": _cv(HEX, 1),
         "result": {"type": 8, "type_name": "IS_UNUSED"}, "jump_targets": []},
        {"index": 3, "opcode_name": "ZEND_RETURN", "op1": _cv(HEX_2, 2),
         "op2": {"type": 8, "type_name": "IS_UNUSED"},
         "result": {"type": 8, "type_name": "IS_UNUSED"}, "jump_targets": []},
    ],
}


def test_obfuscated_variable_names_become_readable_and_consistent():
    _, entry = build_op_array_entry(RAW, "contacts.php")

    variables = [item["value"] for item in entry["vars"]["value"]]
    assert variables[0] == "group_id"
    assert all(not str(name).startswith("_obfuscated_") for name in variables)

    first, second = variables[1], variables[2]
    assert first != second
    assert entry["opcodes"][1]["op1"]["cv_name"] == first
    assert entry["opcodes"][2]["op1"]["cv_name"] == second
    assert entry["opcodes"][2]["op2"]["cv_name"] == first
    assert entry["opcodes"][3]["op1"]["cv_name"] == second
