"""Milestone 4: functions, methods, classes."""

from conftest import arg, const, cv, dump, op, op_array, reconstruct, sv, tmp, unused


def test_function_with_params():
    oa = op_array(
        [
            op("ZEND_RECV", result=cv(0, "a")),
            op("ZEND_RECV", result=cv(1, "b")),
            op("ZEND_ADD", op1=cv(0, "a"), op2=cv(1, "b"), result=tmp(96)),
            op("ZEND_RETURN", op1=tmp(96)),
        ],
        name="add",
        cvs=["a", "b"],
        arg_info=[arg(0, "a"), arg(1, "b")],
        num_args=2,
        required_num_args=2,
    )
    out = reconstruct(dump(main_ops=[], functions={"add": oa}))
    assert "function add($a, $b) {" in out
    assert "return $a + $b;" in out


def test_param_default_from_recv_init():
    oa = op_array(
        [
            op("ZEND_RECV", result=cv(0, "name"), op1={"type": 0, "type_name": "IS_UNUSED", "num": 1}),
            op("ZEND_RECV_INIT", op2=const("world"), result=cv(1, "greeting"),
               op1={"type": 0, "type_name": "IS_UNUSED", "num": 2}),
            op("ZEND_RETURN", op1=cv(0, "name")),
        ],
        name="greet",
        cvs=["name", "greeting"],
        arg_info=[arg(0, "name"), arg(1, "greeting", has_default=True)],
        num_args=2,
        required_num_args=1,
    )
    out = reconstruct(dump(main_ops=[], functions={"greet": oa}))
    assert "function greet($name, $greeting = 'world') {" in out


def test_by_ref_and_typed_params():
    oa = op_array(
        [op("ZEND_RETURN", op1=const(None))],
        name="f",
        cvs=["items", "n"],
        arg_info=[arg(0, "items", type_name="array", by_ref=True), arg(1, "n", type_name="int")],
        num_args=2,
        required_num_args=2,
    )
    out = reconstruct(dump(main_ops=[], functions={"f": oa}))
    assert "function f(array &$items, int $n) {" in out


def test_bogus_type_names_dropped():
    oa = op_array(
        [op("ZEND_RETURN", op1=const(None))],
        name="f",
        cvs=["x"],
        arg_info=[arg(0, "x", type_name="type(128)")],
        num_args=1,
        required_num_args=1,
    )
    out = reconstruct(dump(main_ops=[], functions={"f": oa}))
    assert "function f($x) {" in out
    assert "type(128)" not in out


def test_class_with_method_property_constant():
    method_id = "class:466f6f:method:626172"
    class_raw = {
        "name": sv("Foo"),
        "parent": sv("Base"),
        "interfaces": [],
        "ce_flags_decoded": {},
        "constants_table": {"LIMIT": {"value": sv(10)}},
        "properties_merged": {
            "count": {
                "name": "count",
                "flags_decoded": {"visibility": "protected"},
                "is_static": False,
                "has_default_value": True,
                "default_value": sv(0),
            }
        },
        "methods": {"bar": method_id},
    }
    method_oa = op_array(
        [op("ZEND_RETURN", op1=const(True))],
        kind="method",
        name="bar",
        fn_flags_decoded={"visibility": "public", "is_static": True},
        meta={"class": "class:466f6f", "method_name": sv("bar")},
    )
    out = reconstruct(dump(
        main_ops=[],
        op_arrays={method_id: method_oa},
        class_index={"class:466f6f": class_raw},
    ))
    assert "class Foo extends Base {" in out
    assert "const LIMIT = 10;" in out
    assert "protected $count = 0;" in out
    assert "public static function bar() {" in out
    assert "return true;" in out


def test_main_trailing_return_dropped():
    out = reconstruct(dump(main_ops=[
        op("ZEND_ECHO", op1=const("hello")),
        op("ZEND_RETURN", op1=const(1)),
    ]))
    assert "echo 'hello';" in out
    assert "return" not in out


def test_implicit_function_return_dropped():
    oa = op_array(
        [
            op("ZEND_ECHO", op1=const("x")),
            op("ZEND_RETURN", op1=const(None)),
        ],
        name="f",
    )
    out = reconstruct(dump(main_ops=[], functions={"f": oa}))
    assert "echo 'x';" in out
    assert "return" not in out
