"""Tests for SourceGuardian bytecode IR parser and icdump-ir-v1 conversion."""

import struct
import pytest

from engines.sourceguardian.bytecode_ir import (
    StreamReader,
    ParseError,
    container_to_icdump,
    build_ir,
    _normalize_operand,
    _calc_jump_targets,
    _normalize_oparray,
    parse_container,
)
from php_reconstructor.loader import parse_dump
from php_reconstructor.decompiler.program import decompile_program
from php_reconstructor.decompiler.optimize import optimize
from php_reconstructor.emitter.php_emitter import emit_php


def u32(n: int) -> bytes:
    return struct.pack("<I", n)


def zstr(s: str | None) -> bytes:
    if s is None:
        return u32(0xFFFFFFFF)
    b = s.encode("utf-8")
    return u32(len(b)) + b


def make_zval_string(s: str) -> bytes:
    # base = 6 (string)
    # type_info = 6, tail = 0
    return u32(6) + u32(0) + zstr(s)


def make_zval_int(val: int) -> bytes:
    # base = 4 (int)
    # type_info = 4, tail = 0, value = u32
    return u32(4) + u32(0) + u32(val)


def make_synthetic_op_array(
    function_name: str = "",
    cv_names: list[str] = None,
    literals: list[bytes] = None,
    opcodes: list[bytes] = None,
    fn_flags: int = 0,
    num_args: int = 0,
    required_num_args: int = 0,
    arg_names: list[str] = None,
) -> bytes:
    if cv_names is None:
        cv_names = []
    if literals is None:
        literals = []
    if opcodes is None:
        opcodes = []
    if arg_names is None:
        arg_names = []

    buf = bytearray()
    # version_gate (ver=0x21 >= 0x17): immediate 0xFF terminator
    buf.append(0xFF)
    # type_byte = 2 (full op_array)
    buf.append(2)
    buf.extend(u32(fn_flags))
    # 3 padding bytes
    buf.extend(b"\x00\x00\x00")
    buf.extend(u32(num_args))
    buf.extend(u32(required_num_args))
    for arg_name in arg_names:
        buf.extend(zstr(arg_name))
        buf.extend(u32(0))  # type info
    # function_name
    buf.extend(zstr(function_name if function_name else None))
    # scope_name
    buf.extend(zstr(None))
    # literal_count
    buf.extend(u32(len(literals)))
    for lit in literals:
        buf.extend(lit)
    # counts: _ext_handles_count, literal_slot_size, opcode_count, T, num_cvs
    # literal_slot_size must be in (16, 24, 28, 32)
    buf.extend(u32(0))
    buf.extend(u32(16))
    buf.extend(u32(len(opcodes)))
    buf.extend(u32(1))
    buf.extend(u32(len(cv_names)))
    # cv_names
    for name in cv_names:
        buf.extend(zstr(name))
    # opcodes
    for op in opcodes:
        buf.extend(op)
    # lr_count = 0
    buf.extend(u32(0))
    # tc_count = 0
    buf.extend(u32(0))
    # static variables hashtable count = 0
    buf.extend(u32(0))
    # doc_comment = None
    buf.extend(zstr(None))
    # line_start = 1, line_end = 1, depth = 0
    buf.extend(u32(1))
    buf.extend(u32(1))
    buf.extend(u32(0))
    # attributes count = 0
    buf.extend(u32(0))
    # nested_count = 0
    buf.extend(u32(0))

    return bytes(buf)


def make_synthetic_opcode(
    opcode_num: int,
    res_nibble: int = 0xF,
    op1_nibble: int = 0xF,
    op2_nibble: int = 0xF,
    ext_nibble: int = 0xF,
    payload: bytes = b"",
    lineno: int = 1,
) -> bytes:
    # opcode u8
    # type_word u32:
    # ext_n: bits 12..15
    # res_n: bits 8..11
    # op2_n: bits 4..7
    # op1_n: bits 0..3
    type_word = (ext_nibble << 12) | (res_nibble << 8) | (op2_nibble << 4) | op1_nibble
    return bytes([opcode_num]) + u32(type_word) + payload + u32(lineno)


def test_stream_reader():
    r = StreamReader(b"\x01\x02\x03\x04\x05\x06\x07\x08")
    assert r.read_u8() == 1
    assert r.read_u32() == 0x05040302
    r.skip(2)
    assert r.pos == 7
    with pytest.raises(ParseError):
        r.read_u32()


def test_normalize_operands():
    # Constant operand
    const_op = {"type": 1, "type_name": "IS_CONST", "literal_value": "hello", "literal_index": 0}
    norm = _normalize_operand(const_op)
    assert norm["has_literal"] is True
    assert norm["literal"] == "hello"

    # CV operand
    cv_op = {"type": 8, "type_name": "IS_CV", "variable_name": "$message", "variable_index": 0, "zend_value": 0}
    norm = _normalize_operand(cv_op)
    assert norm["cv_name"] == "message"
    assert norm["cv_index"] == 0

    # Unused jump target
    jmp_op = {"type": 0, "type_name": "IS_UNUSED", "jump_target": 5}
    norm = _normalize_operand(jmp_op)
    assert norm["opline_num"] == 5


def test_calc_jump_targets():
    op = {
        "opcode_name": "ZEND_JMP",
        "op1": {"type_name": "IS_UNUSED", "jump_target": 7},
        "op2": {"type_name": "IS_UNUSED"},
        "result": {"type_name": "IS_UNUSED"},
    }
    assert _calc_jump_targets(op) == [7]

    op_cond = {
        "opcode_name": "ZEND_JMPZ",
        "op1": {"type_name": "IS_CV", "variable_name": "$flag"},
        "op2": {"type_name": "IS_UNUSED", "zend_value": 12},
        "result": {"type_name": "IS_UNUSED"},
    }
    assert _calc_jump_targets(op_cond) == [12]


def test_synthetic_container_parse_and_decompile():
    # Construct a valid synthetic container:
    # 1. Magic: b"SOURCEGUARDIAN\x00" (15 bytes)
    # 2. ver=0x21, flags=0, reserved=0, 0
    # 3. phase 0 (funcs): tag 0x02, key_len 0, func op_array, tag 0x00
    # 4. phase 1 (classes): tag 0x00
    # 5. main: main op_array

    # Function opcodes:
    # Op 0: ZEND_ECHO (136): op1 is const literal 0 ("Hello world!"), result/op2 unused
    # op1 nibble = 3 (const literal): reads u8 then u32 literal_index
    op_echo = make_synthetic_opcode(
        opcode_num=136,  # ZEND_ECHO
        op1_nibble=3,
        payload=b"\x00" + u32(0),  # literal index 0
    )
    # Op 1: ZEND_RETURN (62): op1 is const literal 1 (1)
    op_return = make_synthetic_opcode(
        opcode_num=62,  # ZEND_RETURN
        op1_nibble=3,
        payload=b"\x00" + u32(1),  # literal index 1
    )

    func_bytes = make_synthetic_op_array(
        function_name="say_hello",
        cv_names=[],
        literals=[make_zval_string("Hello world!"), make_zval_int(1)],
        opcodes=[op_echo, op_return],
    )

    # Main opcodes:
    # Op 0: ZEND_RETURN (62): op1 const literal 0 (1)
    main_return = make_synthetic_opcode(
        opcode_num=62,
        op1_nibble=3,
        payload=b"\x00" + u32(0),
    )
    main_bytes = make_synthetic_op_array(
        function_name="",
        cv_names=[],
        literals=[make_zval_int(1)],
        opcodes=[main_return],
    )

    container_buf = bytearray()
    container_buf.extend(b"SOURCEGUARDIAN\x00")
    container_buf.extend(u32(0x21))  # ver = 0x21
    container_buf.extend(u32(0))     # flags = 0
    container_buf.extend(u32(0))     # reserved
    container_buf.extend(u32(0))     # reserved

    # Phase 0: Functions table
    container_buf.append(2)          # tag = 2 (func)
    container_buf.extend(u32(0))     # composite key len = 0
    container_buf.extend(func_bytes) # op_array
    container_buf.append(0)          # end of funcs

    # Phase 1: Classes table
    container_buf.append(0)          # end of classes

    # Main op_array
    container_buf.extend(main_bytes)

    # Now parse the container!
    ir = build_ir(bytes(container_buf), source_file="test_synthetic.php")
    assert ir["format"] == "icdump-ir-v1"
    assert "main" in ir["op_arrays"]
    assert "say_hello" in ir["function_index"]

    fn_id = ir["function_index"]["say_hello"]
    fn_oa = ir["op_arrays"][fn_id]
    assert fn_oa["function_name"] == "say_hello"
    assert len(fn_oa["opcodes"]) == 2
    assert fn_oa["opcodes"][0]["opcode_name"] == "ZEND_ECHO"
    assert fn_oa["opcodes"][0]["op1"]["literal"] == "Hello world!"
    assert fn_oa["opcodes"][1]["opcode_name"] == "ZEND_RETURN"

    # Now feed into php_reconstructor AST decompiler!
    program = parse_dump(ir)
    assert program.entry == "main"
    ast = decompile_program(program)
    ast = optimize(ast)
    php_code = emit_php(ast)

    assert "function say_hello()" in php_code
    assert "echo 'Hello world!';" in php_code or 'echo "Hello world!";' in php_code
    assert "return 1;" in php_code


def make_synthetic_property(
    name: str,
    flags: int,
    default: bytes,
    doc: str = None,
    type_info: bytes = None,
) -> bytes:
    return (
        zstr(name)
        + u32(flags)
        + zstr(None)     # mangled/typed name
        + zstr(doc)
        + default
        + (type_info if type_info is not None else u32(0))
        + u32(0)         # attributes
    )


def class_type_info(name: str, nullable: bool = False) -> bytes:
    return u32(0x10000000 | (0x2 if nullable else 0)) + zstr(name)


def builtin_type_info(mask: int, nullable: bool = False) -> bytes:
    return u32(mask | (0x2 if nullable else 0))


def union_type_info(members: list[bytes], nullable: bool = False) -> bytes:
    return u32(0x40000000 | (0x2 if nullable else 0)) + u32(len(members)) + b"".join(members)


def make_synthetic_class(
    class_name: str,
    methods: list[tuple[str, bytes]] = None,
    constants: dict[str, bytes] = None,
    properties: list[bytes] = None,
    class_flags: int = 0,
    static_properties: int = 0,
) -> bytes:
    if methods is None:
        methods = []
    if constants is None:
        constants = {}
    if properties is None:
        properties = []

    buf = bytearray()
    buf.append(0xFF)  # version_gate
    buf.append(2)     # type_byte = 2
    buf.extend(zstr(class_name))
    buf.extend(u32(class_flags))
    buf.extend(zstr(None))  # parent_name
    buf.extend(u32(0))  # interfaces count
    buf.extend(u32(0))  # traits count
    buf.extend(u32(0))  # trait aliases
    buf.extend(u32(0))  # trait precedences
    buf.extend(zstr(None))  # doc_comment
    buf.extend(u32(len(constants)))  # constants count
    for cname, cval in constants.items():
        buf.extend(zstr(cname))
        buf.extend(cval)
        buf.extend(u32(0))
        buf.extend(zstr(None))
        buf.extend(u32(0))  # _skip_attributes
        buf.extend(u32(0))
    buf.extend(u32(len(properties)))
    buf.extend(u32(static_properties))
    for prop in properties:
        buf.extend(prop)
    # _skip_class_attributes:
    buf.extend(u32(0))  # attributes count
    buf.extend(u32(0))  # trailing flags/line word
    # static properties hashtable:
    buf.extend(u32(0))  # count = 0
    # methods:
    buf.extend(u32(len(methods)))
    for mname, moa in methods:
        buf.extend(zstr(mname))
        buf.extend(moa)

    return bytes(buf)


def make_synthetic_container(classes: list[bytes], main: bytes) -> bytes:
    buf = bytearray()
    buf.extend(b"SOURCEGUARDIAN\x00")
    buf.extend(u32(0x21))  # ver
    buf.extend(u32(0))     # flags
    buf.extend(u32(0))
    buf.extend(u32(0))
    buf.append(0)          # no functions
    for cls in classes:
        buf.append(1)
        buf.extend(u32(0))  # composite key
        buf.extend(cls)
    buf.append(0)          # end of classes
    buf.extend(main)
    return bytes(buf)


def test_synthetic_class_parse_and_decompile():
    # Construct a class ShoppingCart with method getCount returning 42
    op_return = make_synthetic_opcode(
        opcode_num=62,  # ZEND_RETURN
        op1_nibble=3,
        payload=b"\x00" + u32(0),  # literal index 0 (42)
    )
    method_bytes = make_synthetic_op_array(
        function_name="getCount",
        cv_names=[],
        literals=[make_zval_int(42)],
        opcodes=[op_return],
    )

    class_bytes = make_synthetic_class(
        class_name="ShoppingCart",
        methods=[("getCount", method_bytes)],
    )

    main_return = make_synthetic_opcode(
        opcode_num=62,
        op1_nibble=3,
        payload=b"\x00" + u32(0),
    )
    main_bytes = make_synthetic_op_array(
        function_name="",
        cv_names=[],
        literals=[make_zval_int(1)],
        opcodes=[main_return],
    )

    container_buf = bytearray()
    container_buf.extend(b"SOURCEGUARDIAN\x00")
    container_buf.extend(u32(0x21))  # ver = 0x21
    container_buf.extend(u32(0))     # flags = 0
    container_buf.extend(u32(0))     # reserved
    container_buf.extend(u32(0))     # reserved

    # Phase 0: Functions table (empty)
    container_buf.append(0)

    # Phase 1: Classes table
    container_buf.append(1)          # tag = 1 (class)
    container_buf.extend(u32(0))     # composite key len = 0
    container_buf.extend(class_bytes)
    container_buf.append(0)          # end of classes

    # Main op_array
    container_buf.extend(main_bytes)

    ir = build_ir(bytes(container_buf), source_file="test_class.php")
    assert ir["format"] == "icdump-ir-v1"
    assert len(ir["class_index"]) == 1

    cls_id = list(ir["class_index"].keys())[0]
    cls_info = ir["class_index"][cls_id]
    assert cls_info["name"] == "ShoppingCart"
    assert "getCount" in cls_info["methods"]

    # End to end decompile
    program = parse_dump(ir)
    ast = decompile_program(program)
    ast = optimize(ast)
    php_code = emit_php(ast)

    assert "class ShoppingCart" in php_code
    assert "function getCount()" in php_code
    assert "return 42;" in php_code


def encode_literal_lzo(data: bytes) -> bytes:
    n = len(data)
    if n <= 238:
        return bytes([17 + n]) + data + b"\x11\x00\x00"
    rem = n - 18
    zeros = rem // 255
    tail = rem % 255
    return b"\x00" + (b"\x00" * zeros) + bytes([tail]) + data + b"\x11\x00\x00"


def _cbc_encrypt(cipher, data: bytes) -> bytes:
    out = bytearray()
    prev_left = prev_right = 0
    for offset in range(0, len(data) - 7, 8):
        left = int.from_bytes(data[offset:offset + 4], "big") ^ prev_left
        right = int.from_bytes(data[offset + 4:offset + 8], "big") ^ prev_right
        prev_left, prev_right = cipher.encrypt_block(left, right)
        out += struct.pack(">II", prev_left, prev_right)
    return bytes(out)


def _seal_section(key: bytes, raw_section: bytes) -> bytes:
    from engines.sourceguardian.container import Blowfish, rol1
    compressed = encode_literal_lzo(raw_section)
    declen = len(raw_section)
    length = 12 + len(compressed) + 3
    data = struct.pack("<III", 0, length, declen) + compressed + b"\x00\x00\x00"
    checksum = rol1(b"\x00\x00\x00\x00" + data[4:])
    data = struct.pack("<I", checksum) + data[4:]
    data += b"\x00" * ((-len(data)) % 8)
    return _cbc_encrypt(Blowfish(key), data)


def test_full_sg_file_end_to_end_decompile(tmp_path):
    from engines.sourceguardian.container import load_keys
    from decompile import decompile_file
    import base64

    keys = load_keys()
    key = keys[0]

    # Create synthetic function say_hello()
    op_echo = make_synthetic_opcode(
        opcode_num=136,
        op1_nibble=3,
        payload=b"\x00" + u32(0),
    )
    op_return = make_synthetic_opcode(
        opcode_num=62,
        op1_nibble=3,
        payload=b"\x00" + u32(1),
    )
    func_bytes = make_synthetic_op_array(
        function_name="say_hello",
        cv_names=[],
        literals=[make_zval_string("Hello from SourceGuardian!"), make_zval_int(1)],
        opcodes=[op_echo, op_return],
    )
    main_return = make_synthetic_opcode(
        opcode_num=62,
        op1_nibble=3,
        payload=b"\x00" + u32(0),
    )
    main_bytes = make_synthetic_op_array(
        function_name="",
        cv_names=[],
        literals=[make_zval_int(1)],
        opcodes=[main_return],
    )

    body_buf = bytearray()
    body_buf.extend(b"SOURCEGUARDIAN\x00")
    body_buf.extend(u32(0x21))
    body_buf.extend(u32(0))
    body_buf.extend(u32(0))
    body_buf.extend(u32(0))
    body_buf.append(2)
    body_buf.extend(u32(0))
    body_buf.extend(func_bytes)
    body_buf.append(0)
    body_buf.append(0)
    body_buf.extend(main_bytes)

    raw_body = bytes(body_buf)
    raw_meta = b'{"licensed_to":"SG User"}'

    enc_meta = _seal_section(key, raw_meta)
    enc_body = _seal_section(key, raw_body)

    # Preheader TLV:
    preheader = (
        b"\x00" + struct.pack("<I", 0) + struct.pack("<I", 0x21)
        + b"\x04" + struct.pack("<I", len(enc_meta))
        + b"\x80" + struct.pack("<I", 4) + struct.pack("<I", 0x7)
        + b"\xff"
    )

    machine_prefix = b"123456789012"
    container = machine_prefix + preheader + enc_meta + enc_body
    b64_payload = base64.b64encode(container).decode("ascii")

    php_script = f"<?php\n// SourceGuardian loader stub\nsg_load('{b64_payload}');\n?>"

    src_file = tmp_path / "protected_sg.php"
    out_file = tmp_path / "decompiled_sg.php"
    src_file.write_text(php_script, encoding="utf-8")

    success, syntax_ok, err, status = decompile_file(
        src_file,
        output_path=out_file,
    )

    assert success is True
    assert out_file.exists()
    decompiled_code = out_file.read_text(encoding="utf-8")
    assert "function say_hello()" in decompiled_code
    assert "Hello from SourceGuardian!" in decompiled_code


def _main_return() -> bytes:
    return make_synthetic_op_array(
        literals=[make_zval_int(1)],
        opcodes=[
            make_synthetic_opcode(
                opcode_num=62,
                op1_nibble=3,
                payload=b"\x00" + u32(0),
            )
        ],
    )


def test_synthetic_class_keeps_flags_properties_and_parameter_defaults():
    recv_init = make_synthetic_opcode(
        opcode_num=64,  # ZEND_RECV_INIT
        op1_nibble=2,
        op2_nibble=3,
        payload=b"\x00" + u32(1) + b"\x00" + u32(0),
    )
    op_return = make_synthetic_opcode(
        opcode_num=62,
        op1_nibble=3,
        payload=b"\x00" + u32(1),
    )
    method_bytes = make_synthetic_op_array(
        function_name="greet",
        literals=[make_zval_string("hello"), make_zval_int(1)],
        opcodes=[recv_init, op_return],
        num_args=1,
        required_num_args=0,
        arg_names=["greeting"],
    )
    class_bytes = make_synthetic_class(
        class_name="Greeter",
        class_flags=0x20,  # ZEND_ACC_FINAL
        properties=[
            make_synthetic_property("count", 0x11, make_zval_int(1)),
            make_synthetic_property("name", 0x01, make_zval_string("world")),
        ],
        static_properties=1,
        methods=[("greet", method_bytes)],
    )

    ir = build_ir(
        make_synthetic_container([class_bytes], _main_return()),
        source_file="props.php",
    )
    cls = next(iter(ir["class_index"].values()))
    assert cls["ce_flags_decoded"]["is_final"] is True
    assert cls["properties_merged"]["count"]["is_static"] is True
    assert cls["properties_merged"]["name"]["flags_decoded"]["visibility"] == "public"
    assert cls["properties_merged"]["name"]["default_value"] == "world"

    php_code = emit_php(optimize(decompile_program(parse_dump(ir))))
    assert "final class Greeter" in php_code
    assert "public static $count = 1;" in php_code
    assert "public $name = 'world';" in php_code
    assert "function greet($greeting = 'hello')" in php_code


def test_synthetic_abstract_class_flag_is_emitted():
    class_bytes = make_synthetic_class("Base", class_flags=0x40)  # ZEND_ACC_ABSTRACT

    ir = build_ir(
        make_synthetic_container([class_bytes], _main_return()),
        source_file="abstract.php",
    )

    php_code = emit_php(optimize(decompile_program(parse_dump(ir))))
    assert "abstract class Base" in php_code


def test_synthetic_typed_properties_keep_types_nullable_and_readonly():
    undef = u32(0) + u32(0)
    class_bytes = make_synthetic_class(
        "Typed",
        properties=[
            make_synthetic_property(
                "created",
                0x01,
                undef,
                type_info=class_type_info("DateTimeImmutable", nullable=True),
            ),
            make_synthetic_property(
                "id",
                0x81,  # public readonly
                undef,
                type_info=builtin_type_info(0x40),  # MAY_BE_STRING
            ),
            make_synthetic_property(
                "value",
                0x01,
                undef,
                type_info=union_type_info([u32(0x10), u32(0x40)], nullable=True),
            ),
        ],
    )

    ir = build_ir(
        make_synthetic_container([class_bytes], _main_return()),
        source_file="typed.php",
    )
    cls = next(iter(ir["class_index"].values()))
    assert cls["properties_merged"]["created"]["type_name"] == "DateTimeImmutable"
    assert cls["properties_merged"]["created"]["allow_null"] is True
    assert cls["properties_merged"]["id"]["is_readonly"] is True
    assert cls["properties_merged"]["value"]["type_name"] == "int|string"

    php_code = emit_php(optimize(decompile_program(parse_dump(ir))))
    assert "public ?DateTimeImmutable $created;" in php_code
    assert "public readonly string $id;" in php_code
    assert "public int|string|null $value;" in php_code


