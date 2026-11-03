# Decode-Anything: Unified PHP Decompiler & Deobfuscator

[![Python Tests](https://img.shields.io/badge/tests-214%20passed-brightgreen.svg)](tests/)
[![Target PHP](https://img.shields.io/badge/PHP-7.2%20%E2%80%93%208.4-blue.svg)](https://php.net)
[![Supported](https://img.shields.io/badge/Encoders-ionCube%20%7C%20SourceGuardian%20%7C%20YAK%20Pro-purple.svg)](https://github.com/0xLLVEL/decode-anything)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

An advanced, reverse-engineering toolkit and unified multi-engine decompiler for protected and obfuscated PHP applications. It seamlessly handles **IonCube (static for PHP 8.1 – 8.4, static through the 7.2 record layer, static opcodes for 7.4 encoder 15.x, runtime-assisted for the remaining 7.x IR)**, **SourceGuardian (ixed)**, and **YAK Pro (Control Flow Flattening & Goto Obfuscation)**, reconstructing clean, valid, and PSR-12 idiomatic PHP source code.

---

## 📖 Overview

Modern PHP applications often combine binary byte-code encoders with static control-flow obfuscators:
- **IonCube (PHP 8.1+)**: Encrypted envelopes with XOR-scrambled opcodes, randomized dispatch lanes, and interned string pools referencing dynamic loader DLL symbol tables.
- **IonCube (PHP 7.x)**: The loader materializes `zend_op_array` structures at request time. For 7.2 that layer is no longer opaque to us — the `sv5` container, the record walker, the opcode mask and the file-level record cipher are all reversed, and the record key is derived from the header, so every `op_array` in the file decodes without executing it. For 7.4 the same holds for encoder 15.x payloads: the body is a length-prefixed name followed by a fixed field block, each record carries its own 16-bit seed pair in a stub ahead of the op block, and the whole opcode stream comes out byte-exact (**112/112 `op_array`s and 6,061/6,061 opcodes** against the 7.4 runtime dump). Shipping those records through `decompile.py` still uses the loader (see [ionCube 7.x](#5--ioncube-php-7x)).
- **SourceGuardian (ixed)**: Multi-layer encrypted containers (Blowfish-CBC + ROL1 checksum + LZO1X compression) wrapping custom serialized Zend bytecode structures without requiring runtime execution.
- **YAK Pro (Yakpro-Po)**: Aggressive control flow flattening (CFF), state machine trampolines, spaghetti `goto` chains, and hex/octal string scrambling that break standard static analysis and decompilation tools.

### The Solution: `Decode-Anything`
`Decode-Anything` unifies all three engines into an intelligent, auto-detecting pipeline:
1. **IonCube Decompiler Engine**: Full static unpacking of `HR+c` headers, interned string resolution via loader DLL tables, and high-level AST reconstruction (closures, match, try/catch/finally).
2. **SourceGuardian Engine**: Static Blowfish-CBC and LZO1X container unpacking, bytecode IR deserialization, and direct emission into unified `icdump-ir-v1`.
3. **YAK Pro Static Deobfuscator**: Full Control Flow Graph (CFG) restructuring that converts spaghetti `goto` networks into clean `while`, `for`, `if/else`, and `switch` blocks, unmasks escaped octal/hex string literals, and eliminates residual trampolines with 100% PHP syntax pass rate (`php -l`).
4. **Integrated Quality Gate & Post-Processor**: Automatic PSR-12 `use` import cleanup, guard clause lifting, and atomic output verification.

---

## 🛠️ Architecture & Pipeline

```text
                        [ Protected PHP File / Project ]
                                       │
                                       ▼
                       ┌───────────────────────────────┐
                       │  detector/signatures.py       │ ──> Auto-detect encoder signature
                       └───────────────────────────────┘
                                       │
         ┌─────────────────────────────┼─────────────────────────────┐
         ▼                             ▼                             ▼
┌──────────────────┐          ┌──────────────────┐          ┌──────────────────┐
│  IonCube Engine  │          │  SourceGuardian  │          │  YAK Pro Engine  │
│  (PHP 8.1 - 8.4) │          │  (ixed / sg11+)  │          │  (CFG & Goto)    │
└──────────────────┘          └──────────────────┘          └──────────────────┘
         │                             │                             │
  Extract payload &             Blowfish-CBC decrypt          AST & Lexer parser,
  resolve interned              + LZO1X decompress            Hex/octal de-escaping,
  strings from DLLs             into body.bin                 CFG block restructuring
         │                             │                             │
         ▼                             ▼                             ▼
┌────────────────────────────────────────────────┐          ┌──────────────────┐
│            Unified icdump-ir-v1                │          │ Structured Loops │
└────────────────────────────────────────────────┘          │ & Clean Branches │
         │                                                           │
         ▼                                                           │
┌────────────────────────────────────────────────┐                   │
│      ioncube-php8-decompiler (AST Engine)      │                   │
│  Control flow, closures, expressions, emitter  │                   │
└────────────────────────────────────────────────┘                   │
         │                                                           │
         └─────────────────────────────┬─────────────────────────────┘
                                       │
                                       ▼
                       ┌───────────────────────────────┐
                       │   decompile.py Post-Processor │ ──> PSR-12 imports, syntax check
                       │   Atomic verification (php -l)│
                       └───────────────────────────────┘
                                       │
                                       ▼
                       [ Clean, Valid PHP Source Code ]
```

---

## 🚀 Getting Started

### Prerequisites

- **Python**: 3.10 or newer
- **PHP CLI**: `php` available in your system `PATH` (used for automated `php -l` syntax validation)
- **Python Dependencies**:
  ```bash
  pip install pefile pytest
  ```
- **PHP 7.x runtime bundles** (only for ionCube 7.1 – 7.4 inputs through `decompile.py`): point `IONCUBE_OPCODEDUMP_HOME` at a directory holding the `ic72dump-opcodes` / `ic74dump-opcodes` checkouts, or keep them under `loader/opcodedump` or `loader/refs`. The 8.1 – 8.4 static path and the 7.2 / 7.4 static record tools need nothing beyond Python.

### Quick Usage

#### Decompile a Single File
Works out-of-the-box on **IonCube**, **SourceGuardian**, or **YAK Pro** files:
```bash
python decompile.py path/to/encoded_file.php
```
*Output will be saved alongside the original as `path/to/encoded_file.reconstructed.php`.*

Specify custom output:
```bash
python decompile.py path/to/encoded_file.php -o output/decoded.php
```

Pin the target ABI explicitly (otherwise it is inferred from the ionCube header):
```bash
python decompile.py path/to/encoded_file.php --php-version 72
```

#### Inspect a PHP 7.2 Payload Statically
No runtime and no key material: the container, the record walker, the opcode mask and the record cipher all run in Python.
```bash
# container report (chunking, checksums, MD4, header trailer) + the program blob
python tools/ic72_static_container.py path/to/encoded_file.php --body-out body72.bin

# whole body: every op_array, opcodes decoded from the record keys
python tools/ic72_static_dump.py body72.bin --php path/to/encoded_file.php

# just the file-level record, with the key derived from the header
python tools/ic72_record0.py path/to/encoded_file.php
```

#### Inspect a PHP 7.4 Payload Statically
Same deal for 7.4 encoder 15.x artifacts: container gates, field block, argument records, per-record seed stubs and the masked opcode stream, all in Python.
```bash
# container + field block fingerprint per op_array
python tools/ic74_static_dump.py path/to/encoded_file.php

# full opcode streams, diffed byte for byte against a runtime dump
python tools/ic74_static_dump.py loader/refs/ic74dump-opcodes/contacts.php \
    --opcodes --truth loader/refs/ic74dump-opcodes/contacts.opcodes.json
# encoder 15.0.1 / PHP 7.4: entry_count 112, opcodes_decoded 112,
# opcode_total 6061, matched 112, opcode streams 112/112

# the same layer as icdump-ir-v1 JSON (records, lines, opcodes, class index)
python tools/ic74_static_ir.py loader/refs/ic74dump-opcodes/contacts.php \
    --truth loader/refs/ic74dump-opcodes/contacts.opcodes.json -o out.icdump.json
# op_arrays 112, opcode_total 6061, opcode streams 112/112, line ranges 112/112
```

That IR document is the file's *structure*: one entry per `op_array` with its
class, name, line range and opcode stream. Operand values are not in the body,
so every instruction goes in with `IS_UNUSED` - `decompile.py` therefore keeps
using the runtime dump for 7.4 rather than emitting a skeleton that only looks
decompiled. See [`docs/ioncube-74-static.md`](docs/ioncube-74-static.md#the-ir-bridge-and-the-one-table-it-still-needs).

#### Batch Decompile an Entire Directory
Recursively decodes all protected files and mirrors non-protected assets:
```bash
python decompile.py path/to/encoded_dir/ -o output/decoded_dir/
```

Fast scan (skip copying non-protected assets):
```bash
python decompile.py path/to/encoded_dir/ -o output/decoded_dir/ --no-copy-other
```

In-place deobfuscation with automatic `.bak` backups:
```bash
python decompile.py path/to/project_dir/ --in-place
```

---

## 🔍 Project Scanner & Auto-Decompiler

Audit an entire codebase or vendor directory to discover encoded or obfuscated files:

```bash
python decompile.py scan path/to/project/
```

Supported encoder detections:
- **ionCube**: Detects bytecode headers (`HR+c`) and loader bootstrap wrappers across PHP 8.1–8.4, plus the PHP 7.x loader-bootstrap files routed to the runtime-assisted path.
- **SourceGuardian**: Detects `sg_load(` loader calls and binary headers.
- **YAK Pro**: Detects control flow flattening, goto trampolines, and scrambled identifier tables.
- **Zend Guard**: Detects Zend Guard Engine wrappers and binary headers.
- **PHP Bolt**: Detects `bolt_encrypt` / `boltr_` runtime hooks.

#### Scan and Auto-Decompile
Automatically scan a project and decompile all discovered files:
```bash
python decompile.py scan path/to/project/ -d -o output/decoded_project/
```

#### JSON Output (for CI/CD pipelines)
```bash
python decompile.py scan path/to/project/ --json
```

---

## 🧪 Testing & Validation

The test suite covers IonCube AST reconstruction, SourceGuardian container decoding, LZO1X decompression, and YAK Pro CFG restructuring:

```bash
python -m pytest tests/
```

All 214 test cases pass:
```text
============================= 214 passed in 23.22s ==============================
```

---

## 📂 Repository Structure

- [`decompile.py`](decompile.py) — Unified CLI entry point for scanning, single-file, and directory batch decompilation.
- [`detector/`](detector/) — Multi-encoder signature scanner and format analyzer.
- [`engines/`](engines/) — Core decompiler and deobfuscator engines:
  - [`engines/ioncube/`](engines/ioncube/) — Static IonCube PHP 8.1–8.4 opcode dumper, header parser, and loader symbol resolver (`header.py`, `body.py`, `dumper.py`, `adapter.py`), the reversed 7.x primitives (`body72.py`: record cipher, key derivation, PRNG 6), plus the runtime-assisted PHP 7.x path and its AES-256 port (`runtime_dump.py`, `rijndael.py`).
  - [`engines/sourceguardian/`](engines/sourceguardian/) — Static SourceGuardian envelope decryptor, LZO1X inflator, and bytecode IR parser (`container.py`, `bytecode_ir.py`, `lzo1x.py`).
  - [`engines/yakpro/`](engines/yakpro/) — YAK Pro control-flow graph (CFG) restructurer, goto-eliminator, and string de-escaper (`deobfuscator.py`).
- [`tools/`](tools/) — Reverse-engineering utilities: loader extractor, base64 blob decoder, the static 7.2 pipeline (`ic72_static_container.py`, `ic72_record_walk.py`, `ic72_op_walk.py`, `ic72_opcode_mask.py`, `ic72_record0.py`, `ic72_static_dump.py`), the static 7.4 path (`ic74_static_dump.py`, `ic74_mask.py`, `ic74_static_ir.py`, `ic74_rea.py`), and the runtime 7.x debugger probes (`ic72_record_guard.py`, `ic72_blob_watch.py`, `ic72_cipher_trace.py`, `ic72_keystream.py`, `ic72_memdump.py`).
  - [`tools/opcodedump/`](tools/opcodedump/) — C source of `php_opcodedump.dll`, the PHP 7.2 extension that decodes the loader's in-memory op arrays; `build.bat` rebuilds it against the runtime bundle's 7.2 headers (see [`docs/ioncube-72-static.md`](docs/ioncube-72-static.md#rebuilding-the-opcode-dumper-php_opcodedumpdll)).
- [`docs/`](docs/) — Loader analysis notes: [`ioncube-72-static.md`](docs/ioncube-72-static.md) for the 7.2 static decode map, [`ioncube-74-static.md`](docs/ioncube-74-static.md) for the 7.4 field block, seed stubs and opcode walk, [`rea-ida.md`](docs/rea-ida.md) for the REA/IDA workflow.
- [`ioncube-php8-decompiler/`](ioncube-php8-decompiler/) — High-level PHP abstract syntax tree (AST) engine:
  - `src/php_reconstructor/decompiler/` — Opcode handlers, CFG structurer, and optimization passes.
  - `src/php_reconstructor/emitter/` — High-fidelity PHP code emitter.
- [`tests/`](tests/) — Automated test suite (214 tests).

---

## 🗺️ Roadmap

`Decode-Anything` is engineered to be the definitive reverse-engineering and deobfuscation suite for protected PHP applications.

### 1. 🛡️ SourceGuardian (ixed) Decoder
- [x] Envelope decryption and payload extraction for SourceGuardian containers (Blowfish-CBC + ROL1 + LZO1X).
- [x] Static Zend bytecode disassembler and container parser (`engines/sourceguardian/bytecode_ir.py`).
- [x] Direct bridge to unified `icdump-ir-v1` format.
- [ ] Expand opcode dictionary coverage for legacy PHP 7.0–7.4 and PHP 8.2–8.4 ixed variants.

### 2. 🌀 YAK Pro & AST Obfuscator De-flattener
- [x] Static string literal de-obfuscation (hex `\xHH` and octal `\OOO` decoding with brace-safety).
- [x] Control Flow Flattening (CFF) unflattening via basic block CFG reconstruction.
- [x] Elimination of spaghetti `goto` statements into structured `while`, `for`, and `if/else` control flow.
- [x] Zero-residual goto assurance with 100% PHP syntax pass rate (`php -l`).
- [ ] Semantic identifier normalization (heuristic mapping of scrambled `$v_xxx` variables and functions).

### 3. 🧩 Unified Multi-Format CLI Engine
- [x] Auto-detection pipeline: automatically route files to IonCube, SourceGuardian, or YAK Pro decoders.
- [x] Batch directory processing with in-place overwrite and atomic backup protections (`.bak`).
- [x] Fast scanning `--no-copy-other` mode.
- [ ] Interactive side-by-side terminal / HTML inspection view for original vs reconstructed code.

### 4. ⚡ PHP Bolt Decryptor
- [ ] Static decryption key extraction from loader binary and configuration.
- [ ] Decryption of bytecode wrappers (`bolt_encrypt` / `boltr_`).
- [ ] Restoration of native PHP source files from decrypted payloads.

### 5. 🔐 ionCube PHP 7.x
- [x] Runtime-assisted decode for 7.1 – 7.4: the real loader builds each `zend_op_array`, an in-process dumper walks it, and the result is converted into the shared `icdump-ir-v1` IR (`engines/ioncube/runtime_dump.py`). This remains the shipping path for `decompile.py` on every 7.x input.
- [x] `--php-version` ABI pinning with header autodetection, and batch/scan support for the 7.x path.
- [x] Static recovery of the 7.2 text layer: the record parser at `0x6C340` hands `HR+c` payloads to `sub_10065D50`, whose reverse table at `0x10093BC0` decodes the base64 body byte-exactly (9,699 bytes, record magic `0x67A6BF45`).
- [x] 7.2 header and body verified statically: chunked envelope, `MT4IC` PRNG, MD4 trailer, and both body checksums match.
- [x] Static 7.2 `sv5` record walker and opcode decoder: the opcode mask is reproduced from each record's key pair (397/397 opcodes equal the runtime dump), and the file-level record cipher (`sub_180001E10`) plus its 17-byte key (`sub_180003570`) are reversed, so all five `op_array`s now decode from the file alone.
- [x] Derive the four program key words without a runtime: the loader copies the header size, the record count, `0`, and the trailer's `evaluation_min_raw` licence dword into the context, so the file-level record now decrypts from the file alone. See [`docs/ioncube-72-static.md`](docs/ioncube-72-static.md) (M4.13).
- [x] Static 7.2 output is verifiable end to end: `python tools/ic72_record0.py sample.php` prints the file-level record with no key input, and `python tools/ic72_static_dump.py body72.bin --php sample.php` decodes all 408 slots (397 function + 11 file-level) with zero unknowns.
- [ ] Feed the static 7.2 walker into `runtime_dump.to_icdump()` so `decompile.py --php-version 72` emits IR without spawning the loader — the buffer, records, mask and key are all in place; only the IR bridge is missing.
- [x] Static 7.4 decode, no runtime: container gates, the field block fingerprint, the argument-record walk to the op block, the per-record seed stub and the masked opcode stream all run in `tools/ic74_static_dump.py`. Against `loader/refs/ic74dump-opcodes/contacts.opcodes.json` it comes out **112/112 `op_array`s, 112/112 opcode streams, 6,061/6,061 opcodes byte-equal, 27 `0x95` escapes** — no loader DLL, no PHP process. See [`docs/ioncube-74-static.md`](docs/ioncube-74-static.md).
- [x] Static 7.4 body bridged into `icdump-ir-v1` (`engines/ioncube/static74.py`, `tools/ic74_static_ir.py`): every record, line range, opcode byte and class/method id lands in the shared IR — 112/112 opcode streams and 112/112 line ranges against the runtime dump, with no PHP process.
- [ ] Operand values for 7.4: the instruction word block carries opcode, line, cache slot and a presence nibble only, so `decompile.py` still routes 7.4 through the runtime dump. Reading the operand table is the one step between the static IR and runtime-free decompilation.
- [ ] Older 7.4 encoders (13.0.x, as shipped by third-party repackagers) lay the body out differently — a symbol table up front and no `0x42020001` record marks — so those files still go through the runtime path.
- [ ] Repeat the static record layer for 7.1 and 7.3 loaders (the 7.3 DLL is already in [`loader/`](loader/), analysis not started).

### 6. 🔒 Zend Guard Decompiler
- [ ] Support for legacy Zend Guard protected archives (`Zend\x00` format).
- [ ] Extraction of compiled Zend VM bytecode instructions.
- [ ] Symbol reconstruction and variable recovery.

---

## 🙏 Acknowledgments & Credits

This project builds upon foundational reverse-engineering research by **dawwinci** (Andrei Amariei):
- **Research**: [*Static decoding of IonCube PHP 8.x payloads*](https://www.amariei.org/ioncube-php8-static-decode.html) & [*SourceGuardian PHP 8.1 Static Decode*](https://www.amariei.org/sourceguardian-php81-static-decode.html)
- **Base Repository**: [`dawwinci/ioncube-php8-decompiler`](https://github.com/dawwinci/ioncube-php8-decompiler)

---

## ⚖️ Disclaimer & License

This tool is created for security research, software interoperability, educational analysis, and recovery of lost source code. Ensure you have the legal right or explicit permission to reverse-engineer any binaries you analyze.

Distributed under the [MIT License](LICENSE).

