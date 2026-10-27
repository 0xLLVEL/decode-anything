# Decode-Anything: IonCube PHP 8.1 – 8.4 Decompiler & Reconstructor

[![Python Tests](https://img.shields.io/badge/tests-85%20passed-brightgreen.svg)](tests/)
[![Target PHP](https://img.shields.io/badge/PHP-8.1%20%7C%208.2%20%7C%208.3%20%7C%208.4-blue.svg)](https://php.net)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

An advanced, reverse-engineering toolkit and unified decompiler for **IonCube-protected PHP 8.1, 8.2, 8.3, and 8.4** files. It extracts Zend VM bytecode directly from IonCube encrypted envelopes, resolves obfuscated interned strings and opcode handler lanes, and reconstructs clean, valid, PSR-12 idiomatic PHP source code.

---

## 📖 Overview

### The Problem
IonCube encoding on modern PHP (8.1+) underwent significant architectural changes:
- Opcodes are obfuscated using multi-round XOR streams tied to dynamic serialization keys.
- Instruction dispatch lanes are randomized across loader variants.
- Constant pool literals and internal PHP function names (such as `header`, `implode`, `count`, `date`, `fopen`) are replaced by interned indices referencing private runtime tables.
- Nested closures and lexical `use ($var)` bindings are packed into serialized sub-blobs with bit-masked length headers.

Most legacy decompilers fail completely on PHP 8.1+ files, producing broken stubs, empty closures, undefined jumps (`goto`), or invalid PHP parse errors.

### The Solution: `Decode-Anything`
`Decode-Anything` provides an end-to-end decompilation and AST reconstruction pipeline:
1. **Low-Level Header & Payload Parser**: Decodes `HR+c` headers, uncompresses the raw zend payloads, and extracts method/class records.
2. **PE-Loader Interned-String Resolver**: Employs loader DLL symbol tables to decrypt interned string tables into original identifiers.
3. **Structured AST Decompiler**: Reconstructs high-level control structures (if/else, switch, match, loops, try/catch/finally).
4. **Closure & Lambda Restorer**: Traverses nested opcode trees and rebuilds inline anonymous functions with lexical bindings.
5. **PSR-12 Auto-Import Post-Processor**: Converts raw Fully Qualified Class Names (FQCN) into clean, grouped `use` imports at the top of reconstructed files.
6. **Integrated Syntax Checker**: Automatically validates all generated output against `php -l`.

---

## 🛠️ Architecture & Pipeline

```text
[ Encoded PHP File ]
        │
        ▼
┌──────────────────────────────────────────────┐
│ decode_hrc_header.py & decode_php_body.py     │  ──> Extract payload, decrypt outer envelope
└──────────────────────────────────────────────┘
        │
        ▼
┌──────────────────────────────────────────────┐
│ dump_plain_file_static.py                    │  ──> Disassemble Zend VM opcodes,
│ + ioncube_loader_win_8.x.dll (via pefile)    │      resolve interned strings & handler lanes
└──────────────────────────────────────────────┘
        │
        ▼
┌──────────────────────────────────────────────┐
│ loader_static_to_icdump_ir.py                │  ──> Normalize to unified icdump-ir-v1
└──────────────────────────────────────────────┘
        │
        ▼
┌──────────────────────────────────────────────┐
│ ioncube-php8-decompiler (AST Engine)         │  ──> Reconstruct expressions, closures,
│   - structurer.py, handlers/, php_emitter.py │      control flow, and try/catch blocks
└──────────────────────────────────────────────┘
        │
        ▼
┌──────────────────────────────────────────────┐
│ decompile.py (Post-processor)                │  ──> PSR-12 `use` imports, clean AST anomalies,
│                                              │      validate with `php -l`
└──────────────────────────────────────────────┘
        │
        ▼
[ Clean, Valid PHP Source Code ]
```

---

## 🚀 Getting Started

### Prerequisites

- **Python**: 3.10 or newer
- **PHP CLI**: `php` available in your system `PATH` (used for automatic syntax verification)
- **Python Dependencies**:
  ```bash
  pip install pefile pytest
  ```

### Quick Usage

#### Decompile a Single File
```bash
python decompile.py path/to/encoded_file.php
```
*Output will be saved alongside the original as `path/to/encoded_file.reconstructed.php`.*

Specify a custom output path:
```bash
python decompile.py path/to/encoded_file.php -o output/decoded.php
```

#### Batch Decompile an Entire Directory
```bash
python decompile.py path/to/encoded_dir/ -o output/decoded_dir/
```

#### Target Specific PHP Versions
By default, the target PHP version is auto-detected from the file header (e.g. 81, 82, 83, 84). You can override it manually:
```bash
python decompile.py sample.php --php-version 83
```

---

## 🧪 Testing & Validation

The core AST reconstructor includes a comprehensive unit test suite covering complex PHP 8 expressions, nested control flow, variable-variables (`$$var`, `${...}`), and closure bindings:

```bash
python -m pytest ioncube-php8-decompiler/tests/
```

All 85+ test cases pass:
```text
============================== 85 passed in 0.10s ==============================
```

---

## 📂 Repository Structure

- [`decompile.py`](decompile.py) — Unified CLI entry point for single-file and directory batch decompilation.
- [`dump_plain_file_static.py`](dump_plain_file_static.py) — Core static opcode dumper and loader table decipherer.
- [`decode_php_body.py`](decode_php_body.py) — Low-level Zend record deserializer and dynamic cipher0/basic decryptor.
- [`decode_hrc_header.py`](decode_hrc_header.py) — Parser for IonCube file headers, body slices, and payload offsets.
- [`loader_static_to_icdump_ir.py`](loader_static_to_icdump_ir.py) — Intermediate Representation (IR) adapter.
- [`ioncube-php8-decompiler/`](ioncube-php8-decompiler/) — High-level PHP abstract syntax tree (AST) engine:
  - `src/php_reconstructor/decompiler/` — Opcode handlers, control-flow structurer, and optimization passes.
  - `src/php_reconstructor/emitter/` — High-fidelity PHP code emitter.
  - `tests/` — Automated test suite.

---

## 🙏 Acknowledgments & Credits

This project is built upon the foundational reverse-engineering research and core architecture pioneered by **dawwinci** (Andrei Amariei):
- **Research Article**: [*Static decoding of IonCube PHP 8.x payloads*](https://www.amariei.org/ioncube-php8-static-decode.html)
- **Base Repository**: [`dawwinci/ioncube-php8-decompiler`](https://github.com/dawwinci/ioncube-php8-decompiler)

Immense gratitude to their ground-breaking research in dissecting IonCube's modern loader architecture, opcode XOR mechanics, and AST reconstruction patterns.

---

## ⚖️ Disclaimer & License

This tool is created for security research, software interoperability, educational analysis, and recovery of lost source code. Ensure you have the legal right or explicit permission to reverse-engineer any binaries you analyze.

Distributed under the [MIT License](LICENSE).

