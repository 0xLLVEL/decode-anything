# Decode-Anything: Unified PHP Decompiler & Deobfuscator

[![Python Tests](https://img.shields.io/badge/tests-98%20passed-brightgreen.svg)](tests/)
[![Target PHP](https://img.shields.io/badge/PHP-8.1%20%7C%208.2%20%7C%208.3%20%7C%208.4-blue.svg)](https://php.net)
[![Supported](https://img.shields.io/badge/Encoders-ionCube%20%7C%20SourceGuardian%20%7C%20YAK%20Pro-purple.svg)](https://github.com/0xLLVEL/decode-anything)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

An advanced, reverse-engineering toolkit and unified multi-engine decompiler for protected and obfuscated PHP applications. It seamlessly handles **IonCube (PHP 8.1 – 8.4)**, **SourceGuardian (ixed)**, and **YAK Pro (Control Flow Flattening & Goto Obfuscation)**, reconstructing clean, valid, and PSR-12 idiomatic PHP source code.

---

## 📖 Overview

Modern PHP applications often combine binary byte-code encoders with static control-flow obfuscators:
- **IonCube (PHP 8.1+)**: Encrypted envelopes with XOR-scrambled opcodes, randomized dispatch lanes, and interned string pools referencing dynamic loader DLL symbol tables.
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
- **ionCube**: Detects bytecode headers (`HR+c`) and loader bootstrap wrappers across PHP 8.1–8.4.
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

All 98 test cases pass:
```text
============================= 98 passed in 8.01s =============================
```

---

## 📂 Repository Structure

- [`decompile.py`](decompile.py) — Unified CLI entry point for scanning, single-file, and directory batch decompilation.
- [`detector/`](detector/) — Multi-encoder signature scanner and format analyzer.
- [`yakpro_deobfuscator.py`](yakpro_deobfuscator.py) — YAK Pro control-flow graph (CFG) restructurer, goto-remover, and string de-escaper.
- [`sg_container_decode.py`](sg_container_decode.py) — SourceGuardian Blowfish-CBC & ROL1 envelope decryptor.
- [`sg_lzo1x.py`](sg_lzo1x.py) — Standalone pure-Python LZO1X decompressor matching SourceGuardian loader specifications.
- [`sg_bytecode_ir.py`](sg_bytecode_ir.py) — SourceGuardian body bytecode parser and adapter to `icdump-ir-v1`.
- [`dump_plain_file_static.py`](dump_plain_file_static.py) — Static IonCube opcode dumper and interned-string decipherer.
- [`decode_php_body.py`](decode_php_body.py) — Low-level Zend record deserializer and dynamic cipher0 decryptor.
- [`decode_hrc_header.py`](decode_hrc_header.py) — Parser for IonCube file headers and payload offsets.
- [`ioncube-php8-decompiler/`](ioncube-php8-decompiler/) — High-level PHP abstract syntax tree (AST) engine:
  - `src/php_reconstructor/decompiler/` — Opcode handlers, CFG structurer, and optimization passes.
  - `src/php_reconstructor/emitter/` — High-fidelity PHP code emitter.
- [`tests/`](tests/) — Automated test suite (98 tests).

---

## 🗺️ Roadmap

`Decode-Anything` is engineered to be the definitive reverse-engineering and deobfuscation suite for protected PHP applications.

### 1. 🛡️ SourceGuardian (ixed) Decoder
- [x] Envelope decryption and payload extraction for SourceGuardian containers (Blowfish-CBC + ROL1 + LZO1X).
- [x] Static Zend bytecode disassembler and container parser (`sg_bytecode_ir.py`).
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

### 5. 🔒 Zend Guard Decompiler
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

