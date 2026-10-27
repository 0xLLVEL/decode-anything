"""IR layer: basic block splitting and CFG edges."""

from conftest import const, cv, op, op_array, tmp
from php_reconstructor.ir import build_function_ir
from php_reconstructor.opcode import OpArray


def _oa(opcodes):
    return OpArray.from_json("f", op_array(opcodes))


def test_single_block():
    ir = build_function_ir(_oa([
        op("ZEND_ASSIGN", op1=cv(0, "a"), op2=const(1)),
        op("ZEND_RETURN", op1=const(None)),
    ]))
    assert len(ir.blocks) == 1
    assert ir.blocks[0].start == 0
    assert ir.blocks[0].end == 1


def test_branch_splits_blocks():
    # 0: JMPZ cond -> 3 ; 1: assign ; 2: (fallthrough) ; 3: return
    ir = build_function_ir(_oa([
        op("ZEND_JMPZ", op1=cv(0, "c"), jump=[3]),
        op("ZEND_ASSIGN", op1=cv(1, "a"), op2=const(1)),
        op("ZEND_ASSIGN", op1=cv(1, "a"), op2=const(2)),
        op("ZEND_RETURN", op1=const(None)),
    ]))
    assert len(ir.blocks) == 3
    entry = ir.blocks[0]
    assert entry.end == 0
    # Entry branches to both the fallthrough block and the jump target.
    assert sorted(entry.successors) == [1, 2]
    target_block = ir.block_at(3)
    assert target_block is not None
    assert sorted(target_block.predecessors) == [0, 1]


def test_jmp_has_no_fallthrough_edge():
    ir = build_function_ir(_oa([
        op("ZEND_JMP", jump=[2]),
        op("ZEND_ASSIGN", op1=cv(0, "a"), op2=const(1)),
        op("ZEND_RETURN", op1=const(None)),
    ]))
    entry = ir.blocks[0]
    assert entry.successors == [ir.block_of_op[2]]


def test_empty_op_array():
    ir = build_function_ir(_oa([]))
    assert ir.blocks == []
    assert ir.entry is None
