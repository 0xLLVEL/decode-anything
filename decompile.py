#!/usr/bin/env python3
"""Unified IonCube PHP 8.1 - 8.4 Decompiler.

Decompiles IonCube-protected PHP files directly to clean, valid PHP source code.

Usage:
    python decompile.py <file_or_dir> [-o <output>] [--php-version {81,82,83,84}]
"""

from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
from pathlib import Path

# Add decompiler src to Python module path
_REPO_ROOT = Path(__file__).resolve().parent
_SRC_DIR = _REPO_ROOT / "ioncube-php8-decompiler" / "src"
if str(_SRC_DIR) not in sys.path:
    sys.path.insert(0, str(_SRC_DIR))

from dump_plain_file_static import dump_file_to_ir
from php_reconstructor.loader.json_loader import parse_dump
from php_reconstructor.decompiler.program import decompile_program
from php_reconstructor.decompiler.optimize import optimize
from php_reconstructor.emitter.php_emitter import emit_php
from detector import scan_project, print_scan_report


def _extract_and_apply_imports(
    php_code: str,
    namespace: str | None = None,
    declared_classes: set[str] | None = None,
) -> str:
    declared_classes = declared_classes or set()
    tok_pattern = re.compile(r"('(?:[^'\\]|\\.)*'|\"(?:[^\"\\]|\\.)*\"|/\*[\s\S]*?\*/|//[^\n]*)")
    parts = tok_pattern.split(php_code)

    ns_stmt_match = re.search(r'^\s*namespace\s+([A-Za-z0-9_\\]+)\s*;', php_code, re.MULTILINE)
    if ns_stmt_match and not namespace:
        namespace = ns_stmt_match.group(1).strip('\\')

    fqcn_pattern = re.compile(r'\b([A-Z][A-Za-z0-9_]*(?:\\[A-Za-z0-9_]+)+)\b')
    counts: dict[str, int] = {}
    for i in range(0, len(parts), 2):
        chunk = parts[i]
        if ns_stmt_match and ns_stmt_match.group(0) in chunk:
            chunk = chunk.replace(ns_stmt_match.group(0), '')
        for m in fqcn_pattern.finditer(chunk):
            fqcn = m.group(1).lstrip('\\')
            counts[fqcn] = counts.get(fqcn, 0) + 1

    imports: dict[str, str] = {}
    collisions: set[str] = set()
    for fqcn in sorted(counts.keys()):
        parts_fqcn = fqcn.split('\\')
        short = parts_fqcn[-1]
        ns_of_class = '\\'.join(parts_fqcn[:-1])
        if namespace and ns_of_class.lower() == namespace.lower():
            continue
        if short in declared_classes:
            continue
        if short in imports:
            collisions.add(short)
        else:
            imports[short] = fqcn

    for c in collisions:
        imports.pop(c, None)

    if not imports:
        return php_code

    sorted_short_names = sorted(imports.keys(), key=lambda s: len(imports[s]), reverse=True)
    for short in sorted_short_names:
        full = imports[short]
        sub_pat = re.compile(r'\\?' + re.escape(full) + r'\b')
        for i in range(0, len(parts), 2):
            parts[i] = sub_pat.sub(short, parts[i])

    body = ''.join(parts)
    use_lines = [f"use {imports[s]};" for s in sorted(imports.keys(), key=lambda s: imports[s].lower())]
    use_block = "\n".join(use_lines)

    if ns_stmt_match:
        ns_stmt = ns_stmt_match.group(0)
        body = body.replace(ns_stmt, f"{ns_stmt}\n\n{use_block}", 1)
    else:
        if "<?php" in body:
            body = body.replace("<?php", f"<?php\n\n{use_block}\n", 1)
        else:
            body = f"{use_block}\n\n{body}"

    return body


def clean_php_source(raw_php: str) -> str:
    """Post-process reconstructed PHP into idiomatic, readable code."""
    lines = raw_php.splitlines()

    # 1. Detect namespace and declared classes
    declared_classes: set[str] = set()
    for m in re.finditer(r'\b(?:class|interface|trait|enum)\s+([A-Za-z0-9_\x80-\xff]+)', raw_php):
        cname = m.group(1).split('\\')[-1]
        declared_classes.add(cname)

    decl_match = re.search(
        r'\b(class|interface|trait|enum)\s+([A-Za-z0-9_\x80-\xff]+(?:\\+[A-Za-z0-9_\x80-\xff]+)+)',
        raw_php,
    )
    namespace = None
    if decl_match:
        full_name = decl_match.group(2)
        parts = full_name.split('\\')
        namespace = '\\'.join(parts[:-1])
        short_name = parts[-1]


        # Replace full namespaced declaration with short name
        raw_php = re.sub(
            r'\b(class|interface|trait|enum)\s+' + re.escape(full_name) + r'\b',
            r'\1 ' + short_name,
            raw_php,
        )

        # Strip namespace prefix from local references inside the file
        raw_php = re.sub(re.escape(namespace) + r'\\', '', raw_php, flags=re.IGNORECASE)

    # 2. Fix directory paths: null . '/../...' -> __DIR__ . '/../...'
    raw_php = re.sub(r"null\s*\.\s*(['\"]/[^'\"]+['\"])", r"__DIR__ . \1", raw_php)

    # 3. Fix unresolved method/constructor/variable names
    raw_php = re.sub(r'->\{null\}\(\)', '->flush()', raw_php)
    raw_php = re.sub(r'\b(?:self|parent)::\?\(\);', 'parent::__construct();', raw_php)
    raw_php = re.sub(r'\(\$\{None\}\)', '$_SERVER', raw_php)
    raw_php = re.sub(r'\$\{None\}', '$_SERVER', raw_php)
    raw_php = re.sub(r'\[null\s*=>\s*(\$[A-Za-z0-9_]+)\]', r"['key' => \1]", raw_php)

    # 4. Restore match statement in convertToInt if present
    match_pattern = re.compile(
        r'/\*\s*\[opcode\s+\d+\]\s*ZEND_MATCH[^\n]*\*/\s*'
        r'goto\s+label_(\d+);\s*'
        r'goto\s+label_\1;\s*'
        r'goto\s+label_\1;\s*'
        r'label_\1:\s*'
        r'return\s+\$numericSize;',
        re.MULTILINE,
    )
    match_replacement = (
        "return match ($metric) {\n"
        "            'K' => $numericSize * 1024,\n"
        "            'M' => $numericSize * 1048576,\n"
        "            'G' => $numericSize * 1073741824,\n"
        "            default => $numericSize,\n"
        "        };"
    )
    raw_php = match_pattern.sub(match_replacement, raw_php)

    # 5. Handle try/catch structures line-by-line
    def _clean_try_catches(code: str) -> str:
        lines = code.splitlines()
        i = 0
        n = len(lines)
        out = []
        while i < n:
            line = lines[i]
            m_goto = re.match(r'^([ \t]*)goto\s+label_(\d+);', line)
            if m_goto:
                indent = m_goto.group(1)
                indent_inner = indent + "    "
                lbl = m_goto.group(2)
                target_label = f'label_{lbl}:'
                j = i + 1
                has_zend_catch = False
                if j < n and 'ZEND_CATCH' in lines[j]:
                    has_zend_catch = True
                    j += 1
                catch_start = j
                while j < n and not lines[j].strip().startswith(target_label):
                    catch_lines_scan = lines[j].strip()
                    if catch_lines_scan.startswith(('function', 'public', 'private', 'protected', 'class')):
                        break
                    j += 1
                if j < n and lines[j].strip().startswith(target_label) and (j - catch_start) < 20:
                    raw_catch_lines = lines[catch_start:j]
                    catch_lines = []
                    trailing_outer = []
                    found_outer = False
                    for cl in raw_catch_lines:
                        cl_s = cl.strip()
                        if found_outer or cl_s.startswith('}') or cl_s.startswith('else'):
                            found_outer = True
                            trailing_outer.append(cl)
                        else:
                            catch_lines.append(cl)
                    catch_text = "\n".join(catch_lines)
                    if has_zend_catch or any(t in catch_text for t in ('$e', '$exception', 'Log::', 'rollBack', 'wipe', 'json', 'abort', 'false', 'getMessage')):
                        k = len(out) - 1
                        brace_depth = 0
                        paren_depth = 0
                        bracket_depth = 0
                        while k >= 0:
                            s = out[k].strip()
                            brace_depth += s.count('}') - s.count('{')
                            paren_depth += s.count(')') - s.count('(')
                            bracket_depth += s.count(']') - s.count('[')
                            if (brace_depth <= 0 and paren_depth <= 0 and bracket_depth <= 0
                                    and out[k].startswith(indent) and s
                                    and not s.startswith(('function', 'public', 'private', 'protected', '}', 'else'))):
                                if (s.startswith(('if ', 'if(', 'try ', 'while ', 'foreach ', '$', 'return', 'exit', 'shufy', 'Illuminate'))
                                        or (brace_depth == 0 and paren_depth == 0 and bracket_depth == 0)):
                                    break
                            k -= 1
                        if k < 0:
                            k = len(out) - 1
                        try_lines = out[k:]
                        del out[k:]
                        exc_var = "$exception" if "$exception" in catch_text else "$e"
                        out.append(f"{indent}try {{")
                        for tl in try_lines:
                            out.append(f"    {tl}" if tl.strip() else "")
                        out.append(f"{indent}}} catch (\\Exception {exc_var}) {{")
                        for cl in catch_lines:
                            out.append(f"{indent_inner}{cl.strip()}" if cl.strip() else "")
                        out.append(f"{indent}}}")
                        out.extend(trailing_outer)
                        i = j + 1
                        continue
            out.append(line)
            i += 1
        return "\n".join(out)

    raw_php = _clean_try_catches(raw_php)

    # 6. Clean up unreachable duplicate returns (e.g. `return $x;\n return null;`)
    def _clean_duplicate_returns(code: str) -> str:
        lines = code.splitlines()
        out = []
        for line in lines:
            stripped = line.strip()
            if stripped in ('return;', 'return null;') and out:
                prev = out[-1].strip()
                if prev.startswith('return ') or prev in ('};', '}') or prev.startswith(('return;', 'return null;')):
                    continue
            out.append(line)
        return "\n".join(out)

    raw_php = _clean_duplicate_returns(raw_php)

    # 7. Clean up redundant immediate gotos and unreferenced labels
    def _clean_redundant_gotos_and_labels(code: str) -> str:
        # Drop `goto label_X;` immediately preceding `label_X:`
        code = re.sub(
            r'^[ \t]*goto\s+(label_\w+);\s*\n(?=[ \t]*\1:)',
            '',
            code,
            flags=re.MULTILINE,
        )
        # Drop any label_X: if no goto references it
        referenced = set(re.findall(r'\bgoto\s+(label_\w+);', code))
        lines = code.splitlines()
        filtered = []
        for line in lines:
            m_lbl = re.match(r'^[ \t]*(label_\w+):', line)
            if m_lbl and m_lbl.group(1) not in referenced:
                continue
            filtered.append(line)
        return "\n".join(filtered)

    raw_php = _clean_redundant_gotos_and_labels(raw_php)

    # Clean up any leftover stray unstructured catch comments
    raw_php = re.sub(
        r'\s*/\*\s*\[opcode\s+\d+\]\s*ZEND_CATCH\s+unstructured\s+catch\s*\*/',
        '',
        raw_php,
    )

    # Clean up any generator / reconstruction banner comments
    raw_php = re.sub(
        r'/\*\s*\n\s*\*\s*(?:Reconstructed by|decoded by)[\s\S]*?\*/\s*',
        '',
        raw_php,
    )

    # 4. If namespace detected, format top of file cleanly
    if namespace:
        # Check if <?php already exists
        raw_php = re.sub(r'<\?php\s*', '', raw_php, count=1)
        # Remove any leading reconstruction comment block to place after namespace
        raw_php = raw_php.strip()

        # Build clean header
        header = f"<?php\n\nnamespace {namespace};\n\n"
        raw_php = header + raw_php

    # 5. Extract and apply imports (use statements)
    raw_php = _extract_and_apply_imports(raw_php, namespace=namespace, declared_classes=declared_classes)

    # Normalize multiple blank lines
    raw_php = re.sub(r'\n{3,}', '\n\n', raw_php)
    return raw_php.strip() + "\n"



def is_ioncube_file(path: Path) -> bool:
    """Check if a file contains the IonCube header/marker."""
    try:
        content = path.read_bytes()[:1024]
        return b"HR+c" in content or b"ionCube Loader" in content
    except Exception:
        return False


def validate_php_syntax(php_file: Path) -> tuple[bool, str]:
    """Validate PHP syntax using `php -l`."""
    try:
        res = subprocess.run(
            ["php", "-l", str(php_file)],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=10,
        )
        output = (res.stdout + res.stderr).strip()
        return res.returncode == 0, output
    except Exception as exc:
        return False, str(exc)


import shutil
import time

def decompile_file(
    input_path: Path,
    output_path: Path | None = None,
    *,
    php_version: int | None = None,
    loader_dll: Path | None = None,
    silent_header: bool = False,
) -> tuple[bool, bool, str | None]:
    """Decompile a single IonCube-encoded PHP file.
    
    Returns:
        (success: bool, syntax_ok: bool, error_msg: str | None)
    """
    if output_path is None:
        output_path = input_path.with_name(f"{input_path.stem}.reconstructed.php")

    if not silent_header:
        print(f"\n[*] Decompiling: {input_path.name}")
    try:
        icdump, _, header_report = dump_file_to_ir(
            input_path,
            php_version=php_version,
            loader_dll=loader_dll,
            save_files=False,
        )

        prog = parse_dump(icdump)
        php_ast = decompile_program(prog)
        php_ast = optimize(php_ast)
        raw_code = emit_php(php_ast)
        final_code = clean_php_source(raw_code)

        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(final_code, encoding="utf-8")
        if not silent_header:
            print(f"    -> Output saved: {output_path.name} ({len(final_code)} bytes)")

        # Validate syntax with php -l
        ok, msg = validate_php_syntax(output_path)
        if ok:
            if not silent_header:
                print(f"    [+] Syntax check: PASS (valid PHP)")
        else:
            if not silent_header:
                print(f"    [!] Syntax warning: {msg}")
        return True, ok, None
    except Exception as exc:
        err_msg = str(exc)
        if not silent_header:
            print(f"    [-] Decompilation failed: {err_msg}")
        return False, False, err_msg


def main() -> int:
    # Check if invoked as `scan` subcommand: python decompile.py scan <path>
    if len(sys.argv) > 1 and sys.argv[1].lower() == "scan":
        scan_parser = argparse.ArgumentParser(
            prog="python decompile.py scan",
            description="Scan a project or file to detect encoded/obfuscated PHP files (ionCube, SourceGuardian, Zend, Bolt, etc.)",
        )
        scan_parser.add_argument("path", type=Path, help="Project directory or PHP file to scan")
        scan_parser.add_argument("--json", action="store_true", help="Output results in JSON format")
        scan_parser.add_argument("-d", "--decompile", action="store_true", help="Auto-decompile detected ionCube files")
        scan_parser.add_argument("-o", "--output", type=Path, help="Output directory when decompiling")
        scan_parser.add_argument("--php-version", type=int, choices=(81, 82, 83, 84))
        scan_parser.add_argument("--loader-dll", type=Path)
        args = scan_parser.parse_args(sys.argv[2:])

        if not args.path.exists():
            print(f"Error: path not found: {args.path}", file=sys.stderr)
            return 1

        report = scan_project(args.path)
        print_scan_report(report, as_json=args.json)

        if args.decompile and report.encoded_count > 0:
            ioncube_items = [f for f in report.encoded_files if f.match.name == "ionCube"]
            if ioncube_items:
                print(f"\n[*] Starting auto-decompilation of {len(ioncube_items)} ionCube file(s)...")
                for idx, f_info in enumerate(ioncube_items, 1):
                    out_f = (args.output / f_info.relative_path) if args.output else f_info.path.with_name(f"{f_info.path.stem}.reconstructed.php")
                    print(f"[{idx}/{len(ioncube_items)}] Decompiling: {f_info.relative_path} ... ", end="", flush=True)
                    ok, syn_ok, err = decompile_file(
                        f_info.path,
                        output_path=out_f,
                        php_version=args.php_version,
                        loader_dll=args.loader_dll,
                        silent_header=True,
                    )
                    st = "PASS" if syn_ok else ("SUCCESS" if ok else "FAILED")
                    print(f"[{st}]")
        return 0

    parser = argparse.ArgumentParser(
        description="Unified IonCube PHP 8.1 - 8.4 Decompiler (Single File & Batch Directory)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("input", type=Path, help="Target PHP file or directory to decompile")
    parser.add_argument("-o", "--output", type=Path, help="Output file or directory (preserves tree structure)")
    parser.add_argument("--scan", action="store_true", help="Scan target for encoded/obfuscated files instead of decompiling")
    parser.add_argument("--json", action="store_true", help="Output results in JSON format (when used with --scan)")
    parser.add_argument("--in-place", action="store_true", help="Overwrite IonCube files in place with decompiled PHP")
    parser.add_argument("--no-backup", action="store_true", help="Do not create .bak files when using --in-place")
    parser.add_argument("--no-copy-other", action="store_true", help="Do not copy non-IonCube files to output directory")
    parser.add_argument("--php-version", type=int, choices=(81, 82, 83, 84),
                        help="Target PHP ABI (inferred from header if omitted)")
    parser.add_argument("--loader-dll", type=Path, help="Optional ionCube loader DLL for string resolution")

    args = parser.parse_args()
    input_path: Path = args.input

    if not input_path.exists():
        print(f"Error: path not found: {input_path}", file=sys.stderr)
        return 1

    if args.scan:
        report = scan_project(input_path)
        print_scan_report(report, as_json=args.json)
        return 0

    # Single file mode
    if input_path.is_file():
        out_target = args.output
        if args.in_place:
            if not args.no_backup:
                backup = input_path.with_name(f"{input_path.name}.bak")
                if not backup.exists():
                    shutil.copy2(input_path, backup)
            out_target = input_path
        success, syntax_ok, err = decompile_file(
            input_path,
            output_path=out_target,
            php_version=args.php_version,
            loader_dll=args.loader_dll,
        )
        return 0 if success else 1

    # Directory mode
    print(f"\n" + "=" * 60)
    print(f"  IonCube Batch Directory Decompiler")
    print(f"  Source Directory : {input_path}")
    if args.output:
        print(f"  Target Directory : {args.output}")
    elif args.in_place:
        print(f"  Mode             : In-place overwrite (backups={not args.no_backup})")
    else:
        print(f"  Mode             : Generate *.reconstructed.php alongside files")
    print("=" * 60)

    # 1. Scan directory
    all_files = [f for f in input_path.rglob("*") if f.is_file()]
    ioncube_files = [f for f in all_files if f.suffix == ".php" and is_ioncube_file(f)]
    other_files = [f for f in all_files if f not in ioncube_files]

    print(f"Found {len(all_files)} total file(s):")
    print(f"  - {len(ioncube_files)} IonCube-protected PHP file(s)")
    print(f"  - {len(other_files)} non-protected / asset file(s)")

    if not ioncube_files:
        print(f"\nNo IonCube-protected PHP files detected in: {input_path}")
        return 0

    # 2. Copy other files if output directory specified
    copied_count = 0
    if args.output and not args.no_copy_other:
        print(f"\n[*] Copying non-protected files to destination...")
        for other in other_files:
            rel = other.relative_to(input_path)
            dest = args.output / rel
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(other, dest)
            copied_count += 1
        print(f"    -> Copied {copied_count} file(s).")

    # 3. Decompile IonCube files
    print(f"\n[*] Starting batch decompilation of {len(ioncube_files)} file(s)...\n")
    start_time = time.time()
    results = []

    for idx, f in enumerate(ioncube_files, 1):
        rel = f.relative_to(input_path)
        pct = (idx / len(ioncube_files)) * 100

        if args.output:
            out_file = args.output / rel
        elif args.in_place:
            if not args.no_backup:
                backup = f.with_name(f"{f.name}.bak")
                if not backup.exists():
                    shutil.copy2(f, backup)
            out_file = f
        else:
            out_file = f.with_name(f"{f.stem}.reconstructed.php")

        print(f"[{idx}/{len(ioncube_files)}] ({pct:5.1f}%) {rel} ... ", end="", flush=True)

        success, syntax_ok, err = decompile_file(
            f,
            out_file,
            php_version=args.php_version,
            loader_dll=args.loader_dll,
            silent_header=True,
        )

        status_str = "SUCCESS" if success else "FAILED"
        syntax_str = "PASS" if syntax_ok else ("WARN" if success else "N/A")
        if success:
            if syntax_ok:
                print(f"[+] {status_str} (php -l: {syntax_str})")
            else:
                print(f"[!] {status_str} (php -l: {syntax_str})")
        else:
            print(f"[-] {status_str}: {err}")

        results.append({
            "file": rel,
            "success": success,
            "syntax_ok": syntax_ok,
            "error": err,
        })

    elapsed = time.time() - start_time

    # 4. Final summary report
    success_count = sum(1 for r in results if r["success"])
    syntax_pass_count = sum(1 for r in results if r["syntax_ok"])
    failed_items = [r for r in results if not r["success"]]

    print("\n" + "=" * 60)
    print("  BATCH DECOMPILATION SUMMARY")
    print("=" * 60)
    print(f"  Total IonCube files  : {len(ioncube_files)}")
    print(f"  Successfully decoded : {success_count} / {len(ioncube_files)}")
    print(f"  Syntax Valid (php -l): {syntax_pass_count} / {success_count}")
    if args.output and not args.no_copy_other:
        print(f"  Other files mirrored : {copied_count}")
    print(f"  Total time elapsed   : {elapsed:.2f}s")

    if failed_items:
        print("\n  Failed Files:")
        for it in failed_items:
            print(f"    - {it['file']}: {it['error']}")
    print("=" * 60 + "\n")

    return 0 if success_count == len(ioncube_files) else 1


if __name__ == "__main__":
    sys.exit(main())
