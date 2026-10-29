"""YAK Pro (Php Obfuscator 2.0.x) Static Deobfuscator.

Reverses YAK Pro source-level obfuscations:
1. Hex and octal escaped string literal obfuscation.
2. Control-flow flattening and statement shuffling (goto scramble).
3. Inverted guard condition recovery (if-goto -> structured if/else).
4. Loops (foreach, while, for), closures, and exception blocks (try/catch/finally).
5. Method-level and procedural scope deobfuscation.
6. Removal of dead code trampolines and unreferenced labels.
"""

from __future__ import annotations
import re
from pathlib import Path


def is_yakpro_obfuscated(code: str) -> bool:
    """Check if PHP code is obfuscated with YAK Pro."""
    header = code[:500]
    if "Obfuscated by YAK Pro" in header or "yakpro-po" in header:
        return True
    # Heuristic: multiple random labels with gotos and hex escape sequences
    if "goto " in code and ("\\x" in code or "\\0" in code or "\\1" in code):
        goto_count = len(re.findall(r"\bgoto\s+[a-zA-Z0-9_]+;", code))
        if goto_count >= 5:
            return True
    return False


def clean_strings(code: str) -> str:
    """Safely decode hex (\\xHH) and octal (\\OOO) character escape sequences.

    Leaves quote structures intact so nested interpolation like {$arr["key"]}
    does not suffer mismatched quote corruption.
    """
    def repl_hex(m: re.Match) -> str:
        code_point = int(m.group(1), 16)
        if 32 <= code_point <= 126:
            ch = chr(code_point)
            if ch in ('"', '$', '\\'):
                return '\\' + ch
            return ch
        if code_point == 10:
            return '\\n'
        if code_point == 13:
            return '\\r'
        if code_point == 9:
            return '\\t'
        return m.group(0)

    def repl_oct(m: re.Match) -> str:
        val_str = m.group(1)
        code_point = int(val_str, 8)
        if code_point > 255:
            # PHP octal overflow: \501 -> \50 ('(') followed by literal '1'
            val_str_2 = val_str[:2]
            rest = val_str[2:]
            code_point_2 = int(val_str_2, 8)
            ch2 = chr(code_point_2)
            if ch2 in ('"', '$', '\\'):
                ch2 = '\\' + ch2
            return ch2 + rest

        if 32 <= code_point <= 126:
            ch = chr(code_point)
            if ch in ('"', '$', '\\'):
                return '\\' + ch
            return ch
        if code_point == 10:
            return '\\n'
        if code_point == 13:
            return '\\r'
        if code_point == 9:
            return '\\t'
        return m.group(0)

    # Decode hex \xHH
    code = re.sub(r"\\x([0-9a-fA-F]{2})", repl_hex, code)
    # Decode octal \OOO
    code = re.sub(r"\\([0-7]{1,3})", repl_oct, code)
    return code


def strip_outer_negation(cond: str) -> tuple[str, bool]:
    """Strip outer negation !(...) only if parentheses match the entire expression."""
    cond = cond.strip()
    if not cond.startswith("!"):
        return cond, False
    if cond.startswith("!(") and cond.endswith(")"):
        depth = 0
        for i, c in enumerate(cond[1:]):
            if c == "(":
                depth += 1
            elif c == ")":
                depth -= 1
                if depth == 0:
                    if i == len(cond) - 2:
                        return cond[2:-1].strip(), True
                    break
    if cond.startswith("!") and not cond.startswith("!("):
        return cond[1:].strip(), True
    return cond, False


def quote_aware_brace_depth(text: str) -> int:
    """Calculate net brace depth while ignoring braces inside quotes and escape characters."""
    depth = 0
    in_quote = None
    escape = False
    for c in text:
        if escape:
            escape = False
            continue
        if c == "\\":
            escape = True
            continue
        if in_quote:
            if c == in_quote:
                in_quote = None
            continue
        if c in ("'", '"'):
            in_quote = c
            continue
        if c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
    return depth


def find_terminal_goto(chunk: str) -> tuple[str, str] | None:
    """Find an unconditional goto at brace depth 0 that terminates the basic block."""
    depth = 0
    in_quote = None
    escape = False
    for i, c in enumerate(chunk):
        if escape:
            escape = False
            continue
        if c == "\\":
            escape = True
            continue
        if in_quote:
            if c == in_quote:
                in_quote = None
            continue
        if c in ("'", '"'):
            in_quote = c
            continue
        if c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
        elif depth == 0:
            m = re.match(r"\bgoto\s+([a-zA-Z0-9_]+);?", chunk[i:])
            if m:
                stmt = chunk[:i].strip()
                target = m.group(1)
                return stmt, target
    return None


def get_block_successors(chunk: str, resolve_fn) -> list[str]:
    succs = []
    m_if = re.search(r"if\s*\((.*?)\)\s*\{\s*goto\s+([a-zA-Z0-9_]+);?\s*\}\s*goto\s+([a-zA-Z0-9_]+);?", chunk, re.DOTALL)
    if m_if:
        succs.append(resolve_fn(m_if.group(2)))
        succs.append(resolve_fn(m_if.group(3)))
        return succs
    term = find_terminal_goto(chunk)
    if term:
        succs.append(resolve_fn(term[1]))
        return succs
    return succs


def find_join_point(blocks: dict[str, str], resolve_fn, t: str, f: str) -> str | None:
    t = resolve_fn(t)
    f = resolve_fn(f)
    if not t or not f or t == f:
        return t

    reach_t = set()
    q = [t]
    while q:
        c = q.pop(0)
        if c in reach_t or c not in blocks:
            continue
        reach_t.add(c)
        for s in get_block_successors(blocks[c], resolve_fn):
            q.append(s)

    if f in reach_t:
        return f

    reach_f = set()
    q = [f]
    while q:
        c = q.pop(0)
        if c in reach_f or c not in blocks:
            continue
        reach_f.add(c)
        for s in get_block_successors(blocks[c], resolve_fn):
            q.append(s)

    if t in reach_f:
        return t

    common = reach_t & reach_f
    if common:
        q = [t]
        visited = set()
        while q:
            c = q.pop(0)
            if c in visited:
                continue
            visited.add(c)
            if c in common:
                return c
            for s in get_block_successors(blocks.get(c, ""), resolve_fn):
                q.append(s)
    return None


def deobfuscate_scope(code: str) -> str:
    """Deobfuscate a single self-contained CFG scope (function body or procedural script)."""
    m_pro = re.match(r"^(.*?)\bgoto\s+([a-zA-Z0-9_]+);", code, re.DOTALL)
    if not m_pro:
        return code

    prologue = m_pro.group(1).strip()
    entry_label = m_pro.group(2)
    rest = code[m_pro.end():]

    goto_targets = set(re.findall(r"\bgoto\s+([a-zA-Z0-9_]+);", rest))
    goto_targets.add(entry_label)

    pattern = r"(?<![:\w])(" + "|".join(re.escape(t) for t in sorted(goto_targets, key=len, reverse=True)) + r"):(?![:\w])"
    matches = list(re.finditer(pattern, rest))

    blocks: dict[str, str] = {}
    alias_map: dict[str, str] = {}

    split_counter = 0

    for i, m in enumerate(matches):
        lbl = m.group(1)
        start = m.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(rest)
        chunk = rest[start:end].strip()

        # Split block if it starts with scope closure brace and contains statements afterwards
        m_split = re.match(r"^(\}\s*(?:\)\s*)?;)\s*(.+)$", chunk, re.DOTALL)
        if m_split and not chunk.startswith("} catch") and not chunk.startswith("}catch") and not chunk.startswith("} finally") and not chunk.startswith("}finally"):
            split_counter += 1
            split_lbl = f"_synth_split_{split_counter}"
            blocks[lbl] = f"{m_split.group(1)} goto {split_lbl};"
            blocks[split_lbl] = m_split.group(2).strip()
        else:
            blocks[lbl] = chunk

        if not chunk and i + 1 < len(matches):
            alias_map[lbl] = matches[i + 1].group(1)
        else:
            m_direct = re.match(r"^goto\s+([a-zA-Z0-9_]+);?", chunk)
            if m_direct:
                alias_map[lbl] = m_direct.group(1)

    def resolve(l: str) -> str:
        visited = set()
        while l in alias_map and l not in visited:
            visited.add(l)
            l = alias_map[l]
        return l

    def walk_scope(start_lbl: str, stop_labels: set[str] | None = None, ancestors: set[str] | None = None, indent_level: int = 0):
        if stop_labels is None:
            stop_labels = set()
        if ancestors is None:
            ancestors = set()

        lines = []
        curr = resolve(start_lbl)
        visited = set()
        after_scope_lbl = None
        scope_suffix = ""

        ind = "    " * indent_level

        while curr and curr not in stop_labels and curr not in visited and curr not in ancestors and curr in blocks:
            visited.add(curr)
            curr_ancestors = ancestors | {curr}
            chunk = blocks[curr]

            # A. Scope closing block: } <suffix> goto <target>;
            if chunk.startswith("}"):
                if indent_level > 0:
                    if chunk.startswith("} catch") or chunk.startswith("}catch") or chunk.startswith("} finally") or chunk.startswith("}finally"):
                        after_scope_lbl = curr
                        break
                    m_after = re.search(r"^\}\s*(.*?)\s*\bgoto\s+([a-zA-Z0-9_]+);?", chunk, re.DOTALL)
                    if m_after:
                        scope_suffix = m_after.group(1).strip()
                        after_scope_lbl = resolve(m_after.group(2))
                        break
                    scope_suffix = chunk[1:].strip()
                    break
                else:
                    if chunk.strip() == "}":
                        break
                    term = find_terminal_goto(chunk)
                    if term:
                        stmt, tgt = term
                        if stmt:
                            lines.append(f"{ind}{stmt}")
                        curr = resolve(tgt)
                        continue
                    else:
                        m_after_goto = re.search(r"\bgoto\s+([a-zA-Z0-9_]+);?\s*$", chunk)
                        if m_after_goto:
                            stmt = re.sub(r"\bgoto\s+[a-zA-Z0-9_]+;\s*$", "", chunk).strip()
                            lines.append(f"{ind}{stmt}")
                            curr = resolve(m_after_goto.group(1))
                            continue
                        lines.append(f"{ind}{chunk}")
                        break

            # B. Try-catch block
            m_try = re.match(r"^(.*?\btry\b[^{]*?)\s*\{\s*goto\s+([a-zA-Z0-9_]+);?\s*$", chunk, re.DOTALL)
            if m_try:
                prefix = m_try.group(1).strip()
                try_start = resolve(m_try.group(2))
                try_lines, catch_block_lbl, _ = walk_scope(try_start, ancestors=curr_ancestors, indent_level=indent_level + 1)
                lines.append(f"{ind}{prefix} {{")
                lines.extend(try_lines)
                if catch_block_lbl and catch_block_lbl in blocks:
                    catch_chunk = blocks[catch_block_lbl]
                    m_catch_open = re.search(r"^\}\s*(catch\s*\(.*?\)\s*\{)\s*goto\s+([a-zA-Z0-9_]+);?", catch_chunk)
                    if m_catch_open:
                        catch_hdr = m_catch_open.group(1).strip()
                        catch_start = resolve(m_catch_open.group(2))
                        catch_lines, after_catch, _ = walk_scope(catch_start, ancestors=curr_ancestors, indent_level=indent_level + 1)
                        lines.append(f"{ind}}} {catch_hdr}")
                        lines.extend(catch_lines)
                        lines.append(f"{ind}}}")
                        curr = after_catch
                        continue
                    else:
                        m_term = find_terminal_goto(catch_chunk)
                        if m_term:
                            astmt, atgt = m_term
                            lines.append(f"{ind}{astmt}")
                            curr = resolve(atgt)
                            continue
                        else:
                            astmt = re.sub(r"\bgoto\s+[a-zA-Z0-9_]+;\s*$", "", catch_chunk).strip()
                            m_after_goto = re.search(r"\bgoto\s+([a-zA-Z0-9_]+);?\s*$", catch_chunk)
                            lines.append(f"{ind}{astmt}")
                            if m_after_goto:
                                curr = resolve(m_after_goto.group(1))
                                continue
                            break
                else:
                    lines.append(f"{ind}}}")
                    break

            # C. Scoped header block (foreach, while, for, function, closure, catch, finally)
            m_block_open = re.match(r"^(.*?\b(?:foreach|while|for|function|catch|finally)\b[^{]*?)\s*\{\s*goto\s+([a-zA-Z0-9_]+);?\s*$", chunk, re.DOTALL)
            if m_block_open:
                header = m_block_open.group(1).strip()
                inner_start = resolve(m_block_open.group(2))
                inner_lines, inner_after, inner_suffix = walk_scope(inner_start, ancestors=curr_ancestors, indent_level=indent_level + 1)
                lines.append(f"{ind}{header} {{")
                lines.extend(inner_lines)
                lines.append(f"{ind}}}{inner_suffix}")
                curr = inner_after
                continue

            # D. Conditional branch
            m_if = re.search(r"if\s*\((.*?)\)\s*\{\s*goto\s+([a-zA-Z0-9_]+);?\s*\}\s*goto\s+([a-zA-Z0-9_]+);?", chunk, re.DOTALL)
            if m_if:
                prefix = chunk[:m_if.start()].strip()
                if prefix:
                    lines.append(f"{ind}{prefix}")
                raw_cond = m_if.group(1).strip()
                l_else = resolve(m_if.group(2))
                l_then = resolve(m_if.group(3))

                stripped_cond, was_negated = strip_outer_negation(raw_cond)
                if was_negated:
                    real_cond = stripped_cond
                    true_target = l_then
                    false_target = l_else
                else:
                    real_cond = raw_cond
                    true_target = l_else
                    false_target = l_then

                join_pt = find_join_point(blocks, resolve, true_target, false_target)
                effective_stop = stop_labels | ({join_pt} if join_pt else set())

                then_stmts, then_after, then_suffix = walk_scope(true_target, stop_labels=effective_stop | {false_target}, ancestors=curr_ancestors, indent_level=indent_level + 1)
                else_stmts, else_after, else_suffix = walk_scope(false_target, stop_labels=effective_stop | {true_target}, ancestors=curr_ancestors, indent_level=indent_level + 1)

                clean_then = [s for s in then_stmts if s.strip()]
                clean_else = [s for s in else_stmts if s.strip()]

                if clean_then and clean_else:
                    lines.append(f"{ind}if ({real_cond}) {{")
                    lines.extend(clean_then)
                    lines.append(f"{ind}}} else {{")
                    lines.extend(clean_else)
                    lines.append(f"{ind}}}")
                elif clean_then:
                    lines.append(f"{ind}if ({real_cond}) {{")
                    lines.extend(clean_then)
                    lines.append(f"{ind}}}")
                elif clean_else:
                    lines.append(f"{ind}if (!({real_cond})) {{")
                    lines.extend(clean_else)
                    lines.append(f"{ind}}}")

                branch_exit = None
                branch_suffix = ""
                for b_after, b_suff in ((then_after, then_suffix), (else_after, else_suffix)):
                    if b_after and b_after in blocks and blocks[b_after].startswith("}"):
                        branch_exit = b_after
                        branch_suffix = b_suff
                        break

                if branch_exit:
                    after_scope_lbl = branch_exit
                    scope_suffix = branch_suffix
                    break

                curr = join_pt
                continue

            # E. Unconditional goto
            term = find_terminal_goto(chunk)
            if term:
                stmt, tgt = term
                target = resolve(tgt)
                if stmt:
                    lines.append(f"{ind}{stmt}")
                curr = target
                continue

            # F. Terminal statement
            lines.append(f"{ind}{chunk}")
            break

        return lines, after_scope_lbl, scope_suffix

    out_lines, after_lbl, top_suffix = walk_scope(entry_label)

    is_try_prologue = bool(re.search(r"\btry\s*\{$", prologue))
    if is_try_prologue and after_lbl and after_lbl in blocks:
        catch_chunk = blocks[after_lbl]
        if catch_chunk.startswith("}"):
            m_catch_open = re.search(r"^\}\s*(catch\s*\(.*?\)\s*\{)\s*goto\s+([a-zA-Z0-9_]+);?", catch_chunk)
            if m_catch_open:
                catch_hdr = m_catch_open.group(1).strip()
                catch_start = resolve(m_catch_open.group(2))
                catch_lines, after_catch, _ = walk_scope(catch_start)
                out_lines.append(f"}} {catch_hdr}")
                out_lines.extend(catch_lines)
                out_lines.append("}")
                after_lbl = after_catch
            else:
                astmt = re.sub(r"\bgoto\s+[a-zA-Z0-9_]+;\s*$", "", catch_chunk).strip()
                m_after_goto = re.search(r"\bgoto\s+([a-zA-Z0-9_]+);?\s*$", catch_chunk)
                out_lines.append(astmt)
                after_lbl = resolve(m_after_goto.group(1)) if m_after_goto else None
    else:
        p_depth = quote_aware_brace_depth(prologue)
        if p_depth > 0:
            closing = "}" + (top_suffix if top_suffix else "")
            out_lines.append(closing)
            p_depth -= 1
            while p_depth > 0:
                out_lines.append("}")
                p_depth -= 1

    while after_lbl and after_lbl in blocks:
        after_lines, next_after, _ = walk_scope(after_lbl)
        out_lines.extend(after_lines)
        if next_after == after_lbl:
            break
        after_lbl = next_after

    full = (prologue + "\n\n" if prologue else "") + "\n".join(out_lines) + "\n"
    # Remove dead standalone labels
    full = re.sub(r"^\s*[a-zA-Z0-9_]+:\s*$", "", full, flags=re.MULTILINE)
    # Remove inline labels: e.g. `label: }`
    full = re.sub(r"\b[a-zA-Z0-9_]+:\s*(?=[;}])", "", full)
    return full


def deobfuscate_yakpro(raw_code: str) -> str:
    """Deobfuscate YAK Pro PHP source code into clean, structured PHP."""
    code = clean_strings(raw_code)

    # Check if this file contains class/trait/interface/enum definitions
    has_class = bool(re.search(r"\b(?:class|trait|interface|enum)\s+[a-zA-Z0-9_]+", code))

    if not has_class:
        # Procedural script (e.g. functions.php, bg_get.php, index.php)
        res = deobfuscate_scope(code)
        res = re.sub(r"\bgoto\s+[a-zA-Z0-9_]+;\s*", "", res)
        return res

    # Class file: deobfuscate each method/function individually
    pattern = re.compile(
        r"((?:(?:public|private|protected|static|final|abstract)\s+)*function\s+&?[a-zA-Z0-9_]+\s*\([^)]*\)(?:\s*:\s*[^{]+)?\s*\{)"
    )

    out = []
    last_pos = 0
    for m in pattern.finditer(code):
        if m.start() < last_pos:
            continue
        sig = m.group(1)
        body_start = m.start() + len(sig) - 1
        depth = 0
        in_quote = None
        escape = False
        body_end = None
        for i in range(body_start, len(code)):
            c = code[i]
            if escape:
                escape = False
                continue
            if c == "\\":
                escape = True
                continue
            if in_quote:
                if c == in_quote:
                    in_quote = None
                continue
            if c in ("'", '"'):
                in_quote = c
                continue
            if c == "{":
                depth += 1
            elif c == "}":
                depth -= 1
                if depth == 0:
                    body_end = i + 1
                    break
        if body_end is None:
            continue
        raw_body = code[body_start + 1 : body_end - 1]

        # Check if raw_body has any gotos
        m_goto = re.search(r"\bgoto\s+([a-zA-Z0-9_]+);", raw_body)
        if m_goto:
            prologue = raw_body[:m_goto.start()].strip()
            rest_body = raw_body[m_goto.start():]
            mini_code = "<?php\n" + (prologue + "\n" if prologue else "") + rest_body + "\n"
            clean_body = deobfuscate_scope(mini_code)
            clean_body = re.sub(r"^<\?php\s*", "", clean_body).strip()
            clean_body = re.sub(r"\bgoto\s+[a-zA-Z0-9_]+;\s*", "", clean_body)
            method_depth = 1 + quote_aware_brace_depth(clean_body)
            closing = "\n" + ("}\n" * method_depth) if method_depth > 0 else "\n"
            out.append(code[last_pos : body_start + 1])
            out.append("\n" + clean_body + closing)
        else:
            out.append(code[last_pos:body_end])
        last_pos = body_end

    out.append(code[last_pos:])
    return "".join(out)


def deobfuscate_file(input_path: Path, output_path: Path | None = None) -> tuple[bool, str]:
    """Deobfuscate a single YAK Pro PHP file."""
    try:
        raw_code = input_path.read_text(encoding="utf-8", errors="ignore")
        if not is_yakpro_obfuscated(raw_code):
            return False, "Not identified as YAK Pro obfuscated file"

        clean_code = deobfuscate_yakpro(raw_code)
        target = output_path or input_path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(clean_code, encoding="utf-8")
        return True, ""
    except Exception as e:
        return False, str(e)
