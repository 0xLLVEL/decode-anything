"""Zend engine constants needed to interpret PHP 8.1 opcodes."""

from __future__ import annotations

# zend_types.h type codes (used by ZEND_CAST extended_value).
CAST_TYPES: dict[int, str] = {
    4: "int",
    5: "float",
    6: "string",
    7: "array",
    8: "object",
    18: "bool",  # _IS_BOOL
}

# ZEND_ASSIGN_OP / ZEND_ASSIGN_DIM_OP extended_value -> binary opcode number.
# These are the opcode numbers of the corresponding binary operators.
ASSIGN_OP_BINOPS: dict[int, str] = {
    1: "+",
    2: "-",
    3: "*",
    4: "/",
    5: "%",
    6: "<<",
    7: ">>",
    8: ".",
    9: "|",
    10: "&",
    11: "^",
    12: "**",
}

# Binary opcodes -> PHP operator.
BINARY_OPS: dict[str, str] = {
    "ZEND_ADD": "+",
    "ZEND_SUB": "-",
    "ZEND_MUL": "*",
    "ZEND_DIV": "/",
    "ZEND_MOD": "%",
    "ZEND_POW": "**",
    "ZEND_SL": "<<",
    "ZEND_SR": ">>",
    "ZEND_CONCAT": ".",
    "ZEND_FAST_CONCAT": ".",
    "ZEND_BW_OR": "|",
    "ZEND_BW_AND": "&",
    "ZEND_BW_XOR": "^",
    "ZEND_BOOL_XOR": "xor",
    "ZEND_IS_EQUAL": "==",
    "ZEND_IS_NOT_EQUAL": "!=",
    "ZEND_IS_IDENTICAL": "===",
    "ZEND_IS_NOT_IDENTICAL": "!==",
    "ZEND_IS_SMALLER": "<",
    "ZEND_IS_SMALLER_OR_EQUAL": "<=",
    "ZEND_SPACESHIP": "<=>",
    "ZEND_CASE": "==",
    "ZEND_CASE_STRICT": "===",
}

# ZEND_INCLUDE_OR_EVAL extended_value.
INCLUDE_KINDS: dict[int, str] = {
    1: "eval",
    2: "include",
    4: "include_once",
    8: "require",
    16: "require_once",
}

# ZEND_TYPE_CHECK extended_value is a mask of (1 << IS_*) type bits.
# IS_UNDEF=0 IS_NULL=1 IS_FALSE=2 IS_TRUE=3 IS_LONG=4 IS_DOUBLE=5
# IS_STRING=6 IS_ARRAY=7 IS_OBJECT=8 IS_RESOURCE=9
TYPE_CHECK_FUNCS: dict[int, str] = {
    1 << 1: "is_null",
    (1 << 2) | (1 << 3): "is_bool",
    1 << 4: "is_int",
    1 << 5: "is_float",
    1 << 6: "is_string",
    1 << 7: "is_array",
    1 << 8: "is_object",
    1 << 9: "is_resource",
    (1 << 4) | (1 << 5): "is_numeric",  # not exact, kept for readability
}

# isset/empty discriminator on ZEND_ISSET_ISEMPTY_* extended_value.
ZEND_ISEMPTY = 1 << 0

# Opcodes that terminate a basic block without falling through.
NO_FALLTHROUGH = {
    "ZEND_JMP",
    "ZEND_RETURN",
    "ZEND_RETURN_BY_REF",
    "ZEND_THROW",
    "ZEND_EXIT",
    "ZEND_GENERATOR_RETURN",
}

# Conditional / multi-target branch opcodes (have jump_targets + fallthrough).
CONDITIONAL_JUMPS = {
    "ZEND_JMPZ",
    "ZEND_JMPNZ",
    "ZEND_JMPZNZ",
    "ZEND_JMPZ_EX",
    "ZEND_JMPNZ_EX",
    "ZEND_JMP_SET",
    "ZEND_COALESCE",
    "ZEND_FE_RESET_R",
    "ZEND_FE_RESET_RW",
    "ZEND_FE_FETCH_R",
    "ZEND_FE_FETCH_RW",
    "ZEND_ASSERT_CHECK",
    "ZEND_CATCH",
    "ZEND_SWITCH_LONG",
    "ZEND_SWITCH_STRING",
    "ZEND_MATCH",
}

# fn_flags bits (zend_compile.h) -- only the ones we render.
ZEND_ACC_PUBLIC = 1 << 0
ZEND_ACC_PROTECTED = 1 << 1
ZEND_ACC_PRIVATE = 1 << 2
ZEND_ACC_STATIC = 1 << 4
ZEND_ACC_FINAL = 1 << 5
ZEND_ACC_ABSTRACT = 1 << 6
