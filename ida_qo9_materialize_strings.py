"""Materialize decoded ionCube/Qo9 strings into an IDA Strings-visible segment.

This script is meant to be run inside IDA Python.

It scans encoded Qo9 strings, creates a new synthetic IDB segment named QO9STR,
writes the decoded strings there as normal NUL-terminated C strings, and adds
comments on both the original encoded location and the materialized string.

The original binary bytes are not patched by default. If you really want decoded
strings in place, set PATCH_ORIGINAL_IN_PLACE=True, but that is intentionally
off because it destroys the original encoded representation inside the IDB.
"""

from __future__ import annotations

import json
import os
import re
from typing import Any

import ida_bytes
import ida_ida
import ida_kernwin
import ida_name
import ida_nalt
import ida_segment
import ida_strlist
import ida_xref
import idaapi
import idc


# The classic Qo9 format used by ic_qo9_decode_len16 / sub_44B747.
KEY_QO9_16 = bytes.fromhex("25 68 D3 C2 28 F2 59 2E 94 EE F2 91 AC 13 96 95")

# The sibling format used by ic_qo9_decode_xor48_32 / sub_44B875.
KEY_XOR48_32 = bytes.fromhex(
    "48 17 AE 06 91 CC 73 2C 6C 58 4B 6C 2B 8B F3 6C "
    "7D F0 60 17 81 4A 23 0D 69 57 21 76 75 DD D1 DE"
)


# Config. You can override these globals before exec() if needed.
SCAN_SEGMENTS = (".text", ".rdata", ".data")
ENABLED_CODECS = ("qo9_16", "qo9_32_xor48")
SEGMENT_NAME = "QO9STR"
MIN_LEN = 2
MAX_LEN = 254
MIN_PRINTABLE_RATIO = 0.88
XOR48_REQUIRE_XREF = True
PATCH_ORIGINAL_IN_PLACE = False
RENAME_ORIGINALS = False
ADD_XREFS_TO_DECODED = True
COMMENT_CALLSITES = True
MAX_HITS = 0  # 0 = no limit
OUT_JSON = "ida_qo9_materialized.json"

INTERESTING_RE = re.compile(
    r"(dynamic|dynamickey|key|cipher|encrypt|decrypt|random|basic|rijndael|"
    r"default|ioncube|blowfish|cast|des|sha|md5|license|encode|decode|"
    r"iv|salt|seed|php)",
    re.IGNORECASE,
)


PRINTABLE = bytes(
    1 if b in (9, 10, 13) or 32 <= b < 127 else 0
    for b in range(256)
)


def align_up(value: int, alignment: int) -> int:
    return (value + alignment - 1) & ~(alignment - 1)


def short_text(text: str, limit: int = 120) -> str:
    text = text.replace("\r", "\\r").replace("\n", "\\n")
    if len(text) <= limit:
        return text
    return text[: limit - 3] + "..."


def safe_name(text: str) -> str:
    text = re.sub(r"[^0-9A-Za-z_]+", "_", text)
    text = re.sub(r"_+", "_", text).strip("_")
    if not text:
        text = "str"
    if text[0].isdigit():
        text = "s_" + text
    return text[:48]


def printable_ratio(data: bytes) -> float:
    if not data:
        return 0.0
    good = 0
    for b in data:
        good += PRINTABLE[b]
    return good / len(data)


def has_dref_to(ea: int) -> bool:
    return ida_xref.get_first_dref_to(ea) != idaapi.BADADDR


def function_name(ea: int) -> str:
    fn = idaapi.get_func(ea)
    if not fn:
        return ""
    return idc.get_func_name(fn.start_ea) or f"sub_{fn.start_ea:X}"


def collect_xrefs(ea: int, limit: int = 8) -> list[dict[str, str]]:
    refs = []
    xr = ida_xref.get_first_dref_to(ea)
    while xr != idaapi.BADADDR and len(refs) < limit:
        refs.append(
            {
                "ea": f"0x{xr:X}",
                "function": function_name(xr),
                "disasm": idc.generate_disasm_line(xr, 0) or "",
            }
        )
        xr = ida_xref.get_next_dref_to(ea, xr)
    return refs


def decode_qo9_16(raw: bytes) -> tuple[bytes, bool]:
    if not raw:
        return b"", False
    length = raw[0]
    if length < MIN_LEN or length > MAX_LEN or len(raw) < length + 2:
        return b"", False
    # Fast terminator check: decoded terminator must be zero.
    if raw[length + 1] != KEY_QO9_16[(2 * length) & 0xF]:
        return b"", False
    out = bytearray(length)
    for i in range(1, length + 1):
        out[i - 1] = KEY_QO9_16[(length - 1 + i) & 0xF] ^ raw[i]
    return bytes(out), True


def decode_xor48_32(raw: bytes) -> tuple[bytes, bool]:
    if not raw:
        return b"", False
    length = raw[0] ^ 0x48
    if length < MIN_LEN or length > MAX_LEN or len(raw) < length + 1:
        return b"", False
    out = bytearray(length)
    for i in range(1, length + 1):
        out[i - 1] = KEY_XOR48_32[(i + length) & 0x1F] ^ raw[i]
    return bytes(out), True


def iter_segments() -> list[tuple[int, int, str]]:
    wanted = set(globals().get("QO9_SCAN_SEGMENTS", SCAN_SEGMENTS))
    ranges = []
    for i in range(ida_segment.get_segm_qty()):
        seg = ida_segment.getnseg(i)
        if not seg:
            continue
        name = ida_segment.get_segm_name(seg) or ""
        if name in wanted or name.lower() in {x.lower() for x in wanted}:
            ranges.append((seg.start_ea, seg.end_ea, name))
    return ranges


def candidate_codecs(first_byte: int) -> tuple[tuple[str, int, int, Any], ...]:
    return (
        ("qo9_16", first_byte, 2, decode_qo9_16),
        ("qo9_32_xor48", first_byte ^ 0x48, 1, decode_xor48_32),
    )


def scan_hits() -> list[dict[str, Any]]:
    enabled = set(globals().get("QO9_ENABLED_CODECS", ENABLED_CODECS))
    max_hits = int(globals().get("QO9_MAX_HITS", MAX_HITS))
    hits: list[dict[str, Any]] = []

    for start, end, seg_name in iter_segments():
        buf = ida_bytes.get_bytes(start, end - start) or b""
        limit = len(buf)
        off = 0
        while off < limit:
            for codec, length, extra, decoder in candidate_codecs(buf[off]):
                if codec not in enabled:
                    continue
                if not (MIN_LEN <= length <= MAX_LEN and off + length + extra <= limit):
                    continue
                ea = start + off
                if codec == "qo9_32_xor48" and globals().get("QO9_XOR48_REQUIRE_XREF", XOR48_REQUIRE_XREF):
                    if not has_dref_to(ea):
                        continue

                raw = buf[off : off + length + extra]
                decoded, ok = decoder(raw)
                if not ok:
                    continue
                ratio = printable_ratio(decoded)
                if ratio < MIN_PRINTABLE_RATIO:
                    continue
                text = decoded.decode("utf-8", "replace")
                if not text.strip():
                    continue
                alnum = sum(1 for ch in text if ch.isalnum())
                interesting = bool(INTERESTING_RE.search(text))
                if not alnum and not interesting:
                    continue

                refs = collect_xrefs(ea)
                hits.append(
                    {
                        "orig_ea": ea,
                        "orig_ea_hex": f"0x{ea:X}",
                        "segment": seg_name,
                        "codec": codec,
                        "length": length,
                        "text": text,
                        "interesting": interesting,
                        "xrefs": refs,
                    }
                )
                if max_hits and len(hits) >= max_hits:
                    return hits
            off += 1

    hits.sort(key=lambda item: (item["orig_ea"], item["codec"], item["text"]))
    return hits


def unique_segment_name(base_name: str) -> str:
    existing = {
        ida_segment.get_segm_name(ida_segment.getnseg(i))
        for i in range(ida_segment.get_segm_qty())
    }
    if base_name not in existing:
        return base_name
    idx = 1
    while f"{base_name}{idx}" in existing:
        idx += 1
    return f"{base_name}{idx}"


def create_output_segment(total_size: int) -> tuple[int, str]:
    start = align_up(ida_ida.inf_get_max_ea() + 0x1000, 0x1000)
    end = start + align_up(total_size, 0x1000)
    name = unique_segment_name(globals().get("QO9_SEGMENT_NAME", SEGMENT_NAME))
    if not ida_segment.add_segm(0, start, end, name, "DATA"):
        raise RuntimeError(f"Could not create segment {name} at 0x{start:X}..0x{end:X}")
    seg = ida_segment.getseg(start)
    if seg:
        ida_segment.set_segm_class(seg, "DATA")
    return start, name


def materialize_hits(hits: list[dict[str, Any]]) -> list[dict[str, Any]]:
    total_size = 1
    encoded_strings = []
    for hit in hits:
        raw = hit["text"].encode("utf-8", "replace") + b"\x00"
        encoded_strings.append(raw)
        total_size += len(raw)

    base, seg_name = create_output_segment(total_size)
    cur = base
    materialized = []
    patch_original = bool(globals().get("QO9_PATCH_ORIGINAL_IN_PLACE", PATCH_ORIGINAL_IN_PLACE))
    rename_originals = bool(globals().get("QO9_RENAME_ORIGINALS", RENAME_ORIGINALS))
    add_xrefs_to_decoded = bool(globals().get("QO9_ADD_XREFS_TO_DECODED", ADD_XREFS_TO_DECODED))
    comment_callsites = bool(globals().get("QO9_COMMENT_CALLSITES", COMMENT_CALLSITES))

    for idx, (hit, raw) in enumerate(zip(hits, encoded_strings)):
        dst_ea = cur
        ida_bytes.patch_bytes(dst_ea, raw)
        idc.create_strlit(dst_ea, dst_ea + len(raw))
        name = f"qo9_{hit['orig_ea']:08X}_{hit['codec']}_{safe_name(hit['text'])}"
        ida_name.set_name(dst_ea, name, ida_name.SN_FORCE)

        display = short_text(hit["text"])
        callers = sorted({ref["function"] or ref["ea"] for ref in hit.get("xrefs", [])})
        caller_text = ", ".join(callers) if callers else "no xrefs"
        ida_bytes.set_cmt(
            dst_ea,
            f"Decoded Qo9 string from {hit['orig_ea_hex']} ({hit['codec']}); callers: {caller_text}",
            1,
        )
        ida_bytes.set_cmt(
            hit["orig_ea"],
            f'DECODED_QO9 {hit["codec"]} -> {seg_name}:0x{dst_ea:X}: "{display}"',
            0,
        )

        if rename_originals:
            ida_name.set_name(
                hit["orig_ea"],
                f"enc_qo9_{hit['orig_ea']:08X}_{idx}",
                ida_name.SN_FORCE | ida_name.SN_LOCAL,
            )

        if add_xrefs_to_decoded:
            for ref in hit.get("xrefs", []):
                ref_ea = int(ref["ea"], 16)
                ida_xref.add_dref(ref_ea, dst_ea, ida_xref.dr_O)
                if comment_callsites:
                    ida_bytes.set_cmt(ref_ea, f'DECODED_QO9: "{display}"', 0)

        if patch_original:
            ida_bytes.patch_bytes(hit["orig_ea"], raw)
            idc.create_strlit(hit["orig_ea"], hit["orig_ea"] + len(raw))

        item = dict(hit)
        item["decoded_ea"] = dst_ea
        item["decoded_ea_hex"] = f"0x{dst_ea:X}"
        item["decoded_segment"] = seg_name
        materialized.append(item)
        cur += len(raw)

    return materialized


def default_out_json() -> str:
    if "QO9_OUT_JSON" in globals():
        return globals()["QO9_OUT_JSON"]
    if "QO9_OUT_DIR" in globals():
        return os.path.join(globals()["QO9_OUT_DIR"], OUT_JSON)
    return os.path.join(os.getcwd(), OUT_JSON)


def refresh_ida_views() -> None:
    try:
        ida_strlist.clear_strlist()
        ida_strlist.build_strlist()
    except Exception:
        pass
    try:
        ida_kernwin.refresh_idaview_anyway()
    except Exception:
        pass


def main() -> dict[str, Any]:
    hits = scan_hits()
    materialized = materialize_hits(hits)
    out_json = default_out_json()
    os.makedirs(os.path.dirname(out_json), exist_ok=True)
    with open(out_json, "w", encoding="utf-8") as f:
        json.dump(materialized, f, indent=2, ensure_ascii=False)

    refresh_ida_views()
    result = {
        "input_file": idaapi.get_input_file_path(),
        "scan_segments": list(globals().get("QO9_SCAN_SEGMENTS", SCAN_SEGMENTS)),
        "enabled_codecs": list(globals().get("QO9_ENABLED_CODECS", ENABLED_CODECS)),
        "hits": len(hits),
        "materialized": len(materialized),
        "out_json": out_json,
        "patch_original_in_place": bool(globals().get("QO9_PATCH_ORIGINAL_IN_PLACE", PATCH_ORIGINAL_IN_PLACE)),
        "add_xrefs_to_decoded": bool(globals().get("QO9_ADD_XREFS_TO_DECODED", ADD_XREFS_TO_DECODED)),
        "comment_callsites": bool(globals().get("QO9_COMMENT_CALLSITES", COMMENT_CALLSITES)),
    }
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return result


if __name__ == "__main__":
    main()
