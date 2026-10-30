#!/usr/bin/env python3
"""Unified IonCube PHP 8.1 - 8.4 Decompiler.

Decompiles IonCube-protected PHP files directly to clean, valid PHP source code.

Usage:
    python decompile.py <file_or_dir> [-o <output>] [--php-version {72,73,74,81,82,83,84}]
"""

from __future__ import annotations

import argparse
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

# Add decompiler src to Python module path
_REPO_ROOT = Path(__file__).resolve().parent
_SRC_DIR = _REPO_ROOT / "ioncube-php8-decompiler" / "src"
if str(_SRC_DIR) not in sys.path:
    sys.path.insert(0, str(_SRC_DIR))

from engines.ioncube import dump_file_to_ir
from php_reconstructor.loader.json_loader import parse_dump
from php_reconstructor.decompiler.program import decompile_program
from php_reconstructor.decompiler.optimize import optimize
from php_reconstructor.emitter.php_emitter import emit_php
from php_reconstructor import ast as php
from detector import scan_project, print_scan_report
from engines.yakpro import is_yakpro_obfuscated, deobfuscate_yakpro, format_per_coding_style


LARAVEL_FACADES = {
    "App": "Illuminate\\Support\\Facades\\App",
    "Artisan": "Illuminate\\Support\\Facades\\Artisan",
    "Auth": "Illuminate\\Support\\Facades\\Auth",
    "Blade": "Illuminate\\Support\\Facades\\Blade",
    "Broadcast": "Illuminate\\Support\\Facades\\Broadcast",
    "Bus": "Illuminate\\Support\\Facades\\Bus",
    "Cache": "Illuminate\\Support\\Facades\\Cache",
    "Config": "Illuminate\\Support\\Facades\\Config",
    "Cookie": "Illuminate\\Support\\Facades\\Cookie",
    "Crypt": "Illuminate\\Support\\Facades\\Crypt",
    "Date": "Illuminate\\Support\\Facades\\Date",
    "DB": "Illuminate\\Support\\Facades\\DB",
    "Event": "Illuminate\\Support\\Facades\\Event",
    "File": "Illuminate\\Support\\Facades\\File",
    "Gate": "Illuminate\\Support\\Facades\\Gate",
    "Hash": "Illuminate\\Support\\Facades\\Hash",
    "Http": "Illuminate\\Support\\Facades\\Http",
    "Lang": "Illuminate\\Support\\Facades\\Lang",
    "Log": "Illuminate\\Support\\Facades\\Log",
    "Mail": "Illuminate\\Support\\Facades\\Mail",
    "Notification": "Illuminate\\Support\\Facades\\Notification",
    "Password": "Illuminate\\Support\\Facades\\Password",
    "Queue": "Illuminate\\Support\\Facades\\Queue",
    "RateLimiter": "Illuminate\\Support\\Facades\\RateLimiter",
    "Redirect": "Illuminate\\Support\\Facades\\Redirect",
    "Request": "Illuminate\\Support\\Facades\\Request",
    "Response": "Illuminate\\Support\\Facades\\Response",
    "Route": "Illuminate\\Support\\Facades\\Route",
    "Schema": "Illuminate\\Support\\Facades\\Schema",
    "Session": "Illuminate\\Support\\Facades\\Session",
    "Storage": "Illuminate\\Support\\Facades\\Storage",
    "URL": "Illuminate\\Support\\Facades\\URL",
    "Validator": "Illuminate\\Support\\Facades\\Validator",
    "View": "Illuminate\\Support\\Facades\\View",
    "Carbon": "Carbon\\Carbon",
    "Str": "Illuminate\\Support\\Str",
    "Arr": "Illuminate\\Support\\Arr",
}

PHP_GLOBAL_CLASSES = (
    "ArrayAccess",
    "ArrayObject",
    "Closure",
    "Countable",
    "DateTime",
    "DateTimeImmutable",
    "DateTimeInterface",
    "Exception",
    "Generator",
    "InvalidArgumentException",
    "Iterator",
    "IteratorAggregate",
    "JsonSerializable",
    "LogicException",
    "PDO",
    "PDOException",
    "RuntimeException",
    "SplFileInfo",
    "SplFileObject",
    "stdClass",
    "Stringable",
    "Throwable",
    "Traversable",
    "TypeError",
    "UnexpectedValueException",
    "ValueError",
    "WeakMap",
)

VENDOR_PSR4_MAP = {
    "DiDom": ["Document", "Element", "Node", "Query", "ClassList", "Style", "Encoder", "Errors"],
    "Detection": ["MobileDetect"],
    "Sqids": ["Sqids", "SqidsOptions", "SqidsBlocklist"],
    "Illuminate": ["Support", "Database", "Routing", "Http", "Contracts"],
    "Symfony": ["Component", "Contracts"],
}


_COMPARISON_INVERSIONS = {
    "===": "!==",
    "!==": "===",
    "==": "!=",
    "!=": "==",
    ">=": "<",
    "<=": ">",
    ">": "<=",
    "<": ">=",
}
_SIMPLE_ATOM_RE = re.compile(
    r"^(?:\$[A-Za-z_]\w*(?:\[[^\]]*\])?(?:->[A-Za-z_]\w*)?|[A-Za-z_]\w*\([^()]*\))$"
)


def _strip_outer_parens(expr: str) -> str:
    """Remove only parentheses that wrap the whole expression."""
    expr = expr.strip()
    while expr.startswith("(") and expr.endswith(")"):
        masked = _mask_php_literals(expr)
        depth = 0
        wraps = True
        for index, char in enumerate(masked):
            if char == "(":
                depth += 1
            elif char == ")":
                depth -= 1
                if depth == 0 and index != len(masked) - 1:
                    wraps = False
                    break
        if not wraps:
            break
        expr = expr[1:-1].strip()
    return expr


def _split_top_level(expr: str, operator: str) -> tuple[str, str] | None:
    """Split on an operator that is not nested in parens, strings or comments."""
    masked = _mask_php_literals(expr)
    depth = 0
    for index, char in enumerate(masked):
        if char in "([":
            depth += 1
        elif char in ")]":
            depth -= 1
        elif depth == 0 and masked.startswith(operator, index):
            return expr[:index], expr[index + len(operator):]
    return None


def _invert_condition(cond: str) -> str:
    """Negate a boolean expression without changing its meaning."""
    cond = _strip_outer_parens(cond.strip())
    if not cond:
        return "true"

    split = _split_top_level(cond, "||")
    if split:
        parts = [_invert_condition(split[0]), _invert_condition(split[1])]
        joined = [f"({part})" if _split_top_level(part, "||") else part for part in parts]
        return " && ".join(joined)

    split = _split_top_level(cond, "&&")
    if split:
        return f"{_invert_condition(split[0])} || {_invert_condition(split[1])}"

    if _split_top_level(cond, "<=>"):
        return f"!({cond})"

    for operator in ("===", "!==", "==", "!=", ">=", "<=", ">", "<"):
        split = _split_top_level(cond, operator)
        if split is None:
            continue
        left, right = split
        if operator == ">" and left.rstrip().endswith(("-", "=")):
            continue
        return f"{left.strip()} {_COMPARISON_INVERSIONS[operator]} {right.strip()}"

    if cond.startswith("!") and not cond.startswith("!="):
        return _strip_outer_parens(cond[1:].strip())

    if _SIMPLE_ATOM_RE.match(cond):
        return f"!{cond}"
    return f"!({cond})"


def _simplify_boolean_expressions(code: str) -> str:
    """Simplify negated boolean expressions with De Morgan patterns."""
    def repl_dm(m):
        full = m.group(0)
        prefix = m.group(1)
        inner = m.group(2)
        m_or = re.match(r'^!\s*([a-zA-Z0-9_\$->:()\[\]\'"]+)\s*\|\|\s*(.+)$', inner)
        if m_or:
            a = m_or.group(1).strip()
            b = m_or.group(2).strip()
            return f"{prefix}{a} && {_invert_condition(b)}"
        m_and_both = re.match(r'^!\s*([a-zA-Z0-9_\$->:()\[\]\'"]+)\s*&&\s*!\s*(.+)$', inner)
        if m_and_both:
            a = m_and_both.group(1).strip()
            b = m_and_both.group(2).strip()
            return f"{prefix}{a} || {b}"
        m_and = re.match(r'^!\s*([a-zA-Z0-9_\$->:()\[\]\'"]+)\s*&&\s*(.+)$', inner)
        if m_and:
            a = m_and.group(1).strip()
            b = m_and.group(2).strip()
            return f"{prefix}{a} || {_invert_condition(b)}"
        return full

    code = re.sub(r'\b(if\s*\(|while\s*\()!\s*\(([^()]+(?:\([^()]*\)[^()]*)*)\)', repl_dm, code)
    return code


def _invert_empty_if_guards(code: str) -> str:
    """Universally invert empty if guards followed by loop/return/throw statements."""
    lines = code.splitlines()
    out = []
    i = 0
    n = len(lines)
    while i < n:
        line = lines[i]
        m_empty_single = re.match(r'^([ \t]*)if\s*\((.+)\)\s*\{\s*\}\s*$', line)
        m_empty_open = re.match(r'^([ \t]*)if\s*\((.+)\)\s*\{\s*$', line)
        
        indent = None
        cond = None
        next_i = i + 1

        if m_empty_single:
            indent = m_empty_single.group(1)
            cond = m_empty_single.group(2)
        elif m_empty_open and i + 1 < n and re.match(r'^[ \t]*\}\s*$', lines[i + 1]):
            indent = m_empty_open.group(1)
            cond = m_empty_open.group(2)
            next_i = i + 2

        if indent is not None and cond is not None:
            if next_i < n:
                followed_line = lines[next_i]
                f_strip = followed_line.strip()
                is_terminal = (
                    f_strip.startswith(('continue;', 'break;', 'return ', 'return;', 'throw '))
                )
                if is_terminal and followed_line.startswith(indent):
                    inv_cond = _invert_condition(cond)
                    inner_indent = indent + "    "
                    out.append(f"{indent}if ({inv_cond}) {{")
                    out.append(f"{inner_indent}{f_strip}")
                    out.append(f"{indent}}}")
                    i = next_i + 1
                    continue
                if next_i + 1 < n:
                    next2 = lines[next_i + 1]
                    f2_strip = next2.strip()
                    if (f2_strip.startswith(('return', 'continue;', 'break;', 'exit;')) 
                            and followed_line.startswith(indent) and next2.startswith(indent)):
                        inv_cond = _invert_condition(cond)
                        inner_indent = indent + "    "
                        out.append(f"{indent}if ({inv_cond}) {{")
                        out.append(f"{inner_indent}{f_strip}")
                        out.append(f"{inner_indent}{f2_strip}")
                        out.append(f"{indent}}}")
                        i = next_i + 2
                        continue

        out.append(line)
        i += 1
    
    # Remove any remaining empty if blocks. Conditions can contain nested
    # parentheses, so match the opening line rather than the condition text.
    res = "\n".join(out)
    lines = res.splitlines()
    cleaned = []
    i = 0
    while i < len(lines):
        if re.match(r'^[ \t]*if\s*\(.*\)\s*\{\s*$', lines[i]):
            j = i + 1
            while j < len(lines) and not lines[j].strip():
                j += 1
            if j < len(lines) and re.match(r'^[ \t]*\}\s*$', lines[j]):
                i = j + 1
                continue
        cleaned.append(lines[i])
        i += 1
    return "\n".join(cleaned)


_LOOP_HEADER_RE = re.compile(r"^([ \t]*)(foreach|while|for)\b[^\n]*\{\s*$")
_SWITCH_HEADER_RE = re.compile(r"^([ \t]*)switch\b[^\n]*\{\s*$")
_FUNCTION_HEADER_RE = re.compile(
    r"^[ \t]*(?:(?:public|private|protected|static|final|abstract|readonly)\s+)*"
    r"function\b[^\n]*\{\s*$"
)
_LABEL_LINE_RE = re.compile(r"^[ \t]*(label_\w+):\s*$")


def _block_close_line(masked_lines: list[str], start: int) -> int | None:
    depth = 0
    for index in range(start, len(masked_lines)):
        depth += masked_lines[index].count("{") - masked_lines[index].count("}")
        if depth == 0:
            return index
    return None


def _function_spans(masked_lines: list[str]) -> list[tuple[int, int]]:
    spans = []
    for index, line in enumerate(masked_lines):
        if _FUNCTION_HEADER_RE.match(line):
            close = _block_close_line(masked_lines, index)
            if close is not None:
                spans.append((index, close))
    return spans


def _label_scope(masked_lines: list[str], line_index: int) -> tuple[int, int]:
    spans = [s for s in _function_spans(masked_lines) if s[0] <= line_index <= s[1]]
    return min(spans, key=lambda s: s[1] - s[0]) if spans else (0, len(masked_lines) - 1)


def _drop_redundant_gotos(lines: list[str], masked: list[str]) -> bool:
    removals = set()
    for index, line in enumerate(masked):
        match = re.match(r"^[ \t]*goto\s+(label_\w+);\s*$", line)
        if not match:
            continue
        following = index + 1
        while following < len(masked) and not masked[following].strip():
            following += 1
        if following >= len(masked) or not re.match(
            r"^[ \t]*" + re.escape(match.group(1)) + r":\s*$", masked[following]
        ):
            continue
        previous = index - 1
        while previous >= 0 and not masked[previous].strip():
            previous -= 1
        if previous >= 0 and masked[previous].rstrip().endswith("{"):
            continue
        removals.add(index)
    for index in sorted(removals, reverse=True):
        del lines[index]
    return bool(removals)


def _drop_unreferenced_labels(lines: list[str], masked: list[str]) -> bool:
    removals: set[int] = set()
    spans = _function_spans(masked) or [(0, len(masked) - 1)]
    for start, end in spans:
        referenced = set(
            re.findall(r"\bgoto\s+(label_\w+)\s*;", "\n".join(masked[start:end + 1]))
        )
        for index in range(start, end + 1):
            match = _LABEL_LINE_RE.match(masked[index])
            if match and match.group(1) not in referenced:
                removals.add(index)
    for index in sorted(removals, reverse=True):
        del lines[index]
    return bool(removals)


def _structure_loop_exit_guards(code: str) -> str:
    """Rewrite `if (cond) goto label;` loop exits as break, preserving skipped code."""
    for _ in range(512):
        lines = code.splitlines()
        masked = _mask_php_literals(code).splitlines()
        if _drop_redundant_gotos(lines, masked):
            code = "\n".join(lines)
            continue
        if _drop_unreferenced_labels(lines, masked):
            code = "\n".join(lines)
            continue
        action = None

        for i in range(len(lines) - 2):
            header = re.match(r"^([ \t]*)if\s*\((.+)\)\s*\{\s*$", masked[i])
            if not header:
                continue
            goto_line = i + 1
            while goto_line < len(lines) and not masked[goto_line].strip():
                goto_line += 1
            rm = re.match(r"^[ \t]*goto\s+(label_\w+);\s*$", masked[goto_line]) if goto_line < len(lines) else None
            if not rm:
                continue
            close_line = goto_line + 1
            while close_line < len(lines) and not masked[close_line].strip():
                close_line += 1
            if close_line >= len(lines) or not re.match(r"^[ \t]*\}\s*$", masked[close_line]):
                continue
            after = close_line + 1
            while after < len(lines) and not masked[after].strip():
                after += 1
            if after < len(lines) and re.match(r"^[ \t]*(?:else|elseif)\b", masked[after]):
                continue

            label = rm.group(1)
            scope_start, scope_end = _label_scope(masked, i)
            if len(re.findall(
                r"\bgoto\s+" + re.escape(label) + r"\s*;",
                "\n".join(masked[scope_start:scope_end + 1]),
            )) != 1:
                continue

            guard_indent = len(header.group(1))
            loop_line = None
            for candidate in range(i - 1, -1, -1):
                lm = _LOOP_HEADER_RE.match(masked[candidate])
                if not lm or len(lm.group(1)) >= guard_indent:
                    continue
                if _block_close_line(masked, candidate) is None:
                    continue
                loop_line = candidate
                break
            if loop_line is None:
                continue

            loop_indent = len(_LOOP_HEADER_RE.match(masked[loop_line]).group(1))
            loop_close = _block_close_line(masked, loop_line)
            if loop_close is None or loop_close <= close_line:
                continue

            in_switch = any(
                _SWITCH_HEADER_RE.match(masked[cand])
                and len(_SWITCH_HEADER_RE.match(masked[cand]).group(1)) < guard_indent
                and (_block_close_line(masked, cand) or -1) > i
                for cand in range(loop_line + 1, i)
            )
            if in_switch:
                continue

            label_line = None
            for cand in range(loop_close + 1, scope_end + 1):
                if re.match(r"^[ \t]*" + re.escape(label) + r":\s*$", masked[cand]):
                    label_line = cand
                    break
            if label_line is None or label_line <= loop_close:
                continue

            outer_loop = None
            for cand in range(loop_line - 1, -1, -1):
                lm = _LOOP_HEADER_RE.match(masked[cand])
                if not lm or len(lm.group(1)) >= loop_indent:
                    continue
                cand_close = _block_close_line(masked, cand)
                if cand_close is not None and cand_close > loop_line:
                    outer_loop = cand_close
                    break
            if outer_loop is not None and label_line > outer_loop:
                continue

            direct = all(not masked[cand].strip() for cand in range(loop_close + 1, label_line))
            if not direct:
                label_indent = len(re.match(r"^[ \t]*", masked[label_line]).group(0))
                if label_indent > loop_indent:
                    continue
                intervening = masked[loop_close + 1:label_line]
                if any(re.search(r"\b(?:goto\s+label_|label_\w+\s*:)", line) for line in intervening):
                    continue
                depth = sum(line.count("{") - line.count("}") for line in intervening)
                if depth != 0:
                    continue

            action = (i, goto_line, close_line, loop_close, label_line, header.group(2), label, guard_indent, loop_indent, direct)
            break

        if action is None:
            return code

        i, goto_line, close_line, loop_close, label_line, cond, label, guard_indent, loop_indent, direct = action
        flag = f"$__exit_guard_{label.split('_')[-1]}"
        if flag in code:
            suffix = 2
            while f"{flag}_{suffix}" in code:
                suffix += 1
            flag = f"{flag}_{suffix}"

        break_indent = " " * (guard_indent + 4)
        guard_body = []
        if not direct:
            guard_body.append(f"{break_indent}{flag} = true;")
        guard_body.append(f"{break_indent}break;")

        replacement = [lines[i], *guard_body, lines[close_line]]
        if direct:
            lines[i:close_line + 1] = replacement
        else:
            wrapper_open = f"{' ' * loop_indent}if (empty({flag})) {{"
            wrapper_close = f"{' ' * loop_indent}}}"
            lines[i:close_line + 1] = replacement
            # Both the loop close and the target label move with the guard.
            shift = len(replacement) - (close_line - i + 1)
            label_line += shift
            loop_close += shift
            lines[label_line:label_line] = [wrapper_close]
            lines[loop_close + 1:loop_close + 1] = [wrapper_open]
        code = "\n".join(lines)

    return code


def _normalize_psr4_namespaces(
    code: str,
    namespace: str | None = None,
    declared_classes: set[str] | None = None,
) -> str:
    """Universally normalize PascalCase concatenated namespaces for vendor and project classes."""
    declared_classes = declared_classes or set()

    def replace_namespace(match: re.Match[str], target: str) -> str:
        return match.group(0) if match.group(0) in declared_classes else target

    for vendor, classes in VENDOR_PSR4_MAP.items():
        for cls in classes:
            target = f"{vendor}\\{cls}"
            code = re.sub(
                r'\b' + vendor + cls + r'\b',
                lambda m, t=target: replace_namespace(m, t),
                code,
            )
            code = re.sub(
                r'\b' + vendor + r'\\\\?' + cls + r'\b',
                lambda m, t=target: replace_namespace(m, t),
                code,
            )

    if namespace:
        root_ns = namespace.split('\\')[0]

        def repl_project_ns(m):
            matched = m.group(0)
            if matched in declared_classes:
                return matched
            # Keep acronym runs whole: AppXMLParser -> App, XML, Parser.
            parts = re.split(r'(?<=[a-z0-9])(?=[A-Z])|(?<=[A-Z])(?=[A-Z][a-z])', matched)
            if len(parts) >= 2:
                return '\\'.join(parts)
            return matched

        code = re.sub(
            r'\b' + re.escape(root_ns) + r'[A-Z][A-Za-z0-9_]+\b',
            repl_project_ns,
            code,
        )

    return code


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

    # Auto-detect unimported standard Laravel facades
    for short, fqcn in LARAVEL_FACADES.items():
        if short in declared_classes or short in imports or short in collisions:
            continue
        parts_fqcn = fqcn.split('\\')
        ns_of_class = '\\'.join(parts_fqcn[:-1])
        if namespace and ns_of_class.lower() == namespace.lower():
            continue
        facade_pattern = re.compile(
            r'(?<![A-Za-z0-9_])(?:\\)?' + re.escape(short) + r'(?:::|\s+\$[A-Za-z0-9_]+)'
        )
        used = False
        for i in range(0, len(parts), 2):
            if facade_pattern.search(parts[i]):
                used = True
                break
        if used:
            imports[short] = fqcn

    # Bytecode stores FQCNs, so a bare `Closure`/`Exception` type hint in a
    # namespaced file is a global reference that lost its `use` statement.
    global_imports: set[str] = set()
    if namespace:
        for short in PHP_GLOBAL_CLASSES:
            if short in declared_classes or short in imports or short in collisions:
                continue
            used = re.compile(r"(?<![A-Za-z0-9_\\$>:])" + re.escape(short) + r"\b")
            if any(used.search(parts[i]) for i in range(0, len(parts), 2)):
                global_imports.add(short)

    if not imports and not global_imports:
        return php_code

    sorted_short_names = sorted(imports.keys(), key=lambda s: len(imports[s]), reverse=True)
    for short in sorted_short_names:
        full = imports[short]
        sub_pat = re.compile(r'(?:\\|\b)' + re.escape(full) + r'\b')
        for i in range(0, len(parts), 2):
            parts[i] = sub_pat.sub(short, parts[i])

    body = ''.join(parts)
    use_lines = [f"use {imports[s]};" for s in sorted(imports.keys(), key=lambda s: imports[s].lower())]
    use_lines.extend(f"use {s};" for s in sorted(global_imports))
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


STRICT_TYPES_DECLARE = "declare(strict_types=1);"


def _insert_strict_types_declare(code: str) -> str:
    """Put `declare(strict_types=1);` right after the PHP open tag."""
    if re.search(r"declare\s*\(\s*strict_types\s*=", code):
        return code

    open_tag = re.search(r"<\?php", code)
    if not open_tag:
        return f"<?php\n\n{STRICT_TYPES_DECLARE}\n\n{code}"

    head = code[: open_tag.end()]
    tail = code[open_tag.end():].lstrip("\n")
    return f"{head}\n\n{STRICT_TYPES_DECLARE}\n\n{tail}"


def ir_declares_strict_types(icdump: dict) -> bool:
    """True when the encoded file's main op_array was compiled strict."""
    op_arrays = icdump.get("op_arrays")
    main = op_arrays.get("main") if isinstance(op_arrays, dict) else None
    return bool(isinstance(main, dict) and main.get("strict_types"))


def clean_php_source(raw_php: str, *, strict_types: bool = False) -> str:
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
        declared_classes.add(short_name)


        # Replace full namespaced declaration with short name
        raw_php = re.sub(
            r'\b(class|interface|trait|enum)\s+' + re.escape(full_name) + r'\b',
            r'\1 ' + short_name,
            raw_php,
        )

        # Strip namespace prefix from local references inside the file
        raw_php = re.sub(re.escape(namespace) + r'\\', '', raw_php, flags=re.IGNORECASE)

    # 2. Fix unresolved constructor calls
    raw_php = re.sub(r'\b(?:self|parent)::\?\(\);', 'parent::__construct();', raw_php)

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
                if has_zend_catch:
                    catch_start = j
                    while j < n and not lines[j].strip().startswith(target_label):
                        catch_lines_scan = lines[j].strip()
                        if catch_lines_scan.startswith(('function', 'public', 'private', 'protected', 'class', 'trait', 'interface')):
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
                        k = len(out) - 1
                        brace_depth = 0
                        paren_depth = 0
                        bracket_depth = 0
                        while k >= 0:
                            s = out[k].strip()
                            if s.startswith(('function', 'public', 'private', 'protected', 'class', 'trait', 'interface')):
                                k += 1
                                break
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
                        if 0 <= k < len(out):
                            try_lines = out[k:]
                            net_braces = sum(tl.count('{') - tl.count('}') for tl in try_lines)
                            if net_braces == 0 and any(tl.strip() and not tl.strip().startswith(('//', '/*')) for tl in try_lines):
                                del out[k:]
                                exc_var = "$exception" if "$exception" in catch_text else "$e"
                                out.append(f"{indent}try {{")
                                for tl in try_lines:
                                    out.append(f"    {tl}" if tl.strip() else "")
                                # The original catch type is not recoverable from
                                # an unstructured catch; Throwable is the only safe
                                # supertype that cannot be narrower than the source.
                                out.append(f"{indent}}} catch (\\Throwable {exc_var}) {{")
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
                if re.match(r'^return\b[^;]*;', prev):
                    continue
            out.append(line)
        return "\n".join(out)

    raw_php = _clean_duplicate_returns(raw_php)

    # 8. Clean up redundant immediate gotos and unreferenced labels
    def _clean_redundant_gotos_and_labels(code: str) -> str:
        # Drop `goto label_X;` immediately preceding `label_X:`. Keep it when
        # it is the only statement in a branch/loop body; removing it there
        # would leave an empty control-flow block.
        def _drop_redundant_goto(match: re.Match) -> str:
            prefix = code[: match.start()]
            previous = [line for line in prefix.splitlines() if line.strip()]
            if previous and previous[-1].rstrip().endswith("{"):
                return match.group(0)
            return ""

        code = re.sub(
            r'^[ \t]*goto\s+(label_\w+);\s*\n(?=[ \t]*\1:)',
            _drop_redundant_goto,
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

    # Clean up any leftover raw opcode comments
    raw_php = re.sub(r'^[ \t]*/\*\s*\[opcode\s+\d+\][^\n]*\*/\s*\n?', '', raw_php, flags=re.MULTILINE)
    raw_php = re.sub(r'/\*\s*\[opcode\s+\d+\][^\n]*\*/', '', raw_php)

    # Clean up any generator / reconstruction banner comments
    raw_php = re.sub(
        r'/\*\s*\n\s*\*\s*(?:Reconstructed by|decoded by)[\s\S]*?\*/\s*',
        '',
        raw_php,
    )

    # 4. Universal syntax and AST anomaly resolutions
    # 4a. Normalize PascalCase concatenated vendor and project namespaces
    raw_php = _normalize_psr4_namespaces(
        raw_php, namespace=namespace, declared_classes=declared_classes
    )

    # 4c. Clean dead consecutive returns
    lines = raw_php.splitlines()
    out_lines = []
    ret_i = 0
    while ret_i < len(lines):
        line = lines[ret_i]
        out_lines.append(line)
        if re.match(r'^\s*return\b[^;]*;', line):
            ret_j = ret_i + 1
            while ret_j < len(lines) and re.match(r'^\s*return\b[^;]*;', lines[ret_j]):
                ret_j += 1
            ret_i = ret_j - 1
        ret_i += 1
    raw_php = "\n".join(out_lines)

    # 4d. Universally invert empty IF error guards
    raw_php = _invert_empty_if_guards(raw_php)

    # 4e. Simplify negated boolean expressions with De Morgan patterns
    raw_php = _simplify_boolean_expressions(raw_php)

    # 4f. Turn loop-exit gotos into structured break/flag guards
    raw_php = _structure_loop_exit_guards(raw_php)

    # 5. If namespace detected, format top of file cleanly
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

    # After the imports: in a namespace-less file they sit right below `<?php`.
    if strict_types:
        raw_php = _insert_strict_types_declare(raw_php)

    # 6. Apply strict PHP-FIG PER Coding Style formatting
    raw_php = format_per_coding_style(raw_php)
    raw_php = _drop_undefined_gotos(raw_php)
    return raw_php


def _drop_undefined_gotos(code: str) -> str:
    """Remove gotos whose label was never emitted.

    A jump target that lands inside a structured block cannot get a label, so
    the goto would make the file fatal at compile time. Falling through is the
    only interpretation left for such a jump.
    """
    defined = set(re.findall(r"^\s*label_(\d+):", code, re.MULTILINE))
    trailing_newline = code.endswith("\n")
    lines = code.splitlines()
    out: list[str] = []
    index = 0
    while index < len(lines):
        match = re.match(r"^(\s*)goto\s+label_(\d+);\s*$", lines[index])
        if not match or match.group(2) in defined:
            out.append(lines[index])
            index += 1
            continue
        if (
            out
            and re.match(r"^\s*if\s*\(.*\)\s*\{\s*$", out[-1])
            and index + 1 < len(lines)
            and lines[index + 1].strip() == "}"
        ):
            out.pop()
            index += 2
            continue
        index += 1
    result = "\n".join(out)
    return result + "\n" if trailing_newline and result else result


def _reindent_php(code: str) -> str:
    """Format PHP code with strict 4-space indentation matching block nesting."""
    lines = code.splitlines()
    out: list[str] = []
    depth = 0
    indent_str = "    "
    in_docblock = False

    for line in lines:
        stripped = line.strip()
        if not stripped:
            out.append("")
            continue

        # Preserve docblocks /* ... */
        if stripped.startswith("/*"):
            if not stripped.endswith("*/"):
                in_docblock = True
            out.append(indent_str * depth + stripped)
            continue
        if in_docblock:
            if stripped.endswith("*/"):
                in_docblock = False
            out.append(indent_str * depth + " " + stripped)
            continue

        # Strip string literals and line comments to count structure braces accurately
        clean = re.sub(r"'(?:[^'\\]|\\.)*'", "''", stripped)
        clean = re.sub(r'"(?:[^"\\]|\\.)*"', '""', clean)
        clean = re.sub(r"//.*$", "", clean)

        # Count brace changes
        opens = clean.count("{") + clean.count("[")
        closes = clean.count("}") + clean.count("]")

        # Closing line checks
        is_closing = (
            clean.startswith("}")
            or clean.startswith("]")
            or clean.startswith(");")
            or clean.startswith("],")
            or clean.startswith("};")
            or clean.startswith(")")
        )
        is_case = clean.startswith("case ") or clean.startswith("default:")

        line_depth = depth
        if is_closing or is_case:
            line_depth = max(0, depth - 1)

        out.append(indent_str * line_depth + stripped)
        depth = max(0, depth + opens - closes)

    result = "\n".join(out)
    return result.strip() + "\n"



def is_ioncube_file(path: Path) -> bool:
    """Check if a file contains the IonCube binary header marker (HR+c)."""
    try:
        content = path.read_bytes()[:2048]
        return b"HR+c" in content
    except Exception:
        return False


def is_sourceguardian_file(path: Path) -> bool:
    """Check if a file contains the SourceGuardian wrapper/marker."""
    try:
        content = path.read_bytes()[:2048]
        return b"sg_load" in content or b"__SG_EXT__" in content or content.startswith(b"SG")
    except Exception:
        return False


def is_yakpro_file(path: Path) -> bool:
    """Check if a PHP file is obfuscated with YAK Pro."""
    try:
        content = path.read_text(encoding="utf-8", errors="ignore")
        return is_yakpro_obfuscated(content)
    except Exception:
        return False


def is_encoded_file(path: Path) -> bool:
    """Check if a file is IonCube, SourceGuardian, or YAK Pro encoded/obfuscated."""
    return is_ioncube_file(path) or is_sourceguardian_file(path) or is_yakpro_file(path)
def validate_php_syntax(php_file: Path) -> tuple[bool, str]:
    """Validate PHP syntax using `php -l`."""
    try:
        res = subprocess.run(
            ["php", "-l", str(php_file)],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=10,
        )
        output = (res.stdout + res.stderr).strip()
        return res.returncode == 0, output
    except FileNotFoundError:
        return False, "php executable not found; syntax validation skipped"
    except Exception as exc:
        return False, f"syntax validation failed: {exc}"


# Empty loop bodies are valid PHP and often carry their work in the
# condition (`while (($row = $stmt->fetch()) !== false) {}`), so only empty
# branch bodies are treated as reconstruction failures.
_EMPTY_BODY_KEYWORD = re.compile(r"\b(?:if|elseif|else|switch)\b")
_PAREN_BODY_KEYWORDS = frozenset({"if", "elseif", "switch"})


def _mask_php_literals(code: str) -> str:
    """Blank strings, comments and heredocs while preserving braces and newlines."""
    masked = list(code)
    n = len(code)

    def blank(start: int, end: int) -> None:
        for pos in range(start, min(end, n)):
            if code[pos] not in "\r\n":
                masked[pos] = " "

    i = 0
    while i < n:
        ch = code[i]
        if ch in ("'", '"', "`"):
            j = i + 1
            while j < n:
                if code[j] == "\\":
                    j += 2
                    continue
                if code[j] == ch:
                    j += 1
                    break
                j += 1
            blank(i, j)
            i = j
            continue

        if ch == "/" and i + 1 < n and code[i + 1] == "/":
            j = code.find("\n", i)
            if j < 0:
                j = n
            blank(i, j)
            i = j
            continue

        if ch == "#" and not (i + 1 < n and code[i + 1] == "["):
            j = code.find("\n", i)
            if j < 0:
                j = n
            blank(i, j)
            i = j
            continue

        if ch == "/" and i + 1 < n and code[i + 1] == "*":
            j = code.find("*/", i + 2)
            j = n if j < 0 else j + 2
            blank(i, j)
            i = j
            continue

        if code.startswith("<<<", i):
            header = re.match(
                r"<<<[ \t]*(?:'([A-Za-z_][A-Za-z0-9_]*)'|\"([A-Za-z_][A-Za-z0-9_]*)\"|([A-Za-z_][A-Za-z0-9_]*))[ \t]*\r?\n",
                code[i:],
            )
            if header:
                label = header.group(1) or header.group(2) or header.group(3)
                terminator = re.compile(
                    r"(?m)^[ \t]*" + re.escape(label) + r";?[ \t]*(?:\r?\n|$)"
                )
                end = terminator.search(code, i + header.end())
                j = end.end() if end else n
                blank(i, j)
                i = j
                continue

        i += 1

    return "".join(masked)


def _matching_paren(code: str, open_pos: int) -> int | None:
    depth = 0
    for pos in range(open_pos, len(code)):
        if code[pos] == "(":
            depth += 1
        elif code[pos] == ")":
            depth -= 1
            if depth == 0:
                return pos
    return None


def _control_flow_body_open(code: str, keyword: str, keyword_end: int) -> int | None:
    pos = keyword_end
    while pos < len(code) and code[pos].isspace():
        pos += 1

    if keyword in {"else", "do"}:
        return pos if pos < len(code) and code[pos] == "{" else None

    if keyword not in _PAREN_BODY_KEYWORDS or pos >= len(code) or code[pos] != "(":
        return None

    close = _matching_paren(code, pos)
    if close is None:
        return None

    pos = close + 1
    while pos < len(code) and code[pos].isspace():
        pos += 1
    return pos if pos < len(code) and code[pos] == "{" else None


def validate_php_structure(php_code: str) -> tuple[bool, str]:
    """Reject generated PHP that contains an empty branch body."""
    if "<?php" not in php_code[:32]:
        return True, ""

    masked = _mask_php_literals(php_code)
    brace_pairs: dict[int, int] = {}
    stack: list[int] = []
    for match in re.finditer(r"[{}]", masked):
        if match.group() == "{":
            stack.append(match.start())
        elif stack:
            brace_pairs[stack.pop()] = match.start()

    problems: list[str] = []
    seen_bodies: set[int] = set()
    for match in _EMPTY_BODY_KEYWORD.finditer(masked):
        keyword = match.group()
        open_pos = _control_flow_body_open(masked, keyword, match.end())
        if open_pos is None or open_pos in seen_bodies:
            continue
        close_pos = brace_pairs.get(open_pos)
        if close_pos is None or masked[open_pos + 1:close_pos].strip():
            continue
        seen_bodies.add(open_pos)
        line = masked.count("\n", 0, match.start()) + 1
        problems.append(f"line {line}: empty {keyword} body")

    if not problems:
        return True, ""
    suffix = f" (+{len(problems) - 1} more)" if len(problems) > 1 else ""
    return False, problems[0] + suffix


import shutil
import time


def _format_partial_status(status: dict) -> str:
    methods = status.get("methods", {})
    parts = [
        f"{methods.get('ok', 0)}/{methods.get('total', 0)} methods clean",
        f"{methods.get('stubs', 0)} stub(s)",
        f"{methods.get('opcode_errors', 0)} opcode error(s)",
        f"{methods.get('failed', 0)} failed method(s)",
    ]
    loader = status.get("loader", {})
    if loader.get("degraded"):
        parts.append(f"loader PHP {loader.get('expected_php_version')} missing/mismatched")
    return ", ".join(parts)


def _result_exit_code(success: bool, syntax_ok: bool) -> int:
    if not success:
        return 1
    return 0 if syntax_ok else 2


def _write_output_atomically(
    output_path: Path,
    content: str,
    *,
    preserve_on_failure: bool,
    check_structure: bool = True,
) -> tuple[bool, bool, str, bool]:
    """Write via a same-directory temp file, validate, then replace."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(
        prefix=f".{output_path.name}.",
        suffix=".tmp",
        dir=output_path.parent,
    )
    os.close(fd)
    temp_path = Path(temp_name)
    try:
        temp_path.write_text(content, encoding="utf-8")
        if output_path.exists():
            try:
                shutil.copymode(output_path, temp_path)
            except OSError:
                pass

        syntax_ok, message = validate_php_syntax(temp_path)
        if not syntax_ok:
            message = message.replace(str(temp_path), str(output_path))

        structure_ok = True
        if syntax_ok and check_structure:
            structure_ok, structure_message = validate_php_structure(content)
            if not structure_ok:
                message = structure_message

        valid = syntax_ok and structure_ok
        wrote = valid or not preserve_on_failure
        if wrote:
            os.replace(temp_path, output_path)
        return syntax_ok, structure_ok, message, wrote
    finally:
        temp_path.unlink(missing_ok=True)


def decompile_file(
    input_path: Path,
    output_path: Path | None = None,
    *,
    php_version: int | None = None,
    loader_dll: Path | None = None,
    silent_header: bool = False,
) -> tuple[bool, bool, str | None, dict]:
    """Decompile a single IonCube-encoded PHP file.

    Returns:
        (success, syntax_ok, error_msg, decompile_status)
    """
    if output_path is None:
        output_path = input_path.with_name(f"{input_path.stem}.reconstructed.php")

    if not silent_header:
        print(f"\n[*] Decompiling: {input_path.name}")
    try:
        if is_sourceguardian_file(input_path):
            from engines.sourceguardian import decode_sg_file_to_ir
            icdump = decode_sg_file_to_ir(input_path)
            decompile_status = {"status": "ok", "encoder": "SourceGuardian"}
        elif not is_ioncube_file(input_path):
            raw_text = input_path.read_text(encoding="utf-8", errors="ignore")
            if is_yakpro_obfuscated(raw_text):
                if not silent_header:
                    print(f"    [i] Detected YAK Pro obfuscation. Deobfuscating...")
                final_code = deobfuscate_yakpro(raw_text)
                preserve_on_failure = input_path.resolve() == output_path.resolve()
                syntax_ok, structure_ok, msg, wrote = _write_output_atomically(
                    output_path,
                    final_code,
                    preserve_on_failure=preserve_on_failure,
                    check_structure=True,
                )
                if wrote:
                    if not silent_header:
                        print(f"    -> Output saved: {output_path.name} ({len(final_code)} bytes)")
                else:
                    if not silent_header:
                        print(f"    [!] Original left untouched: {output_path}")
                decompile_status = {
                    "type": "yakpro",
                    "syntax": {"ok": syntax_ok, "message": msg if not syntax_ok else ""},
                    "structure": {"ok": structure_ok, "message": msg if not structure_ok else ""},
                }
                valid = syntax_ok and structure_ok
                if valid:
                    if not silent_header:
                        print(f"    [+] Validation: PASS (valid PHP)")
                elif not syntax_ok:
                    if not silent_header:
                        print(f"    [!] Syntax warning: {msg}")
                else:
                    if not silent_header:
                        print(f"    [!] Structure warning: {msg}")
                error_msg = None if wrote else (msg or "validation failed; original left untouched")
                return wrote, valid, error_msg, decompile_status

            icdump, _, header_report = dump_file_to_ir(
                input_path,
                php_version=php_version,
                loader_dll=loader_dll,
                save_files=False,
            )
            decompile_status = icdump.get("summary", {}).get("decompile_status", {})
        else:
            icdump, _, header_report = dump_file_to_ir(
                input_path,
                php_version=php_version,
                loader_dll=loader_dll,
                save_files=False,
            )
            decompile_status = icdump.get("summary", {}).get("decompile_status", {})

        prog = parse_dump(icdump)
        php_ast = decompile_program(prog)
        php_ast = optimize(php_ast)

        # Detect blade template (.blade.php) files composed of echo statements
        is_blade = (
            input_path.name.endswith(".blade.php")
            or output_path.name.endswith(".blade.php")
            or bool(prog.source_file and prog.source_file.endswith(".blade.php"))
        )
        def _to_text(val: Any) -> str | None:
            if isinstance(val, str):
                return val
            if isinstance(val, (bytes, bytearray)):
                try:
                    return val.decode("utf-8")
                except UnicodeDecodeError:
                    return val.decode("latin-1", errors="replace")
            return None

        if is_blade and php_ast.statements and all(
            isinstance(s, php.EchoStmt) and all(isinstance(e, php.Literal) and _to_text(e.value) is not None for e in s.exprs)
            for s in php_ast.statements
        ):
            parts = []
            for s in php_ast.statements:
                for e in s.exprs:
                    t = _to_text(e.value)
                    if t is not None:
                        parts.append(t)
            final_code = "".join(parts).replace("\r\n", "\n")
            if not final_code.endswith("\n"):
                final_code += "\n"
        else:
            raw_code = emit_php(php_ast)
            final_code = clean_php_source(
                raw_code, strict_types=ir_declares_strict_types(icdump)
            )
            if is_yakpro_obfuscated(final_code):
                try:
                    final_code = deobfuscate_yakpro(final_code)
                except Exception:
                    pass

        preserve_on_failure = input_path.resolve() == output_path.resolve()
        syntax_ok, structure_ok, msg, wrote = _write_output_atomically(
            output_path,
            final_code,
            preserve_on_failure=preserve_on_failure,
            check_structure=not is_blade,
        )
        if wrote:
            if not silent_header:
                print(f"    -> Output saved: {output_path.name} ({len(final_code)} bytes)")
        else:
            if not silent_header:
                print(f"    [!] Original left untouched: {output_path}")
        decompile_status["syntax"] = {"ok": syntax_ok, "message": msg if not syntax_ok else ""}
        decompile_status["structure"] = {"ok": structure_ok, "message": msg if not structure_ok else ""}
        valid = syntax_ok and structure_ok
        if valid:
            if not silent_header:
                print(f"    [+] Validation: PASS (valid PHP)")
        elif not syntax_ok:
            if not silent_header:
                print(f"    [!] Syntax warning: {msg}")
        else:
            if not silent_header:
                print(f"    [!] Structure warning: {msg}")
        if decompile_status.get("partial") and not silent_header:
            print(f"    [!] Partial decode: {_format_partial_status(decompile_status)}")
        error_msg = None if wrote else (msg or "validation failed; original left untouched")
        return wrote, valid, error_msg, decompile_status
    except Exception as exc:
        err_msg = str(exc)
        if not silent_header:
            print(f"    [-] Decompilation failed: {err_msg}")
        return False, False, err_msg, {}


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
        scan_parser.add_argument("--php-version", type=int, choices=(72, 73, 74, 81, 82, 83, 84))
        scan_parser.add_argument("--loader-dll", type=Path)
        args = scan_parser.parse_args(sys.argv[2:])

        if not args.path.exists():
            print(f"Error: path not found: {args.path}", file=sys.stderr)
            return 1

        report = scan_project(args.path)
        print_scan_report(report, as_json=args.json)

        if args.decompile and report.encoded_count > 0:
            target_items = [f for f in report.encoded_files if f.match.name in ("ionCube", "SourceGuardian", "YAK Pro")]
            if target_items:
                decompile_failures = 0
                validation_failures = 0
                print(f"\n[*] Starting auto-decompilation of {len(target_items)} encoded/obfuscated file(s)...")
                for idx, f_info in enumerate(target_items, 1):
                    out_f = (args.output / f_info.relative_path) if args.output else f_info.path.with_name(f"{f_info.path.stem}.reconstructed.php")
                    print(f"[{idx}/{len(target_items)}] Decompiling: {f_info.relative_path} ... ", end="", flush=True)
                    ok, syn_ok, err, status = decompile_file(
                        f_info.path,
                        output_path=out_f,
                        php_version=args.php_version,
                        loader_dll=args.loader_dll,
                        silent_header=True,
                    )
                    if not ok:
                        decompile_failures += 1
                        st = f"FAILED: {err}"
                    elif not syn_ok:
                        validation_failures += 1
                        stage = "STRUCTURE" if status.get("structure", {}).get("ok") is False else "SYNTAX"
                        st = f"{stage} FAIL"
                    elif status.get("partial"):
                        st = f"PARTIAL: {_format_partial_status(status)}"
                    else:
                        st = "PASS"
                    print(f"[{st}]")
                return 1 if decompile_failures else (2 if validation_failures else 0)
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
    parser.add_argument("--php-version", type=int, choices=(72, 73, 74, 81, 82, 83, 84),
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
        success, syntax_ok, err, status = decompile_file(
            input_path,
            output_path=out_target,
            php_version=args.php_version,
            loader_dll=args.loader_dll,
        )
        return _result_exit_code(success, syntax_ok)

    # Directory mode
    print(f"\n" + "=" * 60)
    print(f"  IonCube / SourceGuardian Batch Directory Decompiler")
    print(f"  Source Directory : {input_path}")
    if args.output:
        print(f"  Target Directory : {args.output}")
    elif args.in_place:
        print(f"  Mode             : In-place overwrite (backups={not args.no_backup})")
    else:
        print(f"  Mode             : Generate *.reconstructed.php alongside files")
    print("=" * 60)

    # 1. Scan directory
    if args.no_copy_other:
        print("[*] Fast scanning PHP files (--no-copy-other enabled)...")
        target_files = [
            f for f in input_path.rglob("*.php")
            if f.is_file() and is_encoded_file(f)
        ]
        other_files = []
        all_files = target_files
    else:
        all_files = [f for f in input_path.rglob("*") if f.is_file()]
        target_files = [f for f in all_files if f.suffix == ".php" and is_encoded_file(f)]
        other_files = [f for f in all_files if f not in target_files]

    print(f"Found {len(all_files)} total file(s):")
    print(f"  - {len(target_files)} encoded/obfuscated PHP file(s) (ionCube / SourceGuardian / YAK Pro)")
    if not args.no_copy_other:
        print(f"  - {len(other_files)} non-protected / asset file(s)")

    if not target_files:
        print(f"\nNo encoded or obfuscated PHP files detected in: {input_path}")
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

    # 3. Decompile target files
    print(f"\n[*] Starting batch decompilation of {len(target_files)} file(s)...\n")
    start_time = time.time()
    results = []

    for idx, f in enumerate(target_files, 1):
        rel = f.relative_to(input_path)
        pct = (idx / len(target_files)) * 100

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

        print(f"[{idx}/{len(target_files)}] ({pct:5.1f}%) {rel} ... ", end="", flush=True)

        success, syntax_ok, err, status = decompile_file(
            f,
            out_file,
            php_version=args.php_version,
            loader_dll=args.loader_dll,
            silent_header=True,
        )

        if not success:
            print(f"[-] FAILED: {err}")
        elif not syntax_ok:
            stage = "STRUCTURE" if status.get("structure", {}).get("ok") is False else "SYNTAX"
            print(f"[!] {stage} FAIL")
        elif status.get("partial"):
            print(f"[~] PARTIAL ({_format_partial_status(status)}; validation: PASS)")
        else:
            print("[+] SUCCESS (validation: PASS)")

        results.append({
            "file": rel,
            "success": success,
            "valid": syntax_ok,
            "error": err,
            "status": status,
        })

    elapsed = time.time() - start_time

    # 4. Final summary report
    success_count = sum(1 for r in results if r["success"])
    validation_pass_count = sum(1 for r in results if r["valid"])
    failed_items = [r for r in results if not r["success"]]
    validation_failed_items = [r for r in results if r["success"] and not r["valid"]]
    partial_items = [r for r in results if r["success"] and r["status"].get("partial")]

    print("\n" + "=" * 60)
    print("  BATCH DECOMPILATION SUMMARY")
    print("=" * 60)
    print(f"  Total target files   : {len(target_files)}")
    print(f"  Successfully decoded : {success_count} / {len(target_files)}")
    print(f"  Validation Valid     : {validation_pass_count} / {success_count}")
    print(f"  Partial decodes      : {len(partial_items)}")
    if args.output and not args.no_copy_other:
        print(f"  Other files mirrored : {copied_count}")
    print(f"  Total time elapsed   : {elapsed:.2f}s")

    if validation_failed_items:
        print("\n  Validation Failures:")
        for it in validation_failed_items:
            stage = "STRUCTURE" if it["status"].get("structure", {}).get("ok") is False else "SYNTAX"
            print(f"    - [{stage}] {it['file']}")

    if partial_items:
        print("\n  Partial Files:")
        for it in partial_items:
            print(f"    - {it['file']}: {_format_partial_status(it['status'])}")

    if failed_items:
        print("\n  Failed Files:")
        for it in failed_items:
            print(f"    - {it['file']}: {it['error']}")
    print("=" * 60 + "\n")

    if failed_items:
        return 1
    if validation_failed_items:
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
