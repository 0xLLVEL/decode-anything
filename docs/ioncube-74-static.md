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

### The reader chain around it

The functions that sit on the same path, read in this order:

| Address | Role |
|---|---|
| `0x180098FC0` | per-record entry: allocates the 80-byte op_array wrapper, reads the 4-byte header word plus a length-prefixed string, then branches |
| `0x180098C50` | reads a `u16` length, then that many bytes, interned as a `zend_string` |
| `0x1800974B0` | reads the word count and the aux count, allocates `4 * words` and `5 * aux` |
| `0x1800982A0` | static-variable and literal fixups over the record |
| `0x180098D20` | class-only variant (`0x8000` header flag): sets `__construct`, class flags |
| `0x180097AA0` | the word decoder |

So the record carries two parallel arrays, the word block and the 5-byte aux
block, plus a length-prefixed string (the doc comment) ahead of the field block.

### The opcode mask — found

The stored byte is not the opcode. `sub_180098570` allocates **`ops + 1` words**
of mask material and the builder reads **two different bytes of it** per
instruction, both from the same byte cursor:

```
raw    = word & 0xFF                              # stored opcode byte
A      = mask array, bytes 0 .. 4*(ops+1)-1
second = A[i + ops + 0x02]                        # 0x180097d00
if raw == (second ^ 0x95): A[i] = 0               # 7.2 escape, now on A[i]
opcode = raw ^ A[i] ^ second                      # major >= 6: two XORs
```

The `+0x02` in that index is the only per-file constant in it
(`ctx->encoder_major >= 6` takes the two-XOR branch; the second index is
`i + ops + *(ctx->info + 192)`). So what a record hides is the xor of two bytes
of one generated stream, `A[i] ^ A[i + ops + 2]`, and the mask array is
4 * (ops + 1) bytes long because the two reads overlap.

That stream **is** the 7.2 two-word multiply-add generator
(`0x180095390` / `0x1800953E0`, constants `0x7689` / `0x4650`,
`ROL16(s1) + s0`, then `^ bytecode_xor_key`), and the pair it starts from is
stored in the body. For `getTotalSendGroups` the pair sits at body `0x2447`:

```
0x2447   b0 1b 00 00   ea 59 00 00        s0 = 0x1BB0, s1 = 0x59EA
0x24b8   "gettotalsendgroups"             record
0x255b   word block
```

and `mask_stream(0x1BB0, 0x59EA, 0x00363FA4)` reproduces all twelve opcodes
(`52 70 63 0a 04 74 3c 02 52 51 3e 3e`) with no runtime at all. The twelve
hidden bytes are still `90 2b 8d 91 6e c2 b7 8a 1a d4 c2 b2`, but they are the
xor of two stream bytes, which is why no window of the stream ever contains
them and why their distribution is flat.

Measured over the whole sample (`tools/ic74_mask.py --truth`): **92 of 112**
records decode from a pair stored in the body before the record, every masked
byte included. The pair is not at a fixed distance — it sits anywhere in the
113..1400 bytes ahead of the record, which is what a `--window 1400` search
covers.

Every recovered pair sits in a block of its own shape, embedded in the preceding
record's tail rather than in the record's own header:

```
0x2443   X        89 03 00 00      905
0x2447   k1       b0 1b 00 00      0x1BB0
0x244b   k2       ea 59 00 00      0x59EA
0x244f            00 00 00 00 00 00 00 00   (eight zero bytes)
```

`X` is not the distance to the name (`0x24b8 - 0x2443 = 117` for this record,
`0x28e3 - 0x2854 = 143` for `delSendGroup`), so the block is not a record header;
it is a key block the writer emits as part of the surrounding record's data.
Recovered `X` values include 905, 906, 926, 1036, 1056, 1384, 1858, 2167, 2500,
3076, 3173.

The other 20 are pinned by name in `tests/test_ic74_static_dump.py` (`MISSES`):
`editSendGroup`, `addNewsletters`, `getEmailsFromSqlManual`, `getTotalNewsletters`,
`saveEmailsToCron`, `getCronLogs`, `getMessageSend`, `getCompleteDataSend`,
`getProductsToSend`, `delViewsSend`, `getEmailCustomers`, `getClients`,
`getEmailsByOrdereds`, `getShopCountries`, `getTemplates`, `addTemplate`,
`markEmailReqreview`, `getPurchasedsProducts`, `installMailpro`, `getLicense`.

Ruled out by measurement (each probe run on the misses, most on all of them):

| Probe | Result |
|---|---|
| any dword pair in the 398,440-byte body, double xor, every shift `0..2*ops+8` | none |
| any dword pair in the whole 186,438-byte file | none |
| any adjacent pair anywhere, single xor (contiguous byte window) | none |
| pairs at stride 8/12/16/20/24/32 (non-adjacent dwords) | none |
| any `[x][a][b]` triple with all three below `0x100000` (75,636 of them) | none |
| 16-bit pairs (`u16`,`u16`) packed anywhere in the body | none |
| stepping a hit record's state, then any shift `0..2000` | none |
| the seed pair of any of the other 92 records, both orders | none |
| regenerating from each hit seed and searching 40,000 bytes | none |
| keys `0`, `owner_key`, `bytecode_xor_key ^ owner_key` | none |
| MT4IC from the body head, header keys, or ±300 dwords around the record | none |
| seeds = `sub_1800076E0` / `sub_180007730` over the name, name+NUL, name+key | none |

So the mask for those records is produced from state that is neither stored nor a
hash of the record's own fields, while the record layout, block start and word
grammar are all confirmed correct for them (their literal counts land exactly on
the table boundary after the walk, same as the hits). The writer branch that
emits the `[X][k1][k2]` block is therefore the place to look: it must have a
second path for the 20.

On the reader side two generators exist for these states, `sub_1800955E0(kind)`:
kind 4 is a 624-word MT19937 pool seeded through `sub_180094BA0`'s `69069`
recurrence (`0x9908B0DF` matrix, `sub_180094CD0` twist), kind 5 is the 4096-word
MT4IC pool (`0x10DCD`, carry `0x495E`, `sub_180095110`). A per-record state is
seeded from one dword read at `0x18009A754`-equivalent (`sub_180094B10`, which
calls the state's seed slot), and can additionally be xored with a wrapping
table installed by `sub_180094AF0` when a licence key fills `qword_1801C2440`
(`sub_1800072D0` → `sub_180006EB0`). Neither is needed for this sample: the
recovered stream is the multiply-add one with the table slot empty.

### What is still masked

The instruction stream is **not** plain Zend words. For `getTotalSendGroups`
(12 ops, record span 1067 bytes, block at `+0x90`) the first 48 bytes are:

```
c2 07 00 00  69 c5 6a 53  5b 0f 00 00  1b 90 6f 74
ee 1f 00 00  43 a9 2d 15  14 00 00 00  9b 07 00 00
40 c7 f9 48  6a 07 00 00  c8 5e 5e 0d  b6 07 00 00
```

Small counters alternate with high-entropy dwords, i.e. the same split the 7.2
build shows: a per-op key array plus XOR-masked opcode bytes (`0x95` is the "no
key" escape there, and `sub_18009E8B0` XORs by op index). Walking that region
with the builder's grammar **does** stay in sync for `getTotalSendGroups`:
twelve opcode words at `0x255b, 0x2563, 0x256b, ...`, ending at `0x25c7` —
exactly the table boundary. The three cache words land where the runtime dump
says they should: `0x0800` → slot `1`, `0x1000` → slot `60`, `0x1800` → explicit
word, and those explicit words read `20`, `24` and `-1`, i.e. the
`extended_value` of `ZEND_FETCH_CONSTANT`, `ZEND_FETCH_OBJ_R` and the closing
`ZEND_RETURN`. `tools.ic74_static_dump.walk_ops` is that grammar and
`tests/test_ic74_static_dump.py` pins both facts.

### The word block starts after the argument table

`+0x90` is where `getTotalSendGroups` happens to begin, not a rule. Every
declared argument contributes a **20-byte record** there — five dwords, whose
third is always `0x00010000` and whose last is a value shifted left eight:

```
addSendGroup    (1 arg)
  00 00 00 00 00 00 00 00 00 00 01 00 1e 00 00 00 41 00 00 00
                                ^^^^^^^^^^^ 0x00010000
```

So the block start is `+0x90 + 20 * num_args`, and the count is not stored as a
field — it is walked by that signature:

```python
start = fields + 0x90
while u32(start + 8) == 0x00010000:
    start += 20
```

That puts **all 112** sample op_arrays on their real start: walking each one from
here places a cache slot on exactly the instructions whose runtime
`extended_value` is non-zero, with no exceptions. `op_block_start` in
`tools/ic74_static_dump.py` is that loop and the test asserts the 112/112.

Slot *values* then agree for all **1731** of them, except the 44
`ZEND_FE_FETCH_R` instructions. That opcode's cache word carries the jump target
relative to the op_array (`addNewsletters` op 8 stores `198`, and the dump's
`jump_targets` says `198`) while the runtime resolves it into a byte offset for
`extended_value` (`5320`) — so the mismatch is resolution state, not a different
encoding.

Measured deltas, for reference:

| op_array | args | delta |
|---|---|---|
| `getTotalSendGroups` | 0 | `0x90` |
| `addSendGroup` | 1 | `0xA4` |
| `editSendGroup` | 2 | `0xB8` |
| `getProductsToSend` | 3 | `0xCC` |
| `getCatSelectedProducts` | 4 | `0xE0` |
The high-entropy dwords in the dump above are therefore the 7.4-only extended
word of each instruction, not a key array — `addSendGroup` shows the same episode
once its own block start is used instead of `+0x90`. Until that start is read out
of the record, `tools/ic74_static_dump.py` reports structure only.

## Open items, in order

1. Locate the seed pair for the last 20 records. Every stored-data and
   derived-data route tested so far is negative (table above), so the way in is
   the writer: find the branch that emits the `[X][k1][k2]` block and what it
   does instead for the 20 names listed above. The reader side is already mapped:
   `sub_180094B10` seeds the record's state from one dword read in the record
   header, and `sub_180094AC0` applies the licence table when
   `qword_1801C2440` is set.
2. Port the word grammar plus `tools/ic74_mask.py` into
   `tools/ic74_static_dump.py` (`--opcodes`), now that the mask model is pinned
   for the records whose pair is in the body.
3. Feed the result into `engines/ioncube/adapter.py` as an `icdump-ir-v1`
   document so `decompile.py` can run without the runtime bundle.

## Tooling in this repo

| Tool | Use |
|---|---|
| `tools/ic74_static_dump.py` | container + body + op_array field block, `--truth` diff |
| `tools/ic74_mask.py` | mask stream from a stored key pair, `--truth` sweep, `--seed` decode |
| `tools/ic74_rea.py` | thin `rea --format json` wrapper that caches each IDA answer under `scratch/ida74/` |
| `scratch/ida74/f_builderA.c` | decompiler output for the record builder, kept as evidence |
| `scratch/ida_start_mcp.py` | starts the ida-pro-mcp plugin server without the menu (IDA `-S` script) |
