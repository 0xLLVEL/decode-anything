# Decode-Anything: Unified PHP Decompiler & Deobfuscator

[![Python Tests](https://img.shields.io/badge/tests-199%20passed-brightgreen.svg)](tests/)
[![Target PHP](https://img.shields.io/badge/PHP-7.2%20%E2%80%93%208.4-blue.svg)](https://php.net)
[![Supported](https://img.shields.io/badge/Encoders-ionCube%20%7C%20SourceGuardian%20%7C%20YAK%20Pro-purple.svg)](https://github.com/0xLLVEL/decode-anything)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

An advanced, reverse-engineering toolkit and unified multi-engine decompiler for protected and obfuscated PHP applications. It seamlessly handles **IonCube (static for PHP 8.1 – 8.4, runtime-assisted for 7.x)**, **SourceGuardian (ixed)**, and **YAK Pro (Control Flow Flattening & Goto Obfuscation)**, reconstructing clean, valid, and PSR-12 idiomatic PHP source code.

---

## 📖 Overview

Modern PHP applications often combine binary byte-code encoders with static control-flow obfuscators:
- **IonCube (PHP 8.1+)**: Encrypted envelopes with XOR-scrambled opcodes, randomized dispatch lanes, and interned string pools referencing dynamic loader DLL symbol tables.
- **IonCube (PHP 7.x)**: The loader materializes `zend_op_array` structures at request time and keeps the opcode stream XOR-encoded in memory keyed by the request timestamp, so the body blob cannot be replayed statically. Those builds are decoded through the loader itself (see [runtime-assisted 7.x](#5--ioncube-php-7x-runtime-assisted)).
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
- **PHP 7.x runtime bundles** (only for ionCube 7.1 – 7.4 inputs): point `IONCUBE_OPCODEDUMP_HOME` at a directory holding the `ic72dump-opcodes` / `ic74dump-opcodes` checkouts, or keep them under `loader/opcodedump` or `scratch/refs`. The 8.1 – 8.4 static path needs nothing beyond Python.

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

All 199 test cases pass:
```text
============================= 199 passed in 8.11s ==============================
```

---

## 📂 Repository Structure

- [`decompile.py`](decompile.py) — Unified CLI entry point for scanning, single-file, and directory batch decompilation.
- [`detector/`](detector/) — Multi-encoder signature scanner and format analyzer.
- [`engines/`](engines/) — Core decompiler and deobfuscator engines:
  - [`engines/ioncube/`](engines/ioncube/) — Static IonCube PHP 8.1–8.4 opcode dumper, header parser, and loader symbol resolver (`header.py`, `body.py`, `dumper.py`, `adapter.py`), plus the runtime-assisted PHP 7.x path and its AES-256 port (`runtime_dump.py`, `rijndael.py`).
  - [`engines/sourceguardian/`](engines/sourceguardian/) — Static SourceGuardian envelope decryptor, LZO1X inflator, and bytecode IR parser (`container.py`, `bytecode_ir.py`, `lzo1x.py`).
  - [`engines/yakpro/`](engines/yakpro/) — YAK Pro control-flow graph (CFG) restructurer, goto-eliminator, and string de-escaper (`deobfuscator.py`).
- [`tools/`](tools/) — Reverse-engineering utilities: loader extractor, base64 blob decoder, and the 7.x debugger probes (`ic72_record_guard.py`, `ic72_blob_watch.py`, `ic72_cipher_trace.py`, `ic72_keystream.py`, `ic72_memdump.py`).
- [`docs/`](docs/) — Loader analysis notes: [`ioncube-72-static.md`](docs/ioncube-72-static.md) for the 7.2 static decode map, [`rea-ida.md`](docs/rea-ida.md) for the REA/IDA workflow.
- [`ioncube-php8-decompiler/`](ioncube-php8-decompiler/) — High-level PHP abstract syntax tree (AST) engine:
  - `src/php_reconstructor/decompiler/` — Opcode handlers, CFG structurer, and optimization passes.
  - `src/php_reconstructor/emitter/` — High-fidelity PHP code emitter.
- [`tests/`](tests/) — Automated test suite (199 tests).

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

### 5. 🔐 ionCube PHP 7.x (runtime-assisted)
- [x] Runtime-assisted decode for 7.1 – 7.4: the real loader builds each `zend_op_array`, an in-process dumper walks it, and the result is converted into the shared `icdump-ir-v1` IR (`engines/ioncube/runtime_dump.py`).
- [x] `--php-version` ABI pinning with header autodetection, and batch/scan support for the 7.x path.
- [x] Static recovery of the 7.2 text layer: the record parser at `0x6C340` hands `HR+c` payloads to `sub_10065D50`, whose reverse table at `0x10093BC0` decodes the base64 body byte-exactly (9,699 bytes, record magic `0x67A6BF45`).
- [x] 7.2 header and body verified statically: chunked envelope, `MT4IC` PRNG, MD4 trailer, and both body checksums match.
- [x] Static 7.2 `sv5` record walker and opcode decoder: the opcode mask is reproduced from each record's key pair (397/397 opcodes equal the runtime dump), and the file-level record cipher (`sub_180001E10`) plus its 16-byte key (`sub_180003570`) are reversed, so all five `op_array`s now decode from the file alone.
- [ ] Derive the four program key words (`0xB8`, record count, `0`, a per-file hash) without a runtime, so the file-level record needs no supplied key — the last step before the PHP runtime can be dropped for 7.x.

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

