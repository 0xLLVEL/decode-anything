"""Command-line interface.

Usage::

    php-reconstruct input.json -o output.php
    php-reconstruct input.json --dump-ir
    php-reconstruct input.json --dump-ast
    php-reconstruct input.json --debug-opcodes
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import __version__
from .decompiler import decompile_program, optimize
from .emitter import emit_php
from .ir import build_function_ir
from .loader import DumpFormatError, load_dump
from .opcode import OpArray, Program


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="php-reconstruct",
        description="Reconstruct PHP source code from a PHP 8.1 opcode dump (icdump-ir-v1 JSON).",
    )
    parser.add_argument("input", help="path to the .opcodes.json dump")
    parser.add_argument("-o", "--output", metavar="FILE", help="write PHP to FILE instead of stdout")
    parser.add_argument("--dump-ir", action="store_true", help="print the IR (basic blocks / CFG) and exit")
    parser.add_argument("--dump-ast", action="store_true", help="print the reconstructed AST as JSON and exit")
    parser.add_argument("--debug-opcodes", action="store_true", help="print the normalized opcode listing and exit")
    parser.add_argument("--only", metavar="ID", help="restrict --dump-ir/--debug-opcodes to one op_array id (substring match)")
    parser.add_argument("--no-optimize", action="store_true", help="skip AST cleanup passes")
    parser.add_argument("--show-warnings", action="store_true", help="print decompiler warnings to stderr")
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_arg_parser().parse_args(argv)

    try:
        program = load_dump(args.input)
    except FileNotFoundError:
        print(f"error: file not found: {args.input}", file=sys.stderr)
        return 2
    except DumpFormatError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    if args.debug_opcodes:
        _print_opcodes(program, args.only)
        return 0
    if args.dump_ir:
        _print_ir(program, args.only)
        return 0

    php_file = decompile_program(program)
    if not args.no_optimize:
        php_file = optimize(php_file)

    if args.dump_ast:
        json.dump(php_file.to_dict(), sys.stdout, indent=2, default=str)
        print()
        return 0

    source = emit_php(php_file)
    if args.output:
        Path(args.output).write_text(source, encoding="utf-8", newline="\n")
        print(f"wrote {args.output} ({len(source.splitlines())} lines)", file=sys.stderr)
    else:
        sys.stdout.write(source)

    if args.show_warnings:
        _print_warnings(program)
    return 0


def _selected(program: Program, only: str | None) -> list[OpArray]:
    op_arrays = list(program.op_arrays.values())
    if only:
        op_arrays = [
            oa
            for oa in op_arrays
            if only in oa.id or (oa.function_name and only in oa.function_name)
        ]
    return op_arrays


def _print_opcodes(program: Program, only: str | None) -> None:
    for op_array in _selected(program, only):
        title = op_array.function_name or op_array.id
        print(f"== {op_array.id} ({op_array.kind}) {title} ==")
        for op in op_array.opcodes:
            parts = [f"{op.index:5d}  {op.name:<28}"]
            for label, operand in (("op1", op.op1), ("op2", op.op2), ("res", op.result)):
                if operand.is_unused:
                    continue
                if operand.is_const:
                    parts.append(f"{label}=const({operand.const_value()!r})")
                elif operand.is_cv:
                    parts.append(f"{label}=${operand.cv_name or '?'}")
                else:
                    parts.append(f"{label}=t{operand.temp_key}")
            if op.jump_targets:
                parts.append(f"-> {list(op.jump_targets)}")
            if op.extended_value:
                parts.append(f"ext={op.extended_value}")
            print("  " + " ".join(parts))
        print()


def _print_ir(program: Program, only: str | None) -> None:
    for op_array in _selected(program, only):
        ir = build_function_ir(op_array)
        title = op_array.function_name or op_array.id
        print(f"== {op_array.id} ({op_array.kind}) {title}: {len(ir.blocks)} blocks ==")
        for block in ir.blocks:
            succ = ", ".join(f"B{s}" for s in block.successors) or "-"
            pred = ", ".join(f"B{p}" for p in block.predecessors) or "-"
            print(f"  B{block.id}: ops {block.start}..{block.end}  preds[{pred}] succs[{succ}]")
            for op in block.opcodes(op_array):
                print(f"      {op.index:5d}  {op.name}")
        print()


def _print_warnings(program: Program) -> None:
    php_file_warnings: list[str] = []
    from .decompiler.structurer import decompile_body

    for op_array in program.op_arrays.values():
        _, ctx = decompile_body(op_array, program)
        php_file_warnings.extend(ctx.warnings)
    for warning in php_file_warnings:
        print(f"warning: {warning}", file=sys.stderr)


if __name__ == "__main__":
    raise SystemExit(main())
