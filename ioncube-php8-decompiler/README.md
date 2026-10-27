# ionCube PHP 8.x Decompiler

`php-reconstructor` rebuilds readable PHP source code from JSON opcode dumps
generated from ionCube-protected applications. It is designed for PHP 8.x,
with current support focused on PHP 8.1 through PHP 8.4.

Pipeline:

```
JSON opcode dump  ->  normalized opcode model  ->  IR (basic blocks / CFG)
                  ->  PHP AST  ->  AST cleanup passes  ->  PHP source
```

## Installation

```bash
cd php_reconstructor
pip install -e .[dev]
```

Requires Python 3.11+.

## Usage

```bash
php-reconstruct input.opcodes.json -o output.php   # reconstruct to a file
php-reconstruct input.opcodes.json                 # reconstruct to stdout
php-reconstruct input.opcodes.json --dump-ir       # basic blocks / CFG per op_array
php-reconstruct input.opcodes.json --dump-ast      # reconstructed AST as JSON
php-reconstruct input.opcodes.json --debug-opcodes # normalized opcode listing
```

Useful extras:

```bash
--only NAME        # restrict --dump-ir/--debug-opcodes to one op_array
                   # (substring of the id or the function name)
--no-optimize      # skip AST cleanup passes (raw decompiler output)
--show-warnings    # print decompiler reconciliation warnings to stderr
```

Try the bundled example:

```bash
python examples/make_example.py
php-reconstruct examples/hello.opcodes.json
```

## Architecture

```
src/php_reconstructor/
├── cli.py                  # argparse CLI / entry point
├── loader/                 # JSON -> Program (parses icdump-ir-v1, unwraps safe_value)
├── opcode/                 # normalized models: Operand, Opcode, OpArray, Program
│   └── constants.py        # zend constants (cast types, ASSIGN_OP map, flags...)
├── ir/                     # basic blocks + CFG per op_array
├── ast/                    # PHP AST node definitions (dataclasses, to_dict())
├── decompiler/
│   ├── context.py          # temp-slot tracking, call frames, statement sinks
│   ├── handlers/           # one isolated handler per opcode (registry pattern)
│   │   ├── basic.py        # assignments, binary/unary ops, casts, inc/dec
│   │   ├── calls.py        # INIT_*CALL / SEND_* / DO_FCALL protocol
│   │   ├── fetch.py        # dim/property/constant fetches, isset/empty/unset
│   │   ├── arrays.py       # INIT_ARRAY / ADD_ARRAY_ELEMENT / in_array...
│   │   └── misc.py         # echo, return, silence, ropes, includes, closures
│   ├── structurer.py       # control-flow reconstruction (if/else, loops, try)
│   ├── program.py          # program level: functions, methods, classes
│   └── optimize.py         # AST cleanup passes
└── emitter/                # AST -> formatted PHP (precedence-aware)
```

### Design notes

* **Temp-slot model.** The Zend VM stores intermediate values in TMP/VAR
  slots; the decompiler mirrors this with a map from slot to AST
  expression. Consuming an operand pops its entry, so expressions inline
  naturally and anything left over signals a dump anomaly.
* **LIFO reconciliation.** ionCube dumps occasionally rewrite operand var
  numbers on semantically-resolved opcodes (consumer slot != producer
  slot, or `var: null`). When an exact slot lookup fails, the decompiler
  falls back to the most recently produced live temp -- correct in
  practice because Zend temps live in near-stack order. Run with
  `--show-warnings` to see every reconciliation.
* **Isolated handlers.** Each opcode handler is a standalone function
  registered by name; adding support for a new opcode never touches the
  walker. Unknown opcodes degrade to `/* [opcode N] NAME */` comments so
  the output stays valid PHP and nothing is silently dropped.
* **Control flow.** The structurer pattern-matches the shapes the PHP
  compiler emits: top-tested and bottom-tested `while` (including
  conditions with side effects, which are primed before the loop and
  re-evaluated at the end of the body), `foreach` via
  FE_RESET/FE_FETCH (with the older encoder shape where the key arrives
  in a temp), if/else/elseif, ternaries, `&&`/`||` short-circuits,
  do-while back edges, break/continue, `switch` (from the CASE/JMPNZ
  dispatch chain, repaired from SWITCH_STRING/LONG byte-offset tables when
  their opcode stride can be inferred uniquely), and try/catch from the
  op_array exception table.

## Milestones (all implemented)

1. **M1** -- project skeleton, CLI, JSON loader, Opcode/Operand models.
2. **M2** -- expressions: variables, constants, assignments, binary ops,
   function/method calls, `return`.
3. **M3** -- basic blocks, jump analysis, `if/else`, `while`, `foreach`,
   `switch`, ternaries, short-circuit operators, break/continue, try/catch.
4. **M4** -- functions, methods, classes (params, defaults, by-ref,
   visibility, static, constants, properties).
5. **M5** -- clean PHP emitter with operator precedence, AST optimizer
   (boolean-cast stripping, comparison inversion, elseif collapsing,
   dead implicit returns, redundant continue).

## Validation against real dumps

All three real dumps in the parent directory reconstruct to PHP that
passes `php -l` with zero leaked temporaries:

| dump | op_arrays | output | fallback comments |
|---|---|---|---|
| Example 1 | 11 | 392 lines | 0 |
| Example 2 | 179 | ~2700 lines | 5 (one `switch`) |
| Example 3 | 124 | ~1750 lines | 0 |

## Known limitations

* `match`, generators, fibers, attributes and enums are not handled
  (absent from PHP 8.1 ionCube dumps seen so far).
* `for(;;)` loops are emitted as the equivalent `while` loop -- the
  opcode stream does not distinguish them.
* Loop conditions with side effects are reconstructed via the
  priming-read transformation, which duplicates the condition statement
  before the loop and at the end of the body (semantically equivalent).

## Tests

```bash
python -m pytest
```

82 tests: unit tests per milestone (loader, models, IR, expressions,
control flow, declarations, emitter, optimizer) plus integration tests
that reconstruct the real dumps when present (skipped otherwise).
