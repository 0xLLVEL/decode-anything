# ionCube 7.4 — static decode status

Target: decode an ionCube-encoded PHP 7.4 file with no PHP process, no loader and
no opcode-dump extension. The 7.2 equivalent is `docs/ioncube-72-static.md`; this
document covers what the 7.4 build gives up statically and what is still masked.

Sample and oracle: `loader/refs/ic74dump-opcodes/contacts.php` (encoder 15.0.1,
`php_version_code = 74`) plus `contacts.opcodes.json`, produced by the 32-bit
runtime dumper and holding 113 op_arrays (1 `main`, 112 class methods).

## Runtime (when a dump is needed)

`loader/php74-nts-x64/` — PHP 7.4.33 NTS VC15 x64, fetched from
`https://windows.php.net/downloads/releases/archives/`:

| Item | File |
|---|---|
| interpreter | `php-7.4.33-nts-Win32-vc15-x64.zip` → `loader/php74-nts-x64/` |
| headers + `php7.lib` | `php-devel-pack-7.4.33-nts-Win32-vc15-x64.zip` → `loader/php74-nts-x64/dev/` |
| loader | `loader/ioncube_loader_win_7.4.dll` (x64, v15.5.1, build id `API20190902,NTS,VC15`) |

`php74-nts-x64/php.ini` points `extension_dir` at the local `ext/`, which holds a
copy of the loader:

```bash
./loader/php74-nts-x64/php.exe -c loader/php74-nts-x64/php.ini -v
#  with the ionCube PHP Loader v15.5.1
```

Both the 7.2 and 7.4 loaders in `loader/` are PE32+ x86-64, so this runtime is the
matching host; the `loader/refs/ic74dump-opcodes/runtime` bundle is the 32-bit
one and cannot load them.

## Loader map (`ioncube_loader_win_7.4.dll`)

Read with REA against a live IDA 9.0 session (`rea analyze|decompile|search|xrefs
--provider ida`, registration file `scratch/rea-ida.json`).

| Item | Value |
|---|---|
| Build | 15.5.1, PE32+ x86-64, image base `0x180000000`, `SizeOfImage 0x1d5000` |
| `zend_extension_entry` | `0x1801bfe30` (name `ionCube Loader` at `+0x00`, `+0x38` → `15.5.1`, `+0x80` → `API20190902,NTS,VC15`) |
| startup / shutdown | `0x18006d3b0` / `0x18006d680` |
| activate / deactivate | `0x18006d6b0` / `0x18006d6d0` |
| message handler | `0x18006cfb0` |
| MINIT tail | `0x18006d4d9`..`0x18006d660` — registers `ION_CORRUPT_FILE`, `ION_EXPIRED_FILE`, … as long constants |
| internal build name | `0x1801bb226` → `ioncube_loader_15.5_7.4.0_nonts.dll` |
| declared handlers | `op_array_handler`, `statement_handler`, `op_array_ctor`, `op_array_dtor` are all zero in the entry |

The 7.2 RVA shortcuts (`0x18007ba00` header parser, `0x1800a02a0` record walker in
the 7.2 build) do **not** carry over: the 7.4 build is a different compilation and
the same RVA lands in an unrelated `dirname` helper. Anchor on the extension entry
and on data, not on 7.2 addresses.

## Container layer — solved

`engines/ioncube/header.py` decodes the 7.4 payload unchanged; `tools/ic72_static_container.py`
already reports it:

```
decoded_version             0x4FF571B7
md4_matches                 True
transition_checksum_matches True
all_frame_checksums_match   True
inflate_eof                 True
header_size                 172
body_offset                 227
body_size                   398440
php_version_code            74
encoder                     15.0.1
```

That is the same four gates the loader runs before it ever looks at bytecode, so
the container layer needs no 7.4-specific work.

## Body layer — structure solved, opcode stream open

Encoder 15.x no longer uses the 12.0 record framing that `tools/ic72_record_walk.py`
expects (`resync()` finds 32 bogus records and then desynchronises). What it does
use is a flat image where each op_array is written as:

```
name              NUL-terminated ASCII identifier
+0x04             u32 == 2
+0x08             u32 record mark: (word >> 16) & 0xFF == 0x02,
                  word & 0xFF in {1, 4}   (0x42020001, 0x02020001, 0x42020004)
```

and the field block, with offsets measured from the first byte after the name:

| Offset | Field | Verified against |
|---|---|---|
| `+0x28` | opcode count | `len(opcodes)` |
| `+0x30` | local variables | `last_var` |
| `+0x34` | temp variables | `T` |
| `+0x54` | first source line | `line_start` |
| `+0x58` | last source line | `line_end` |
| `+0x60` | literal count | `len(literals)` |

All six agree for **112/112** named op_arrays in the sample, with no extra records
invented by the scan. That is the whole of `tools/ic74_static_dump.py` today:

```bash
python tools/ic74_static_dump.py loader/refs/ic74dump-opcodes/contacts.php \
  --truth loader/refs/ic74dump-opcodes/contacts.opcodes.json
# entry_count 112, matched 112, mismatched 0, missing 0, extra 0
```

Class records are separate and cleaner: `02 00 02 00 02`, a u32 length, then the
class name — the sample has one, `ModelMarketingContacts`, and the runtime dump's
`class_index` also carries `Model` as an alias recorded right after it.

### The record builder (`sub_180097AA0`)

The scan above finds records but never reads their instructions. The function that
turns a record into a `zend_op_array` is reachable now:

| Step | Address | Role |
|---|---|---|
| compiler hook | `0x1800987C0` | per-op_array entry, called from the compile path |
| stream feeder | `0x180098570` | allocates the mask array for the record |
| record builder | `0x180097AA0` | decodes words into 32-byte op records |
| mask generator candidates | `0x1800953A3`, `0x1800953E0` | 7.2's two-word multiply-add, same constants |
| generator state init | `0x180095380` | `state[0]=s0`, `state[1]=s1` |
| string/mask decryptor | `0x180001F40` | seeded keystream XOR over a buffer |

`sub_180097AA0(ctx, op_array, stream)` walks the word array one entry per
instruction. With `ctx->encoder_major >= 6` and `ctx->php_minor >= 74` (both true
here) every instruction consumes **two** words:

```
v21  = words[i++]                 # opcode word
rec.qword0 = words[i++]           # 7.4-only extended word (stored at +0x00)
raw  = v21 & 0xFF                 # stored opcode byte
```

and the rest of the word is handed out by bit:

| Bits of `v21` | Meaning | Record slot |
|---|---|---|
| `0x100` | aux group present | `+0x31` tag, `+0x10..13` payload (5 bytes) |
| `0x200` | aux group present | `+0x29` tag, `+0x08..0B` payload (5 bytes) |
| `0x400` | aux group present | `+0x30` tag, `+0x0C..0F` payload (5 bytes) |
| `0x1800 == 0x0800` | cache slot | `+0x14 = 1` |
| `0x1800 == 0x1000` | cache slot | `+0x14 = 60` |
| `0x1800 == 0x1800` | cache slot | `+0x14 =` next word |
| `0x8000` file flag | line suppressed | `+0x18 = 0` |
| else | line | `+0x18 = v21 >> 16`, or next word when that is `0xFFFF` |

So the record is 32 bytes per instruction: `+0x00` extended qword, `+0x08` /
`+0x0C` / `+0x10` the three aux payloads, `+0x14` cache slot, `+0x18` line,
`+0x1C` the stored opcode byte.

### The opcode mask

The stored byte is not the opcode. `sub_180098570` allocates **`ops + 1` dwords**
of mask material and the builder XORs the byte at `mask[op_index]` into the
opcode twice (once inside the `ctx->flags & 0x80` block, once unconditionally for
`encoder_major >= 6`), with the 7.2 escape still in place:

```
if (raw == (mask[i] ^ 0x95)) mask[i] = 0     # slot decodes to the stored byte
opcode = raw ^ mask[i]                       # after the escape, ^ mask[i] again
```

The mask values are **read from the program stream**, not generated: the slots
come from `sub_180094B40`, which pulls one value from the record's byte stream
and XORs its low byte with a byte of a wrapping keystream table
(`reader+0x30` pointer, `+0x38` length, `+0x40` cursor). The bytes of that dword
array are the per-slot mask, i.e. slot `i` is the byte at index `i` of the
stream — the same `0x95`-guarded byte-cursor scheme the 7.2 loader uses.

The same two-word multiply-add generator as 7.2 does exist in this build
(`0x1800953A3`, constants `0x7689` / `0x4650`, `ROL32(s1,16) + s0`, then
`^ bytecode_xor_key` at `0x1800953E0`), but on the 7.4 path it is only reached
through `sub_180001F40`, the seeded buffer decryptor — not for the opcode mask.

### What is still masked

The instruction stream starts at `+0x90` and is **not** plain Zend words. For
`getTotalSendGroups` (12 ops, record span 1067 bytes) the first 48 bytes are:

```
c2 07 00 00  69 c5 6a 53  5b 0f 00 00  1b 90 6f 74
ee 1f 00 00  43 a9 2d 15  14 00 00 00  9b 07 00 00
40 c7 f9 48  6a 07 00 00  c8 5e 5e 0d  b6 07 00 00
```

Small counters alternate with high-entropy dwords, i.e. the same split the 7.2
build shows: a per-op key array plus XOR-masked opcode bytes (`0x95` is the "no
key" escape there, and `sub_18009E8B0` XORs by op index). The 7.4 side of that
split is `sub_180097AA0`, mapped above: the counters are opcode words, the
high-entropy dwords are the 7.4-only extended word of each instruction, and the
mask that turns one into the other is still to be located in the stream, so
`tools/ic74_static_dump.py` deliberately reports structure only.

## Open items, in order

1. Pin the stream offset of the mask dwords. The builder's algorithm is fully
   known; what is left is where in the record `sub_180098570` starts reading its
   `ops + 1` values, and whether the wrapping keystream table it XORs them with
   is the decrypted header or a per-record table. Cross-check: slot bytes
   recovered from `contacts.opcodes.json` (`raw ^ opcode`) must show up in the
   body once that keystream is applied.
2. Port the word grammar into `tools/ic74_static_dump.py` (`--opcodes`), using
   the table above, and verify that the parse lands exactly on the record's
   literal table for all 112 entries.
3. Feed the result into `engines/ioncube/adapter.py` as an `icdump-ir-v1`
   document so `decompile.py` can run without the runtime bundle.

## Tooling in this repo

| Tool | Use |
|---|---|
| `tools/ic74_static_dump.py` | container + body + op_array field block, `--truth` diff |
| `tools/ic74_rea.py` | thin `rea --format json` wrapper that caches each IDA answer under `scratch/ida74/` |
| `scratch/ida74/f_builderA.c` | decompiler output for the record builder, kept as evidence |
| `scratch/ida_start_mcp.py` | starts the ida-pro-mcp plugin server without the menu (IDA `-S` script) |
