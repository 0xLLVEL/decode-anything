"""IR layer: basic blocks and a per-op_array control-flow graph."""

from __future__ import annotations

from dataclasses import dataclass, field

from ..opcode import OpArray, Opcode
from ..opcode.constants import NO_FALLTHROUGH


@dataclass(slots=True)
class BasicBlock:
    id: int
    start: int  # first opcode index (inclusive)
    end: int    # last opcode index (inclusive)
    successors: list[int] = field(default_factory=list)
    predecessors: list[int] = field(default_factory=list)

    def opcodes(self, op_array: OpArray) -> list[Opcode]:
        return op_array.opcodes[self.start : self.end + 1]


@dataclass(slots=True)
class FunctionIR:
    op_array: OpArray
    blocks: list[BasicBlock] = field(default_factory=list)
    block_of_op: dict[int, int] = field(default_factory=dict)

    @property
    def entry(self) -> BasicBlock | None:
        return self.blocks[0] if self.blocks else None

    def block_at(self, op_index: int) -> BasicBlock | None:
        block_id = self.block_of_op.get(op_index)
        return self.blocks[block_id] if block_id is not None else None


def build_function_ir(op_array: OpArray) -> FunctionIR:
    """Split an op_array into basic blocks and connect jump/fallthrough edges."""
    ops = op_array.opcodes
    ir = FunctionIR(op_array=op_array)
    count = len(ops)
    if count == 0:
        return ir

    leaders: set[int] = {0}
    for op in ops:
        for target in op.jump_targets:
            if 0 <= target < count:
                leaders.add(target)
        if op.jump_targets and op.index + 1 < count:
            leaders.add(op.index + 1)
    for entry in op_array.try_catch:
        for boundary in (entry.try_op, entry.catch_op, entry.finally_op):
            if boundary is not None and 0 <= boundary < count:
                leaders.add(boundary)

    ordered = sorted(leaders)
    for block_id, start in enumerate(ordered):
        end = ordered[block_id + 1] - 1 if block_id + 1 < len(ordered) else count - 1
        block = BasicBlock(id=block_id, start=start, end=end)
        ir.blocks.append(block)
        for i in range(start, end + 1):
            ir.block_of_op[i] = block_id

    for block in ir.blocks:
        last = ops[block.end]
        for target in last.jump_targets:
            succ = ir.block_of_op.get(target)
            if succ is not None and succ not in block.successors:
                block.successors.append(succ)
        if last.name not in NO_FALLTHROUGH and block.end + 1 < count:
            succ = ir.block_of_op.get(block.end + 1)
            if succ is not None and succ not in block.successors:
                block.successors.append(succ)

    for block in ir.blocks:
        for succ in block.successors:
            if block.id not in ir.blocks[succ].predecessors:
                ir.blocks[succ].predecessors.append(block.id)

    return ir
