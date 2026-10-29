#!/usr/bin/env python3
"""
sg_bytecode_ir.py — parse decrypted SourceGuardian body.bin into normalized
icdump-ir-v1 JSON and opcode listings.

Based on "SourceGuardian PHP 8.1 — Static Container & Bytecode Recovery Without Execution"
(https://www.amariei.org/sourceguardian-php81-static-decode.html).

Converts SourceGuardian bytecode containers to the unified `icdump-ir-v1` format
consumed directly by the `php_reconstructor` AST decompiler and emitter.
"""

from __future__ import annotations

import json
import os
import struct
import sys
from pathlib import Path
from .container import decode_bytes, decode_file, SGError


# ── PHP 8.1 opcode names, from Zend/zend_vm_opcodes.h ──────────────────────
OPCODE_NAMES = {
    0: 'ZEND_NOP', 1: 'ZEND_ADD', 2: 'ZEND_SUB', 3: 'ZEND_MUL', 4: 'ZEND_DIV',
    5: 'ZEND_MOD', 6: 'ZEND_SL', 7: 'ZEND_SR', 8: 'ZEND_CONCAT', 9: 'ZEND_BW_OR',
    10: 'ZEND_BW_AND', 11: 'ZEND_BW_XOR', 12: 'ZEND_POW', 13: 'ZEND_BW_NOT',
    14: 'ZEND_BOOL_NOT', 15: 'ZEND_BOOL_XOR', 16: 'ZEND_IS_IDENTICAL',
    17: 'ZEND_IS_NOT_IDENTICAL', 18: 'ZEND_IS_EQUAL', 19: 'ZEND_IS_NOT_EQUAL',
    20: 'ZEND_IS_SMALLER', 21: 'ZEND_IS_SMALLER_OR_EQUAL', 22: 'ZEND_ASSIGN',
    23: 'ZEND_ASSIGN_DIM', 24: 'ZEND_ASSIGN_OBJ', 25: 'ZEND_ASSIGN_STATIC_PROP',
    26: 'ZEND_ASSIGN_OP', 27: 'ZEND_ASSIGN_DIM_OP', 28: 'ZEND_ASSIGN_OBJ_OP',
    29: 'ZEND_ASSIGN_STATIC_PROP_OP', 30: 'ZEND_ASSIGN_REF', 31: 'ZEND_QM_ASSIGN',
    32: 'ZEND_ASSIGN_OBJ_REF', 33: 'ZEND_ASSIGN_STATIC_PROP_REF',
    34: 'ZEND_PRE_INC', 35: 'ZEND_PRE_DEC', 36: 'ZEND_POST_INC', 37: 'ZEND_POST_DEC',
    38: 'ZEND_PRE_INC_STATIC_PROP', 39: 'ZEND_PRE_DEC_STATIC_PROP',
    40: 'ZEND_POST_INC_STATIC_PROP', 41: 'ZEND_POST_DEC_STATIC_PROP',
    42: 'ZEND_JMP', 43: 'ZEND_JMPZ', 44: 'ZEND_JMPNZ', 45: 'ZEND_JMPZNZ',
    46: 'ZEND_JMPZ_EX', 47: 'ZEND_JMPNZ_EX', 48: 'ZEND_CASE', 49: 'ZEND_CHECK_VAR',
    50: 'ZEND_SEND_VAR_NO_REF_EX', 51: 'ZEND_CAST', 52: 'ZEND_BOOL',
    53: 'ZEND_FAST_CONCAT', 54: 'ZEND_ROPE_INIT', 55: 'ZEND_ROPE_ADD',
    56: 'ZEND_ROPE_END', 57: 'ZEND_BEGIN_SILENCE', 58: 'ZEND_END_SILENCE',
    59: 'ZEND_INIT_FCALL_BY_NAME', 60: 'ZEND_DO_FCALL', 61: 'ZEND_INIT_FCALL',
    62: 'ZEND_RETURN', 63: 'ZEND_RECV', 64: 'ZEND_RECV_INIT',
    65: 'ZEND_SEND_VAL', 66: 'ZEND_SEND_VAR_EX', 67: 'ZEND_SEND_REF',
    68: 'ZEND_NEW', 69: 'ZEND_INIT_NS_FCALL_BY_NAME', 70: 'ZEND_FREE',
    71: 'ZEND_INIT_ARRAY', 72: 'ZEND_ADD_ARRAY_ELEMENT', 73: 'ZEND_INCLUDE_OR_EVAL',
    74: 'ZEND_UNSET_VAR', 75: 'ZEND_UNSET_DIM', 76: 'ZEND_UNSET_OBJ',
    77: 'ZEND_FE_RESET_R', 78: 'ZEND_FE_FETCH_R', 79: 'ZEND_EXIT',
    80: 'ZEND_FETCH_R', 81: 'ZEND_FETCH_DIM_R', 82: 'ZEND_FETCH_OBJ_R',
    83: 'ZEND_FETCH_W', 84: 'ZEND_FETCH_DIM_W', 85: 'ZEND_FETCH_OBJ_W',
    86: 'ZEND_FETCH_RW', 87: 'ZEND_FETCH_DIM_RW', 88: 'ZEND_FETCH_OBJ_RW',
    89: 'ZEND_FETCH_IS', 90: 'ZEND_FETCH_DIM_IS', 91: 'ZEND_FETCH_OBJ_IS',
    92: 'ZEND_FETCH_FUNC_ARG', 93: 'ZEND_FETCH_DIM_FUNC_ARG',
    94: 'ZEND_FETCH_OBJ_FUNC_ARG', 95: 'ZEND_FETCH_UNSET',
    96: 'ZEND_FETCH_DIM_UNSET', 97: 'ZEND_FETCH_OBJ_UNSET',
    98: 'ZEND_FETCH_LIST_R', 99: 'ZEND_FETCH_CONSTANT', 100: 'ZEND_CHECK_FUNC_ARG',
    101: 'ZEND_EXT_STMT', 102: 'ZEND_EXT_FCALL_BEGIN', 103: 'ZEND_EXT_FCALL_END',
    104: 'ZEND_EXT_NOP', 105: 'ZEND_TICKS', 106: 'ZEND_SEND_VAR_NO_REF',
    107: 'ZEND_CATCH', 108: 'ZEND_THROW', 109: 'ZEND_FETCH_CLASS', 110: 'ZEND_CLONE',
    111: 'ZEND_RETURN_BY_REF', 112: 'ZEND_INIT_METHOD_CALL',
    113: 'ZEND_INIT_STATIC_METHOD_CALL', 114: 'ZEND_ISSET_ISEMPTY_VAR',
    115: 'ZEND_ISSET_ISEMPTY_DIM_OBJ', 116: 'ZEND_SEND_VAL_EX', 117: 'ZEND_SEND_VAR',
    118: 'ZEND_INIT_USER_CALL', 119: 'ZEND_SEND_ARRAY', 120: 'ZEND_SEND_USER',
    121: 'ZEND_STRLEN', 122: 'ZEND_DEFINED', 123: 'ZEND_TYPE_CHECK',
    124: 'ZEND_VERIFY_RETURN_TYPE', 125: 'ZEND_FE_RESET_RW', 126: 'ZEND_FE_FETCH_RW',
    127: 'ZEND_FE_FREE', 128: 'ZEND_INIT_DYNAMIC_CALL', 129: 'ZEND_DO_ICALL',
    130: 'ZEND_DO_UCALL', 131: 'ZEND_DO_FCALL_BY_NAME', 132: 'ZEND_PRE_INC_OBJ',
    133: 'ZEND_PRE_DEC_OBJ', 134: 'ZEND_POST_INC_OBJ', 135: 'ZEND_POST_DEC_OBJ',
    136: 'ZEND_ECHO', 137: 'ZEND_OP_DATA', 138: 'ZEND_INSTANCEOF',
    139: 'ZEND_GENERATOR_CREATE', 140: 'ZEND_MAKE_REF', 141: 'ZEND_DECLARE_FUNCTION',
    142: 'ZEND_DECLARE_LAMBDA_FUNCTION', 143: 'ZEND_DECLARE_CONST',
    144: 'ZEND_DECLARE_CLASS', 145: 'ZEND_DECLARE_CLASS_DELAYED',
    146: 'ZEND_DECLARE_ANON_CLASS', 147: 'ZEND_ADD_ARRAY_UNPACK',
    148: 'ZEND_ISSET_ISEMPTY_PROP_OBJ', 149: 'ZEND_HANDLE_EXCEPTION',
    150: 'ZEND_USER_OPCODE', 151: 'ZEND_ASSERT_CHECK', 152: 'ZEND_JMP_SET',
    153: 'ZEND_UNSET_CV', 154: 'ZEND_ISSET_ISEMPTY_CV', 155: 'ZEND_FETCH_LIST_W',
    156: 'ZEND_SEPARATE', 157: 'ZEND_FETCH_CLASS_NAME', 158: 'ZEND_CALL_TRAMPOLINE',
    159: 'ZEND_DISCARD_EXCEPTION', 160: 'ZEND_YIELD', 161: 'ZEND_GENERATOR_RETURN',
    162: 'ZEND_FAST_CALL', 163: 'ZEND_FAST_RET', 164: 'ZEND_RECV_VARIADIC',
    165: 'ZEND_SEND_UNPACK', 166: 'ZEND_YIELD_FROM', 167: 'ZEND_COPY_TMP',
    168: 'ZEND_BIND_GLOBAL', 169: 'ZEND_COALESCE', 170: 'ZEND_SPACESHIP',
    171: 'ZEND_FUNC_NUM_ARGS', 172: 'ZEND_FUNC_GET_ARGS',
    173: 'ZEND_FETCH_STATIC_PROP_R', 174: 'ZEND_FETCH_STATIC_PROP_W',
    175: 'ZEND_FETCH_STATIC_PROP_RW', 176: 'ZEND_FETCH_STATIC_PROP_IS',
    177: 'ZEND_FETCH_STATIC_PROP_FUNC_ARG', 178: 'ZEND_FETCH_STATIC_PROP_UNSET',
    179: 'ZEND_UNSET_STATIC_PROP', 180: 'ZEND_ISSET_ISEMPTY_STATIC_PROP',
    181: 'ZEND_FETCH_CLASS_CONSTANT', 182: 'ZEND_BIND_LEXICAL',
    183: 'ZEND_BIND_STATIC', 184: 'ZEND_FETCH_THIS', 185: 'ZEND_SEND_FUNC_ARG',
    186: 'ZEND_ISSET_ISEMPTY_THIS', 187: 'ZEND_SWITCH_LONG',
    188: 'ZEND_SWITCH_STRING', 189: 'ZEND_IN_ARRAY', 190: 'ZEND_COUNT',
    191: 'ZEND_GET_CLASS', 192: 'ZEND_GET_CALLED_CLASS', 193: 'ZEND_GET_TYPE',
    194: 'ZEND_ARRAY_KEY_EXISTS', 195: 'ZEND_MATCH', 196: 'ZEND_CASE_STRICT',
    197: 'ZEND_MATCH_ERROR', 198: 'ZEND_JMP_NULL', 199: 'ZEND_CHECK_UNDEF_ARGS',
    200: 'ZEND_FETCH_GLOBALS', 201: 'ZEND_VERIFY_NEVER_TYPE',
    202: 'ZEND_CALLABLE_CONVERT',
}

IS_UNUSED, IS_CONST, IS_TMP_VAR, IS_VAR, IS_CV = 0, 1, 2, 4, 8
IS_NAMES = {0: 'IS_UNUSED', 1: 'IS_CONST', 2: 'IS_TMP_VAR', 4: 'IS_VAR', 8: 'IS_CV'}


class ParseError(SGError):
    pass


class StreamReader:
    def __init__(self, data: bytes):
        self.data, self.pos = data, 0

    def read_u8(self) -> int:
        if self.pos >= len(self.data):
            raise ParseError(f'EOF read_u8 @{self.pos}')
        v = self.data[self.pos]
        self.pos += 1
        return v

    def read_u32(self) -> int:
        if self.pos + 4 > len(self.data):
            raise ParseError(f'EOF read_u32 @{self.pos}')
        v = struct.unpack_from('<I', self.data, self.pos)[0]
        self.pos += 4
        return v

    def read_double(self) -> float:
        if self.pos + 8 > len(self.data):
            raise ParseError(f'EOF read_double @{self.pos}')
        v = struct.unpack_from('<d', self.data, self.pos)[0]
        self.pos += 8
        return v

    def read_bytes(self, n: int) -> bytes:
        if self.pos + n > len(self.data):
            raise ParseError(f'EOF read_bytes({n}) @{self.pos}')
        v = self.data[self.pos:self.pos + n]
        self.pos += n
        return v

    def read_zstr(self) -> str | None:
        n = self.read_u32()
        if n == 0xFFFFFFFF:
            return None
        data = self.read_bytes(n)
        try:
            return data.decode('utf-8')
        except UnicodeDecodeError:
            return data.decode('latin-1')

    def skip(self, n: int) -> None:
        if self.pos + n > len(self.data):
            raise ParseError(f'skip({n}) past EOF @{self.pos}')
        self.pos += n


def version_gate(r: StreamReader, ver: int) -> None:
    if ver < 0x17:
        return
    while True:
        b = r.read_u8()
        if b == 0xFF:
            break
        if b == 0xF0:
            r.skip(r.read_u32())
            break


# ── operand slot primitives ─────────────────────────────────────────────────
def _slot(r: StreamReader) -> tuple[int, int]:
    idx = r.read_u32()
    return idx, 16 * (idx + 3)


def _literal_idx(r: StreamReader) -> int:
    return r.read_u32()


def _cache_slot(r: StreamReader, ext_handles: int = 0) -> int:
    return 4 * (ext_handles + r.read_u32())


def _generic_operand(r: StreamReader) -> tuple[int, int, int]:
    tb = r.read_u8()
    t = tb & 0xF
    if t == IS_CONST:
        idx = _literal_idx(r)
        return tb, idx, idx
    if t in (IS_TMP_VAR, IS_VAR, IS_CV):
        raw, slot = _slot(r)
        return tb, raw, slot
    val = r.read_u32()
    return tb, 0, val


def _op(tp: int, **kw) -> dict:
    base = {'type': tp, 'type_name': IS_NAMES.get(tp, f'IS_{tp}'), 'zend_value': 0}
    base.update(kw)
    return base


def _unwrap_zval(z: Any) -> Any:
    if isinstance(z, dict):
        if "type" in z and "value" in z and len(z) <= 3:
            return _unwrap_zval(z["value"])
        keys = list(z.keys())
        if keys and all(k.isdigit() for k in keys):
            int_keys = [int(k) for k in keys]
            if sorted(int_keys) == list(range(len(int_keys))):
                return [_unwrap_zval(z[str(i)]) for i in range(len(int_keys))]
        return {k: _unwrap_zval(v) for k, v in z.items()}
    if isinstance(z, list):
        return [_unwrap_zval(v) for v in z]
    return z


def _make_operand(tp_byte: int, raw_idx: int, zend_val: int, cv_names: list, literals: list) -> dict:
    t = tp_byte & 0xF
    o = _op(t, zend_value=zend_val)
    if t == IS_CONST:
        o['literal_index'] = raw_idx
        if 0 <= raw_idx < len(literals):
            o['literal_value'] = _unwrap_zval(literals[raw_idx])
    elif t == IS_CV:
        o['variable_index'] = raw_idx
        name = cv_names[raw_idx] if 0 <= raw_idx < len(cv_names) else f'cv{raw_idx}'
        o['variable_name'] = '$' + name
    elif t in (IS_TMP_VAR, IS_VAR):
        o['variable_index'] = raw_idx
    return o


def _unused(val: int = 0) -> dict:
    return _op(IS_UNUSED, zend_value=val)


def _jump_operand(target: int) -> dict:
    o = _op(IS_UNUSED, zend_value=target)
    o['jump_target'] = target
    return o


def _dec_result(r: StreamReader, nibble: int, ext_handles: int, cv_names: list, literals: list) -> dict:
    if nibble == 0xF:
        return _unused()
    if nibble == 0:
        tb, ri, zv = _generic_operand(r)
        return _make_operand(tb, ri, zv, cv_names, literals)
    if nibble == 1:
        tb = r.read_u8()
        ri, zv = _slot(r)
        return _make_operand(tb, ri, zv, cv_names, literals)
    if nibble == 2:
        tb = r.read_u8()
        v = r.read_u32()
        return _make_operand(tb, 0, v, cv_names, literals)
    if nibble == 3:
        slot = _cache_slot(r, ext_handles)
        return _op(IS_VAR, zend_value=slot)
    if nibble == 4:
        tb = r.read_u8()
        slot = _cache_slot(r, ext_handles) if tb == 1 else _slot(r)[1]
        return _make_operand(tb, 0, slot, cv_names, literals)
    raise ParseError(f'unknown result nibble {nibble:#x}')


def _dec_op1(r: StreamReader, nibble: int, ext_handles: int, cv_names: list, literals: list) -> dict:
    if nibble == 0xF:
        return _unused()
    if nibble == 0:
        tb, ri, zv = _generic_operand(r)
        return _make_operand(tb, ri, zv, cv_names, literals)
    if nibble == 1:
        tb = r.read_u8()
        ri, zv = _slot(r)
        return _make_operand(tb, ri, zv, cv_names, literals)
    if nibble == 2:
        tb = r.read_u8()
        v = r.read_u32()
        return _make_operand(tb, 0, v, cv_names, literals)
    if nibble == 3:
        r.read_u8()
        li = _literal_idx(r)
        return _make_operand(IS_CONST, li, li, cv_names, literals)
    if nibble == 4:
        return _jump_operand(r.read_u32())
    if nibble == 5:
        tb = r.read_u8()
        if tb == 0:
            return _unused(r.read_u32())
        if tb == 1:
            li = _literal_idx(r)
            return _make_operand(IS_CONST, li, li, cv_names, literals)
        ri, zv = _slot(r)
        return _make_operand(tb, ri, zv, cv_names, literals)
    raise ParseError(f'unknown op1 nibble {nibble:#x}')


def _dec_op2(r: StreamReader, nibble: int, ext_handles: int, cv_names: list, literals: list) -> dict:
    if nibble == 0xF:
        return _unused()
    if nibble == 0:
        tb, ri, zv = _generic_operand(r)
        return _make_operand(tb, ri, zv, cv_names, literals)
    if nibble == 1:
        tb = r.read_u8()
        ri, zv = _slot(r)
        return _make_operand(tb, ri, zv, cv_names, literals)
    if nibble == 2:
        tb = r.read_u8()
        v = r.read_u32()
        return _make_operand(tb, 0, v, cv_names, literals)
    if nibble == 3:
        r.read_u8()
        li = _literal_idx(r)
        return _make_operand(IS_CONST, li, li, cv_names, literals)
    if nibble == 4:
        return _jump_operand(r.read_u32())
    if nibble == 5:
        tb = r.read_u8()
        if tb == 0:
            return _unused(r.read_u32())
        if tb == 1:
            li = _literal_idx(r)
            return _make_operand(IS_CONST, li, li, cv_names, literals)
        ri, zv = _slot(r)
        return _make_operand(tb, ri, zv, cv_names, literals)
    if nibble == 6:
        slot = _cache_slot(r, ext_handles)
        return _op(IS_VAR, zend_value=slot)
    raise ParseError(f'unknown op2 nibble {nibble:#x}')


def _parse_opcode(r: StreamReader, ver: int, index: int, literals: list, cv_names: list, ext_handles: int = 0) -> dict:
    opcode = r.read_u8()
    type_word = r.read_u32() if ver >= 0x1B else 0xFFFFFF

    ext_n = (type_word >> 12) & 0xF
    res_n = (type_word >> 8) & 0xF
    op1_n = type_word & 0xF
    op2_n = (type_word >> 4) & 0xF

    ext_val = 0
    if ext_n == 0xF:
        pass
    elif ext_n in (2, 3):
        ext_val = r.read_u32()
    elif ext_n == 1:
        _, ext_val = _slot(r)
    elif ext_n == 4:
        ext_val = _cache_slot(r, ext_handles)
    elif ext_n == 5:
        ext_val = _cache_slot(r, ext_handles)
        flags = r.read_u8()
        ext_val = (ext_val & ~3) | (flags & 3)
    elif ext_n == 6:
        ext_val = 24 * r.read_u32()
        flags = r.read_u8()
        ext_val = (ext_val & ~3) | (flags & 3)
    else:
        raise ParseError(f'opcode {opcode}@{index}: bad ext nibble {ext_n:#x}')

    call_name = None
    if opcode in (205, 206, 207) and _next_zstr_plausible(r):
        call_name = r.read_zstr()

    result = _dec_result(r, res_n, ext_handles, cv_names, literals)
    op1 = _dec_op1(r, op1_n, ext_handles, cv_names, literals)
    op2 = _dec_op2(r, op2_n, ext_handles, cv_names, literals)
    lineno = r.read_u32()

    opcode_name = OPCODE_NAMES.get(opcode, f'ZEND_UNKNOWN_{opcode}')
    if opcode in (205, 206, 207) and call_name:
        opcode_name = 'ZEND_SG_FCALL'

    return {
        'index': index, 'opcode': opcode, 'opcode_name': opcode_name,
        'lineno': lineno, 'extended_value': ext_val, 'call_name': call_name,
        'op1': op1, 'op2': op2, 'result': result,
    }


# ── zval / hashtable ─────────────────────────────────────────────────────────
def _parse_zval(r: StreamReader, ver: int) -> dict:
    type_info = r.read_u32()
    tail = r.read_u32()
    if tail == 0xFFFFFFFF:
        r.read_u32()
    base = type_info & 0xFF

    if base in (127, 126):           # SG_FILE / SG_DIR marker
        return {'type': 'sg_special', 'tag': base, 'value': None}
    if base in (125, 124):           # SG path constant: string + extra u32
        s = r.read_zstr()
        r.read_u32()
        return {'type': 'string', 'value': s}
    if base == 0:
        return {'type': 'undef', 'value': None}
    if base == 1:
        return {'type': 'null', 'value': None}
    if base == 2:
        return {'type': 'bool', 'value': False}
    if base == 3:
        return {'type': 'bool', 'value': True}
    if base == 4:
        v = r.read_u32()
        return {'type': 'int', 'value': v - 0x100000000 if v >= 0x80000000 else v}
    if base == 5:
        return {'type': 'float', 'value': r.read_double()}
    if base == 6:
        return {'type': 'string', 'value': r.read_zstr()}
    if base == 7:
        ht = _parse_hashtable(r, ver)
        r.read_u32()
        r.read_u32()
        return {'type': 'array', 'value': ht}
    return {'type': 'unknown', 'value': base}


def _parse_hashtable(r: StreamReader, ver: int) -> dict:
    count = r.read_u32()
    if count == 0:
        return {}
    if ver >= 0x20:
        r.read_u8()  # packed flag
    result = {}
    for _ in range(count):
        klen = r.read_u32()
        if klen == 0xFFFFFFFF:
            key = str(r.read_u32())
        else:
            raw = r.read_bytes(klen)
            try:
                key = raw.decode('utf-8')
            except UnicodeDecodeError:
                key = raw.decode('latin-1')
        result[key] = _parse_zval(r, ver)
    return result


def _skip_type_info(r: StreamReader, ver: int) -> None:
    hi = r.read_u32()
    if hi & 0x40000000:
        count = r.read_u32()
        for _ in range(count):
            entry_hi = r.read_u32() if ver >= 0x21 else hi
            if (entry_hi & 0x10000000) or ver < 0x21:
                r.read_zstr()
            elif entry_hi & 0x40000000:
                _skip_type_info(r, ver)
    elif hi & 0x11000000:
        r.read_zstr()


def _skip_attributes(r: StreamReader, ver: int) -> None:
    count = r.read_u32()
    for _ in range(count):
        r.read_zstr()
        r.read_u32()
        r.read_u32()
        r.read_u32()
        arg_count = r.read_u32()
        for _ in range(arg_count):
            r.read_zstr()
            _parse_zval(r, ver)


# ── op_array / class / container ────────────────────────────────────────────
def _read_raw_oparray_counts(r: StreamReader) -> tuple[int, int, int, int, int]:
    return (r.read_u32(), r.read_u32(), r.read_u32(), r.read_u32(), r.read_u32())


def _oparray_counts_plausible(r: StreamReader, counts: tuple) -> bool:
    _ext_handles_count, literal_slot_size, opcode_count, T, num_cvs = counts
    remaining = len(r.data) - r.pos
    if literal_slot_size not in (16, 24, 28, 32):
        return False
    if opcode_count > 200000 or T > 200000 or num_cvs > 10000:
        return False
    if opcode_count == 0 and (T != 0 or num_cvs != 0):
        return False
    return num_cvs * 4 + opcode_count * 9 <= remaining


def _read_oparray_counts(r: StreamReader, ver: int, literals: list) -> tuple[int, int, int, int, int]:
    counts_pos = r.pos
    for extra_count in range(0, 17):
        r.pos = counts_pos
        extras = []
        try:
            for _ in range(extra_count):
                extras.append(_parse_zval(r, ver))
            counts = _read_raw_oparray_counts(r)
        except ParseError:
            continue
        if _oparray_counts_plausible(r, counts):
            literals.extend(extras)
            return counts
    r.pos = counts_pos
    return _read_raw_oparray_counts(r)


def parse_op_array(r: StreamReader, ver: int, has_hybrid_vm: bool = False) -> dict:
    version_gate(r, ver)

    type_byte = r.read_u8()  # 1 = function stub, 2 = full op_array
    if type_byte not in (1, 2):
        raise ParseError(f'bad op_array type {type_byte} @{r.pos}')

    fn_flags = r.read_u32()
    r.read_u8(); r.read_u8(); r.read_u8()
    num_args = r.read_u32()
    required_num_args = r.read_u32()

    arg_names = []
    if fn_flags & 0x6000:            # return-type info precedes params
        r.read_zstr()
        _skip_type_info(r, ver)
    for _ in range(num_args):
        arg_names.append(r.read_zstr() or '')
        _skip_type_info(r, ver)

    function_name = r.read_zstr()
    r.read_zstr()                    # scope name

    if type_byte == 1:
        return {
            'kind': 'function_stub', 'function_name': function_name or '',
            'fn_flags': fn_flags, 'num_args': num_args, 'required_num_args': required_num_args,
            'arg_names': arg_names, 'opcodes': [], 'literals': [], 'cv_names': [],
            'try_catches': [], 'line_start': None, 'line_end': None, 'doc_comment': None,
            'nested': [],
        }

    literal_count = r.read_u32()
    literals = [_parse_zval(r, ver) for _ in range(literal_count)]

    _, _, opcode_count, T, num_cvs = _read_oparray_counts(r, ver, literals)

    cv_names = [r.read_zstr() or '' for _ in range(num_cvs)]
    pre_data = [r.read_u32() for _ in range(opcode_count)] if has_hybrid_vm else []
    opcodes = [_parse_opcode(r, ver, i, literals, cv_names) for i in range(opcode_count)]

    lr_count = r.read_u32()
    for _ in range(lr_count):
        if ver >= 0x1B:
            r.read_u8(); _slot(r)
        elif ver >= 0x1A:
            _slot(r)
        else:
            r.read_u32()
        r.read_u32(); r.read_u32()

    tc_count = r.read_u32()
    try_catches = []
    for _ in range(tc_count):
        try_catches.append({
            'try_op': r.read_u32(), 'catch_op': r.read_u32(),
            'finally_op': r.read_u32(), 'finally_end': r.read_u32(),
        })

    _parse_hashtable(r, ver)         # static variables
    doc_comment = r.read_zstr()
    line_start = r.read_u32()
    line_end = r.read_u32()
    r.read_u32()                     # prototype depth
    _skip_attributes(r, ver)

    nested_count = r.read_u32()
    nested = [parse_op_array(r, ver, has_hybrid_vm) for _ in range(nested_count)]

    return {
        'kind': 'op_array', 'fn_flags': fn_flags,
        'function_name': function_name or '', 'arg_names': arg_names,
        'num_args': num_args, 'required_num_args': required_num_args,
        'literals': literals, 'opcode_count': opcode_count, 'T': T,
        'num_cvs': num_cvs, 'cv_names': cv_names, 'pre_data': pre_data,
        'opcodes': opcodes, 'try_catches': try_catches,
        'doc_comment': doc_comment, 'line_start': line_start, 'line_end': line_end,
        'nested': nested,
    }


def parse_container(data: bytes) -> dict:
    r = StreamReader(data)
    magic = r.read_bytes(15)
    if magic != b'SOURCEGUARDIAN\x00':
        raise ParseError(f'bad magic {magic!r}')

    ver, flags = r.read_u32(), r.read_u32()
    r.read_u32(); r.read_u32()       # reserved words
    if ver > 0x21:
        raise ParseError(f'unsupported container version {ver}')
    has_hybrid_vm = bool(flags & 2)

    functions, classes = [], []
    for phase in range(3):
        if phase == 1:
            while (tag := r.read_u8()) != 0:
                if tag != 1:
                    raise ParseError(f'class tag={tag:#x} @{r.pos}')
                r.read_bytes(r.read_u32())     # SG composite key
                classes.append(parse_class(r, ver, has_hybrid_vm))
            if ver >= 0x1D:
                break
        else:
            while (tag := r.read_u8()) != 0:
                if tag != 2:
                    raise ParseError(f'func tag={tag:#x} @{r.pos}')
                r.read_bytes(r.read_u32())
                functions.append(parse_op_array(r, ver, has_hybrid_vm))
            if ver < 0x1D:
                break

    main = parse_op_array(r, ver, has_hybrid_vm)
    return {'ver': ver, 'flags': flags, 'functions': functions, 'classes': classes, 'main': main}


# ── class property table ────────────────────────────────────────────────────
def _next_u32_is_probable_prop_slot(r: StreamReader) -> bool:
    if r.pos + 8 > len(r.data):
        return False
    first = struct.unpack_from('<I', r.data, r.pos)[0]
    second = struct.unpack_from('<I', r.data, r.pos + 4)[0]
    if first >= 0x10000:
        return False
    if 0 < second <= 512 and r.pos + 8 + second <= len(r.data):
        return True
    if r.pos + 9 <= len(r.data):
        shifted = struct.unpack_from('<I', r.data, r.pos + 5)[0]
        return 0 < shifted <= 512 and r.pos + 9 + shifted <= len(r.data)
    return False


def _read_prop_zstr(r: StreamReader) -> str | None:
    length = struct.unpack_from('<I', r.data, r.pos)[0]
    if r.pos + 5 <= len(r.data):
        shifted = struct.unpack_from('<I', r.data, r.pos + 1)[0]
        if (length > 512 or length > len(r.data) - r.pos) and shifted <= 512:
            r.read_u8()
    return r.read_zstr()


def _next_zstr_plausible(r: StreamReader, limit: int = 512) -> bool:
    if r.pos + 4 > len(r.data):
        return False
    length = struct.unpack_from('<I', r.data, r.pos)[0]
    if length == 0xFFFFFFFF:
        return True
    if length > limit or r.pos + 4 + length > len(r.data):
        return False
    data = r.data[r.pos + 4:r.pos + 4 + length]
    return all(b in (9, 10, 13) or 32 <= b < 127 for b in data)


def _parse_property_zval(r: StreamReader, ver: int) -> dict:
    type_info = r.read_u32()
    tail = r.read_u32()
    if tail == 0xFFFFFFFF:
        r.read_u32()
    base = type_info & 0xFF
    if base == 7:
        ht = _parse_hashtable(r, ver)
        r.read_u32()
        return {'type': 'array', 'value': ht}
    rr = StreamReader(r.data)
    rr.pos = r.pos - (12 if tail == 0xFFFFFFFF else 8)
    value = _parse_zval(rr, ver)
    r.pos = rr.pos
    return value


# Zend class/property flag bits, shared by PHP 8.1 through 8.4.
_ZEND_ACC_PROTECTED = 0x02
_ZEND_ACC_PRIVATE = 0x04
_ZEND_ACC_STATIC = 0x10
_ZEND_ACC_READONLY = 0x80
_ZEND_ACC_FINAL = 0x20
_ZEND_ACC_ABSTRACT = 0x40
_ZEND_ACC_INTERFACE = 0x01
_ZEND_ACC_TRAIT = 0x02


def _decode_class_flags(flags: int) -> dict:
    return {
        "is_interface": bool(flags & _ZEND_ACC_INTERFACE),
        "is_trait": bool(flags & _ZEND_ACC_TRAIT),
        "is_final": bool(flags & _ZEND_ACC_FINAL),
        "is_abstract": bool(flags & _ZEND_ACC_ABSTRACT),
    }


def _decode_property_flags(flags: int) -> dict:
    if flags & _ZEND_ACC_PRIVATE:
        visibility = "private"
    elif flags & _ZEND_ACC_PROTECTED:
        visibility = "protected"
    else:
        visibility = "public"
    return {
        "visibility": visibility,
        "is_static": bool(flags & _ZEND_ACC_STATIC),
        "is_readonly": bool(flags & _ZEND_ACC_READONLY),
    }


# MAY_BE_<T> = 1 << IS_<T>, the low bits of a serialized zend_type mask.
_ZEND_BUILTIN_TYPE_BITS = (
    (1 << 4, "int"),
    (1 << 5, "float"),
    (1 << 6, "string"),
    (1 << 7, "array"),
    (1 << 8, "object"),
    (1 << 9, "resource"),
    (1 << 12, "callable"),
    (1 << 13, "iterable"),
    (1 << 14, "void"),
    (1 << 16, "mixed"),
    (1 << 17, "never"),
    (1 << 18, "static"),
)


def _decode_type_mask(mask: int) -> tuple[str | None, bool]:
    """Return ``(type_name, allow_null)`` for a serialized builtin type mask."""
    builtin = mask & 0x00FFFFFF
    allow_null = bool(builtin & (1 << 1))
    names: list[str] = []
    if builtin & (1 << 2) and builtin & (1 << 3):
        names.append("bool")
    elif builtin & (1 << 2):
        names.append("false")
    elif builtin & (1 << 3):
        names.append("true")
    for bit, name in _ZEND_BUILTIN_TYPE_BITS:
        if builtin & bit:
            names.append(name)
    if not names:
        return None, allow_null
    if "mixed" in names:
        return "mixed", False
    if "void" in names:
        return "void", False
    if "never" in names:
        return "never", False
    return "|".join(names), allow_null


def _read_type_info(r: StreamReader, ver: int) -> dict | None:
    """Parse the SG type blob and return ``{type_name, allow_null}``."""
    hi = r.read_u32()
    if not hi:
        return None
    if hi & 0x40000000:
        count = r.read_u32()
        members: list[str] = []
        for _ in range(count):
            member_hi = r.read_u32() if ver >= 0x21 else hi
            if (member_hi & 0x10000000) or ver < 0x21:
                members.append(r.read_zstr() or "mixed")
            elif member_hi & 0x40000000:
                nested = _read_type_info(r, ver)
                if nested and nested.get("type_name"):
                    members.append(nested["type_name"])
            else:
                name, _ = _decode_type_mask(member_hi)
                members.append(name or "mixed")
        type_name = "|".join(dict.fromkeys(members)) or None
        return {"type_name": type_name, "allow_null": bool(hi & 0x2)}
    if hi & 0x11000000:
        return {"type_name": r.read_zstr(), "allow_null": bool(hi & 0x2)}
    type_name, allow_null = _decode_type_mask(hi)
    if not type_name:
        return None
    return {"type_name": type_name, "allow_null": allow_null}


def _parse_class_props(r: StreamReader, ver: int) -> dict:
    total = r.read_u32()
    static_count = r.read_u32()
    properties: dict = {}
    for index in range(total):
        if _next_u32_is_probable_prop_slot(r):
            r.read_u32()             # property slot/offset
        name = _read_prop_zstr(r)
        flags = r.read_u32()
        _read_prop_zstr(r)           # mangled/typed-property name
        doc_comment = _read_prop_zstr(r)
        default = _parse_property_zval(r, ver)
        type_info = _read_type_info(r, ver)
        _skip_attributes(r, ver)
        if not name:
            continue
        default_type = default.get("type") if isinstance(default, dict) else None
        has_default = default_type not in (None, "undef")
        properties[name] = {
            "name": name,
            "flags_decoded": _decode_property_flags(flags),
            "is_static": index < static_count or bool(flags & _ZEND_ACC_STATIC),
            "is_readonly": bool(flags & _ZEND_ACC_READONLY),
            "type_name": type_info.get("type_name") if type_info else None,
            "allow_null": bool(type_info.get("allow_null")) if type_info else False,
            "has_default_value": has_default,
            "default_value": _unwrap_zval(default) if has_default else None,
            "doc_comment": doc_comment,
        }
    return properties


def _attributes_plausible_at(r: StreamReader, pos: int, ver: int, require_nonempty: bool = False) -> bool:
    if pos + 4 > len(r.data):
        return False
    rr = StreamReader(r.data)
    rr.pos = pos
    try:
        count = rr.read_u32()
        if require_nonempty and count == 0:
            return False
        if count > 64:
            return False
        for _ in range(count):
            if not _next_zstr_plausible(rr, 512):
                return False
            name = rr.read_zstr()
            if not isinstance(name, str) or not name:
                return False
            if rr.pos + 16 > len(rr.data):
                return False
            rr.read_u32(); rr.read_u32(); rr.read_u32()
            arg_count = rr.read_u32()
            if arg_count > 64:
                return False
            for _ in range(arg_count):
                if not _next_zstr_plausible(rr, 512):
                    return False
                rr.read_zstr()
                _parse_zval(rr, ver)
    except ParseError:
        return False
    return True


def _skip_class_attributes(r: StreamReader, ver: int) -> None:
    if (r.pos + 9 <= len(r.data)
            and struct.unpack_from('<I', r.data, r.pos)[0] == 0
            and r.data[r.pos + 4] == 0
            and _attributes_plausible_at(r, r.pos + 5, ver, require_nonempty=True)):
        r.skip(5)
    _skip_attributes(r, ver)


def _method_count_plausible(r: StreamReader, pos: int) -> bool:
    if pos + 4 > len(r.data):
        return False
    count = struct.unpack_from('<I', r.data, pos)[0]
    if count > 4096:
        return False
    if count == 0:
        return True
    name_pos = pos + 4
    if name_pos + 4 > len(r.data):
        return False
    length = struct.unpack_from('<I', r.data, name_pos)[0]
    if length == 0 or length > 256 or name_pos + 4 + length > len(r.data):
        return False
    name = r.data[name_pos + 4:name_pos + 4 + length]
    if not all(b in (92, 95, 36) or 48 <= b <= 57 or 65 <= b <= 90 or 97 <= b <= 122 for b in name):
        return False
    gate_pos = name_pos + 4 + length
    return r.data[gate_pos] in (0xF0, 0xFF) if gate_pos < len(r.data) else False


def _skip_optional_class_aux_table(r: StreamReader, ver: int) -> None:
    pos = r.pos
    if _method_count_plausible(r, pos) and struct.unpack_from('<I', r.data, pos)[0] != 0:
        return
    aux_skip = 5 if ver >= 0x20 else 4
    if pos + aux_skip > len(r.data):
        return
    if struct.unpack_from('<I', r.data, pos)[0] != 0:
        return
    if ver >= 0x20 and r.data[pos + 4] != 0:
        return
    if _method_count_plausible(r, pos + aux_skip):
        r.skip(aux_skip)


def parse_class(r: StreamReader, ver: int, has_hybrid_vm: bool = False) -> dict:
    version_gate(r, ver)
    type_byte = r.read_u8()
    if type_byte != 2:
        raise ParseError(f'class type_byte={type_byte} (expected 2) @{r.pos}')

    class_name = r.read_zstr() or ''
    class_flags = r.read_u32()
    parent_name = r.read_zstr()

    interfaces = [r.read_zstr() for _ in range(r.read_u32())]
    traits = [r.read_zstr() for _ in range(r.read_u32())]
    for _ in range(r.read_u32()):     # trait aliases
        mcount = r.read_u32()
        r.read_zstr(); r.read_zstr()
        for _ in range(mcount):
            r.read_zstr()
    for _ in range(r.read_u32()):     # trait precedences
        r.read_zstr(); r.read_zstr(); r.read_zstr(); r.read_u32()

    doc_comment = r.read_zstr()

    constants = {}
    for _ in range(r.read_u32()):
        cname = r.read_zstr() or ''
        cval = _parse_zval(r, ver)
        r.read_u32(); r.read_zstr()
        _skip_attributes(r, ver)
        r.read_u32()
        constants[cname] = cval.get('value') if isinstance(cval, dict) else cval

    properties = _parse_class_props(r, ver)
    _skip_class_attributes(r, ver)
    r.read_u32()                     # trailing flags/line word
    _parse_hashtable(r, ver)         # static properties table
    _skip_optional_class_aux_table(r, ver)

    methods = []
    for _ in range(r.read_u32()):
        method_name = r.read_zstr() or ''
        oa = parse_op_array(r, ver, has_hybrid_vm)
        oa['method_name'] = method_name
        methods.append(oa)

    return {
        'class_name': class_name, 'class_flags': class_flags,
        'ce_flags_decoded': _decode_class_flags(class_flags),
        'parent_name': parent_name, 'interfaces': interfaces,
        'traits': traits, 'doc_comment': doc_comment,
        'constants': constants, 'properties': properties, 'methods': methods,
    }


# ── icdump-ir-v1 conversion ──────────────────────────────────────────────────
def _normalize_operand(op: dict) -> dict:
    t_name = op.get("type_name", "IS_UNUSED")
    t_num = op.get("type", 0)
    norm: dict[str, Any] = {
        "type": t_num,
        "type_name": t_name,
    }
    if t_name == "IS_CONST":
        val = op.get("literal_value")
        norm["has_literal"] = True
        norm["literal"] = val
        norm["constant"] = op.get("literal_index")
    elif t_name == "IS_CV":
        raw_name = op.get("variable_name", "")
        clean_name = raw_name.lstrip("$") if raw_name else None
        norm["cv_name"] = clean_name
        norm["cv_index"] = op.get("variable_index")
        norm["var"] = op.get("zend_value", op.get("variable_index"))
    elif t_name in ("IS_TMP_VAR", "IS_VAR"):
        var_slot = op.get("variable_index", op.get("zend_value"))
        norm["var"] = var_slot
        norm["num"] = var_slot
    elif t_name == "IS_UNUSED":
        if "jump_target" in op:
            norm["opline_num"] = op["jump_target"]
            norm["var"] = op["jump_target"]
        elif "zend_value" in op:
            norm["var"] = op["zend_value"]
    return norm


def _calc_jump_targets(op: dict) -> list[int]:
    targets: list[int] = []
    op1 = op.get("op1", {})
    op2 = op.get("op2", {})
    res = op.get("result", {})

    if "jump_target" in op1:
        targets.append(int(op1["jump_target"]))
    if "jump_target" in op2:
        targets.append(int(op2["jump_target"]))
    if "jump_target" in res:
        targets.append(int(res["jump_target"]))

    name = op.get("opcode_name", "")
    if not targets:
        if name == "ZEND_JMP":
            val = op1.get("zend_value")
            if val is not None and val != 0:
                targets.append(int(val))
        elif name in (
            "ZEND_JMPZ", "ZEND_JMPNZ", "ZEND_JMPZNZ", "ZEND_JMPZ_EX",
            "ZEND_JMPNZ_EX", "ZEND_JMP_SET", "ZEND_JMP_NULL", "ZEND_COALESCE",
            "ZEND_FE_RESET_R", "ZEND_FE_RESET_RW",
        ):
            val = op2.get("zend_value")
            if val is not None and val != 0:
                targets.append(int(val))
        elif name in ("ZEND_FE_FETCH_R", "ZEND_FE_FETCH_RW"):
            ext = op.get("extended_value")
            if ext:
                targets.append(int(ext))
            else:
                val = op2.get("zend_value")
                if val is not None and val != 0 and op2.get("type_name") not in ("IS_CV", "IS_VAR"):
                    targets.append(int(val))

    return targets


def _decode_fn_flags(flags: int) -> dict:
    vis = "public"
    if flags & 0x0100:
        vis = "protected"
    elif flags & 0x0200:
        vis = "private"
    return {
        "is_static": bool(flags & 0x01),
        "returns_reference": bool(flags & 0x800),
        "visibility": vis,
    }


def _normalize_oparray(
    oa: dict,
    oa_id: str,
    kind: str = "function",
    meta: dict | None = None,
) -> dict:
    fn_name = oa.get("function_name") or oa.get("method_name") or ""
    fn_flags = oa.get("fn_flags", 0)

    arg_names = oa.get("arg_names", [])
    required_num_args = oa.get("required_num_args")
    if not isinstance(required_num_args, int):
        required_num_args = len(arg_names)
    arg_info = [
        {
            "index": i,
            "name": name,
            "type_name": None,
            "pass_by_reference": False,
            "allow_null": False,
            "is_variadic": False,
            "has_default": i >= required_num_args,
        }
        for i, name in enumerate(arg_names)
    ]

    cv_names = oa.get("cv_names", [])
    vars_dict = {str(i): name for i, name in enumerate(cv_names)}

    raw_literals = oa.get("literals", [])
    literals = [_unwrap_zval(lit) for lit in raw_literals]

    normalized_ops = []
    for raw_op in oa.get("opcodes", []):
        idx = raw_op.get("index", 0)
        op_name = raw_op.get("opcode_name", "ZEND_NOP")
        opcode_num = raw_op.get("opcode", 0)
        call_name = raw_op.get("call_name")

        # Normalize SG dynamic call to ZEND_INIT_FCALL so handlers immediately bind call_name
        if op_name in ("ZEND_SG_FCALL", "ZEND_UNKNOWN_205", "ZEND_UNKNOWN_206", "ZEND_UNKNOWN_207"):
            op_name = "ZEND_INIT_FCALL"

        targets = _calc_jump_targets(raw_op)
        fe_done = None
        if op_name in ("ZEND_FE_FETCH_R", "ZEND_FE_FETCH_RW") and targets:
            fe_done = targets[0]

        normalized_ops.append({
            "index": idx,
            "opcode": opcode_num,
            "opcode_name": op_name,
            "line": raw_op.get("lineno"),
            "extended_value": raw_op.get("extended_value", 0),
            "call_name": call_name,
            "op1": _normalize_operand(raw_op.get("op1", {})),
            "op2": _normalize_operand(raw_op.get("op2", {})),
            "result": _normalize_operand(raw_op.get("result", {})),
            "jump_targets": targets,
            "fe_fetch_done_opline": fe_done,
        })

    return {
        "id": oa_id,
        "kind": kind,
        "function_name": fn_name,
        "line_start": oa.get("line_start"),
        "line_end": oa.get("line_end"),
        "fn_flags": fn_flags,
        "fn_flags_decoded": _decode_fn_flags(fn_flags),
        "num_args": oa.get("num_args", len(arg_names)),
        "required_num_args": oa.get("required_num_args", len(arg_names)),
        "arg_info": arg_info,
        "vars": vars_dict,
        "literals": literals,
        "try_catch": oa.get("try_catches", []),
        "doc_comment": oa.get("doc_comment"),
        "opcodes": normalized_ops,
        "meta": meta or {},
    }


def container_to_icdump(container: dict, source_file: str = "sourceguardian.php") -> dict:
    """Convert parsed SourceGuardian container into icdump-ir-v1 JSON format."""
    op_arrays: dict[str, Any] = {}
    function_index: dict[str, str] = {}
    class_index: dict[str, Any] = {}
    closure_index: dict[str, str] = {}

    # 1. Main op_array
    if "main" in container:
        main_oa = _normalize_oparray(container["main"], oa_id="main", kind="main")
        op_arrays["main"] = main_oa

    # 2. Standalone functions
    for i, fn in enumerate(container.get("functions", [])):
        fn_name = fn.get("function_name") or f"func_{i}"
        oa_id = f"function:{fn_name.encode('utf-8', errors='replace').hex()}"
        function_index[fn_name] = oa_id
        op_arrays[oa_id] = _normalize_oparray(fn, oa_id=oa_id, kind="function")

        # Nested closures inside function
        for j, nested in enumerate(fn.get("nested", [])):
            c_id = f"closure:{oa_id}:{j}"
            closure_index[c_id] = c_id
            op_arrays[c_id] = _normalize_oparray(nested, oa_id=c_id, kind="closure")

    # 3. Classes and methods
    for cls in container.get("classes", []):
        cls_name = cls.get("class_name", "")
        cls_id = f"class:{cls_name.encode('utf-8', errors='replace').hex()}"
        methods_map: dict[str, str] = {}

        for method in cls.get("methods", []):
            m_name = method.get("method_name") or method.get("function_name") or "unknown"
            m_id = f"method:{cls_name}::{m_name}"
            methods_map[m_name] = m_id
            op_arrays[m_id] = _normalize_oparray(
                method,
                oa_id=m_id,
                kind="method",
                meta={"class": cls_id, "class_name": cls_name},
            )

            # Nested closures inside method
            for j, nested in enumerate(method.get("nested", [])):
                c_id = f"closure:{m_id}:{j}"
                closure_index[c_id] = c_id
                op_arrays[c_id] = _normalize_oparray(nested, oa_id=c_id, kind="closure")

        class_index[cls_id] = {
            "name": cls_name,
            "parent": cls.get("parent_name"),
            "interfaces": cls.get("interfaces", []),
            "traits": cls.get("traits", []),
            "ce_flags_decoded": cls.get("ce_flags_decoded")
            or _decode_class_flags(cls.get("class_flags", 0)),
            "constants_table": cls.get("constants", {}),
            "properties_merged": cls.get("properties", {}),
            "methods": methods_map,
            "doc_comment": cls.get("doc_comment"),
        }

    return {
        "format": "icdump-ir-v1",
        "source_file": source_file,
        "entry": "main",
        "op_arrays": op_arrays,
        "function_index": function_index,
        "class_index": class_index,
        "closure_index": closure_index,
    }


def build_ir(body_bytes: bytes, source_file: str = "sourceguardian.php") -> dict:
    """Parse decrypted body.bin bytes and convert to icdump-ir-v1 format."""
    container = parse_container(body_bytes)
    return container_to_icdump(container, source_file=source_file)


def decode_sg_file_to_ir(file_path: str | Path) -> dict:
    """Full pipeline: decode SourceGuardian file directly into icdump-ir-v1 dict."""
    decoded = decode_file(file_path)
    body_bytes = decoded.get("body")
    if not body_bytes:
        raise SGError(f"{file_path}: decoded container carries no body section")
    return build_ir(body_bytes, source_file=str(Path(file_path).name))


def process_file(path: str) -> None:
    data = open(path, 'rb').read()
    if data.startswith(b"SOURCEGUARDIAN\x00"):
        container = parse_container(data)
        ir = container_to_icdump(container, source_file=os.path.basename(path))
    else:
        # Encoded PHP container
        ir = decode_sg_file_to_ir(path)

    out_base = os.path.splitext(path)[0]
    with open(out_base + '.icdump.json', 'w', encoding='utf-8') as fh:
        json.dump(ir, fh, indent=2, default=str)

    print(f"{path}: successfully dumped icdump-ir-v1 JSON to {out_base}.icdump.json")


def main() -> None:
    if len(sys.argv) < 2:
        print('usage: python sg_bytecode_ir.py <file.php | body.bin> [...]', file=sys.stderr)
        sys.exit(1)
    for path in sys.argv[1:]:
        try:
            process_file(path)
        except Exception as e:
            print(f'{path}: ERROR: {e}', file=sys.stderr)


if __name__ == '__main__':
    main()
