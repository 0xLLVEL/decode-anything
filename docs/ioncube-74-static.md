# ionCube 7.4 — static decode status

Target: decode an ionCube-encoded PHP 7.4 file with no PHP process, no loader and
no opcode-dump extension. The 7.2 equivalent is `docs/ioncube-72-static.md`; this
document covers the container gates, the body layout, and the per-record key stub
that makes all 6061 instructions of the sample come out of the file alone.

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

The field scan above stops at the six counters. The function that turns a record
into a `zend_op_array` is where the instruction stream comes from, and it is
reachable by decompile:

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
op     = raw ^ A[i] ^ second                      # major >= 6: two XORs
if op == 0x95:                                    # 7.2 sentinel on the result
    A[i] = 0                                      # encoder omitted the A[i] term
    op   = raw ^ second
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

Measured over the whole sample (`tools/ic74_mask.py --truth`): **112 of 112**
records decode, every opcode byte included.

### The pair is a stub bound by record id

Each record owns a key block written ahead of it, and the block is a stub in the
same envelope the records themselves use:

```
0x2443   record id  89 03 00 00      905    == the dword at +0x00 of the field block
0x2447   s0         b0 1b 00 00      0x1BB0
0x244b   s1         ea 59 00 00      0x59EA
0x244f              00 00 00 00 00 00 00 00
```

The leading dword is not a distance and not a length: it is the **record id**, and
the identical dword sits at `+0x00` of the op_array's field block. That is the
binding the positional search was missing. The lookup that works:

1. index every `[id][s0][s1][8 zero bytes]` in the body with `s0`, `s1` both
   `< 0x10000`;
2. read the record's own id at `+0x00` of its field block;
3. take the **last** stub with that id that starts before the record's name.

Distance from stub to name runs 109..1342 bytes, and ids are not unique — 105
distinct ids over 112 records, up to 10 stubs sharing one — so "last one before
the record" is the rule and "a dword pair somewhere ahead" is not.

### The `0x95` escape

`stored ^ A[i] ^ A[i + ops + 2]` is correct for **6034** of the 6061
instructions. The other 27 resolve to `0x95`, the 7.2 sentinel, and at encode
time the `A[i]` term was simply left out:

```
op = stored ^ A[i] ^ A[i + ops + 2]
if op == 0x95:
    op = stored ^ A[i + ops + 2]          # 27 instructions
```

| Records | Instructions |
|---|---|
| 92 records, no sentinel byte | 6034, plain double XOR |
| 20 records, 27 sentinel bytes total | 27, `0x95` escape |

That split is exact, not approximate: the twenty names the earlier version of
this document listed as "still locked" are **precisely** the twenty records that
contain at least one sentinel byte, and the other ninety-two contain none.

### Why the search reported 92

The old probe derived the mask as `stored ^ opcode` from the runtime dump and
asked for a stored dword pair whose predicted mask matched it **byte for byte**,
over a fixed window, with no notion of the escape. One disagreeing byte anywhere
in a record meant no exact hit, and the pair was reported as absent.

`editSendGroup` is the demonstration: 29 of its 30 derived bytes match its stub's
prediction exactly, and the thirtieth is off by exactly `A[i]` — it is the byte
that double-XORs to `0x95`. With the escape applied, `stored ^ A[i + ops + 2]`
reproduces the runtime opcode and the stub sits at `0xa9d`, 196 bytes ahead of the
name, exactly where the positional search was looking.

So the seed never lived outside the body. The failure was in the probe, not in the
container: it searched *by position* for a pair that is bound *by id*, and it
required an exact match on a stream that carries a sentinel.

On the reader side two generators exist for these states, `sub_1800955E0(kind)`:
kind 4 is a 624-word MT19937 pool seeded through `sub_180094BA0`'s `69069`
recurrence (`0x9908B0DF` matrix, `sub_180094CD0` twist), kind 5 is the 4096-word
MT4IC pool (`0x10DCD`, carry `0x495E`, `sub_180095110`). A per-record state is
seeded from one dword read at `0x18009A754`-equivalent (`sub_180094B10`, which
calls the state's seed slot), and can additionally be xored with a wrapping
table installed by `sub_180094AF0` when a licence key fills `qword_1801C2440`
(`sub_1800072D0` → `sub_180006EB0`). Neither is needed for this sample: the
recovered stream is the multiply-add one with the table slot empty.

### The instruction stream, decoded

The stream is still not plain Zend words. For `getTotalSendGroups` (12 ops,
record span 1067 bytes, block at `+0x90`) the first 48 bytes are:

```
c2 07 00 00  69 c5 6a 53  5b 0f 00 00  1b 90 6f 74
ee 1f 00 00  43 a9 2d 15  14 00 00 00  9b 07 00 00
40 c7 f9 48  6a 07 00 00  c8 5e 5e 0d  b6 07 00 00
```

Small counters alternate with high-entropy dwords: the 7.4-only extended word of
each instruction, not a key array. The opcode byte rides in the low byte of the
first word of each pair and is XORed with `A[i] ^ A[i + ops + 2]`, which is what
`tools.ic74_static_dump.walk_ops` reverses. The walk stays in sync for the whole
record: twelve opcode words at `0x255b, 0x2563, 0x256b, ...`, ending at `0x25c7`
— exactly the literal table boundary. The three cache words land where the
runtime dump says: `0x0800` → slot `1`, `0x1000` → slot `60`, `0x1800` →
explicit word, and those explicit words read `20`, `24` and `-1`, the
`extended_value` of `ZEND_FETCH_CONSTANT`, `ZEND_FETCH_OBJ_R` and the closing
`ZEND_RETURN`.

End to end, `tools/ic74_static_dump.py --opcodes` runs container → body → record
scan → stub lookup → mask stream → `0x95` escape, and prints the whole opcode
stream of every record:

```
python tools/ic74_static_dump.py loader/refs/ic74dump-opcodes/contacts.php \
  --opcodes --truth loader/refs/ic74dump-opcodes/contacts.opcodes.json
# entry_count 112, opcodes_decoded 112, opcode_total 6061, opcode_escapes 27
# matched 112, mismatched 0, missing 0, extra 0, opcode streams 112/112
```

No PHP process, no loader, no debugger, no dump extension.

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
once its own block start is used instead of `+0x90`.

## The reader, mapped in IDA

The seed question is a reader question, so the reader was walked end to end in
`icube_loader_74.dll` with REA. The chain, top down:

| Address | Role |
|---|---|
| `sub_180098FC0` | op_array reader: reads the leading dword, calls `sub_180098C50` for the `u16`-length name, then forks |
| `sub_180098C50` | `u16` length + bytes, copied into a zend_string; **no seed here** |
| `sub_1800987C0` | the 108-byte header path (`a2[1] & 0x8000` clear); builds the op_array, then applies the mask |
| `sub_180098D20` | the inline path (`a2[1] & 0x8000` set): reads the count, **two dwords**, `sub_180098D20`'s own field reads, one trailing dword |
| `sub_180096720` | reads the 27 dwords (108 bytes) that become the record header |
| `sub_180002680` / `sub_180002340` | allocate the 224-byte op_array and copy the two dwords into it |
| `sub_180098570` | builds the opcode-mask array from the state at `header+40`, gated on `flags & 0x2C80` |
| `sub_180094B40` | one mask dword: `sub_180094AC0(state, (*state[3])(state[0]))` |
| `sub_180094AC0` | returns the raw generator word, **XORed with a keystream byte when `state+48` is non-zero** |
| `sub_1800955E0(6)` → `sub_180095560` | allocates the 72-byte state; slots `[2]`/`[3]`/`[4]` hold the step, peek and reset thunks |
| `sub_180095380` | `state.seed[0] = k1; state.seed[1] = k2` — the pair, two dwords |
| `sub_180094AF0` | `state[6] = table; state[7] = len; state[8] = 0` — attaches the keystream table |

The header word map, from `sub_180096720` (`v16` is the 108-byte block, word
index counted in dwords from its first byte):

| Struct | Source |
|---|---|
| `+0` (4 bytes) | words 0..3 as bytes |
| `+4` flags | word 1 |
| `+16`, `+24`, `+40`, `+104` | words 3, 5, 7, 8 |
| `+32`, `+36`, `+52`, `+56`, `+60`, `+64` | words 4, 5, 11, 12, 9, 10 |
| `+112`, `+116`, `+128`, `+136`, `+144`, `+148` | words 14, 15, 16, 18, 19, 20 |
| `+152` | string, when word 21 is set |
| `+160`, `+168` | words 22, 23 |

### The generator, confirmed

`sub_180095390` steps the two-word state and `sub_1800953E0` finishes the word:

```c
s1 = (s1 & 0xFFFF) * 0x7689 + (s1 >> 16);
s0 = (s0 & 0xFFFF) * 0x4650 + (s0 >> 16);
word = ((s1 << 16) | (s1 >> 16)) + s0;   // ROL32(s1, 16) + s0
mask = word ^ dword_1801C20B0;           // the header's bytecode_xor_key
```

That is exactly `tools/ic72_opcode_mask.mask_stream`, and `dword_1801C20B0`
is the `0x00363FA4` the tools pass as `xor_key` — the model was right, and now it
is read out of the binary instead of inferred. Two details come with it:

* `sub_180095400` sets `state[3]`, and `sub_180095390` returns the cached
  `state[2]` without stepping when it is set. So the stream can hand the same
  word out twice, which is why the second byte of each instruction is read at a
  distance of `ops + 2`.
* Two seeders exist and they are not interchangeable. `sub_180095380(state, k1,
  k2)` writes **two** dwords into the seed cell; `sub_180094B10(dword, state)`
  forwards **one** dword to `(*(state + 8))(dword, state[0])` and is only used by
  the class/compiler context (`sub_18009A6xx`). The op_array pair belongs to the
  first: `sub_180003300` calls `sub_180095380(v5, *(header + 20), *(header + 24))`
  — two separate fields.

### Where `header + 20` / `+ 24` are filled

The struct `sub_180003300` seeds from (`v4`) is reachable as
`op_array + 200 -> +136`, and that slot is written in exactly two places:

| Site | Value written |
|---|---|
| `sub_180002680` | `a6`, i.e. the init function `sub_180096970` — a zeroing pass over the 224-byte record |
| `sub_180098FC0`, `0x8000` branch only | `sub_18000B910(reader, v10)` — a raw `v10`-byte **blob copied out of the stream** |

`sub_18000B910` is just "allocate `n`, read `n` bytes" (it masks `0x20000000`
for the `+1` and does nothing else), so the `0x8000` branch does not assemble the
header field by field — it lifts an image.

That matches the stub: the pair for every record is written in the body **ahead**
of the record, 109..1342 bytes before its name, in the block
`[record id][s0][s1][8 zero bytes]`. The reader does not need to be traced
further — the writer's envelope is enough to decode all 112.

Two search attempts that followed this trail and came back empty, both now
explained:

* **The tail scan.** Scanning every byte offset in the 0x400 bytes *after* each
  former miss's op block gives 0 hits (`scratch/probe74_tail_header.py`), and it
  always would: the stub precedes the record, it does not follow it.
* **The zeroed state.** `predict(0, 0)`, `(1, 1)`, `(0, 1)`, `(1, 0)` under
  `0x00363FA4` reproduce none of the masks, which is consistent with every record
  carrying a real pair in its stub.

### `descriptor + 40` is filled behind a vtable

The descriptor is threaded down, not built locally:

```
sub_18009A6C0(?, descriptor)  ->  sub_180098FC0(reader, descriptor, path)
                              ->  sub_1800987C0(reader, descriptor, out, 0)
                              ->  sub_180098570(descriptor, out, &image)   // reads +40
```

Its shape, from the way those three read it:

| Field | Meaning |
|---|---|
| `+0` | version, compared against `4` and `5` |
| `+4` | flags: low nibble picks the state kind (`v7 + 4`), `0x2C80` gates `sub_180098570`, `0x8000` picks the inline branch |
| `+8` | size, compared against `100000` before the keystream table attaches |
| `+40` | the mask state pointer `sub_180098570` dereferences |

`sub_18009A6C0` has **no code xrefs at all** — only two data references,
`0x1801C0050` and `0x1801CFA50`. Both are now decoded (`scratch/pe_vtable74.py`,
reading the PE directly because the adapter has no data-xref verb):

```
0x1801C0050  (in .data, not a vtable)
  rec 0: { 0, sub_18009A6C0, 0,0,0,0,0, 1, "BASIC", 0x48 }
  rec 1: { 0, sub_18009E570, 0,0,0,0,0, 1, "BASIC", 0x47 }
  rec 2: { 0, sub_1800A1BF0, ... }            then packed 32-bit tables

0x1801CFA50  (in .pdata)
  = the RUNTIME_FUNCTION begin RVA of sub_18009A6C0, not a second reference
```

So the "vtable" reading was wrong twice over: `0x1801CFA50` is x64 unwind data,
and `0x1801C0050` is a **profile registration record** — `{0, handler, 0 ×5, 1,
"BASIC", length}` — with three handlers registered under the same `BASIC`
profile. `sub_18009A6C0` therefore has no call site by construction: it is reached
as a function pointer taken out of that `.data` table, together with its two
siblings.

Reaching the write site for `+40` now needs a data xref on `0x1801C0050` (the
adapter lists code xrefs only and returns no result for data addresses) or the
runtime watch. The descriptor is built by whatever indexes that table.

### Who writes the mask array at `op_array + 64`

A sweep over every decompiled body for stores to `+64` gives exactly three
candidates, and only one of them materialises an array:

| Site | Instruction | What it is |
|---|---|---|
| `sub_180096720` | `*(v3 + 64) = v26` | a numeric header field (stream word 10), not a pointer to generated bytes |
| `sub_180096970` | `*(a1 + 64) = 0` | the zeroing pass |
| `sub_180098570` | `*(a3 + 64) = v12` | `malloc(4 * n + 4)` filled one dword at a time from `sub_180094B40` — the only real mask array |

So the array has exactly one producer, and it sits behind the `flags & 0x2C80`
gate. The consumer does not check the gate again; it indexes the array by a
triple stride (`sub_180097AA0`, the byte-level decoder):

```c
v27 = opcode ^ mask_array[v18];
v30 = (desc->version < 6)
    ? v27
    : v27 ^ *(u8 *)(v9 + image->count + *(desc->ctx + 192) + mask_array);
```

`*(desc->ctx + 192)` is a running offset, so the mask is consumed as one stream
over the whole file while the per-record array supplies the local copy. That is
why the tool's `A[i] ^ A[i + count + 2]` model works: the same absolute position
appears once as the record-local index and once as the stream offset.

### The offset hypothesis, tested and dead

If the `*(ctx + 192)` term were what differs between records, a mask would be the
same stream read from another position — `S[d] ^ S[d + count + 2]` for one of the
known seed pairs and some shift `d`. `scratch/probe74_offset_shift.py` tests that
over 92 pairs × shifts `0..2000` × the 20 former misses: **0/20** matches. The
offset is not the variable. The seed is, and each record carries its own in its
stub.

### The context constructor, and why `+40` never mattered

The context is created by PHP stream glue, four hops above the reader:

```
sub_180077D30        stream opener
gets it from v36 = sub_18000BE70()      // constructor
sub_18000BE70        installs slots, calls sub_180001440()
sub_180001440        emalloc(232); memset(0, 0xE8)     ← everything zeroed
```

`sub_18000BE70` then fills `+160` (open), `+168`, `+176`, `+192`, `+200`, `+216`
(dtor), `+24 = -1`, `+88 = +96 = -1`. **`+40` is not among them** — the 232-byte
block is memset to zero and `+40` stays `NULL`.

That closes the question. `sub_180098570` is gated on `*(ctx+4) & 0x2C80`, and
the stream writes `2` into that field for all 112 records, so it never
dereferences `+40` at all in this container. The mask that actually hides the
opcode bytes is applied one level down:

```c
// sub_1800976A0 -> per instruction
result = sub_1800975D0(op, i, opcode_byte, kind, mask_array, ctx, count);

// sub_1800975D0
v11 = i + count + 2 * i;                       // 3*i + count
v12 = *(u32 *)(mask_array + v11);              // four bytes, not two
if (*(int *)(ctx + 16) >= 6 && *op != ~v12)
    return sub_180069240(...);                 // escape path
result = sub_1800692C0(op, opcode_byte, v12);  // stored byte ^ mask dword
```

So the mask byte for instruction `i` is read at offset `3*i + count` of the array
at `op_array + 64`, and the double-read distance the tools model is the same
thing seen from the byte stream: `i` and `i + count + 2` collapse into one
triple-stride index. `ctx + 16` is the encoder major — `>= 6` enables the escape
path, which is why 7.4 behaves like 7.2 only up to that branch.

### The registration chain, decoded

A `lea`/`movabs` scan of `.text` (`scratch/pe_find_table_refs.py`) found the three
profile blocks by their addresses — stride `0x50`, exactly the record size:

```
0x18006a6f9  lea r8, 0x1801C0030
0x18006a713  lea r8, 0x1801C0080
0x18006a71f  lea r8, 0x1801C00D0
```

They are loaded in `sub_18006A630`, the module-init routine (it also does the
`CLI`/`cli` SAPI detection and interns a string), which then hands the array to
the registrar. End to end:

| Function | Role |
|---|---|
| `sub_18006A630` | module init; builds `{&0x1C0030, &0x1C0080, &0x1C00D0}` |
| `sub_180001D10` | walks each block, one `sub_180001C90` per entry |
| `sub_180001C90` | appends the entry pointer to growable array `qword_1801C1840` (`{count, capacity, base}`) |
| `sub_180001DA0` | lookup: scans the array for `entry->kind == kind` and `sub_180001D70(entry, version)` |
| `sub_180001D70` | version test on `entry+16`: low 16 bits = max, high 16 = min, match when `min <= v <= max` |

So the record layout is `+0` kind (`1` for all three `BASIC` entries), `+16`
version range, `+32` handler, and the handler pointers land exactly where the data
dump put them. The lookup callers are the container parsers; the one at
`sub_18006FBF0` shows the whole handshake:

```c
v11 = *(unsigned int **)(a2 + 24);
v12 = sub_180001DA0(**(_DWORD **)(a2 + 16), *v11, v10);   // (kind, version)
if ( !v12 ) return -2;
...
v13 = (*(__int64 (__fastcall **)(__int64, __int64, __int64 *))(v12 + 32))(v12, a1, &v15);
```

`a1` there is the loader context — the same struct whose `+4` flags, `+8` size and
`+40` mask state `sub_180098570` reads. The registry therefore selects a
*profile handler*, it does not build the context; the context arrives already
populated, which is consistent with the rest of this document: `+40` is written
outside both the registry and the record reader, and the mask that matters for
7.4 is applied in `sub_180097AA0`, not from `+40`.

### The one-dword seeder is a stub

`sub_180094B10(dword, state)` forwards to `(*(state + 8))(dword, state[0])`, and
`state[8]` is vtable slot 1, filled by `sub_180095560` with
`_guard_check_icall_nop`. That symbol decompiles to a bare `;` at `0x1800076D0`.
So the call **discards its dword and seeds nothing** — every `0x18009A6xx` call
site that looks like it seeds from one stream dword is a no-op, and the state it
left behind is the zeroed one (which is why the `(0, 0)` test failed).

There is therefore exactly one seeder in the binary: `sub_180095380`, two dwords,
two callers, both listed below.

### The executor's other two callers

`sub_180003300` has three code xrefs besides the done-check wrapper:

| Caller | Role | Touches the seed? |
|---|---|---|
| `sub_180007820` | `byte 0 == 2 && flags & 0x4000000` → run | no, it calls in |
| `sub_18006A250` | same two guards, then `sub_180003300` | no |
| `sub_180077680` | same two guards, frame call with an `int16` slot | no |

All three only *consume* a record whose flags already say "ready". None of them
writes `+20`/`+24`, so the fill site is not on the executor side.

### Who calls the two-dword seeder

`sub_180095380` has exactly **two** xrefs in the whole DLL, and both of them are
readers:

| Caller | What it seeds from | Consumer |
|---|---|---|
| `sub_180001F40` | `sub_1800076E0(ptr, len)` and `sub_180007730(ptr, len)` — hashes of a string | byte decryptor: `sub_180094B20` per byte, `BYTE1(word)` |
| `sub_180003300` | `*(header + 20)`, `*(header + 24)` | op_array: `sub_180094B40` per dword, full word |

Two things fall out of this:

* Nobody in the DLL *writes* the stub through this function. The pair reaches the
  op_array header from wherever the header is filled, so the writer is a
  header-fill site, not a seed site — the stub is emitted by the encoder and read
  back by the header path, not assembled by the loader.
* The two paths use different word producers. Strings take `state[+16]` →
  `sub_180095390`, the raw step with no `xor_key`. Op_arrays take `state[+24]` →
  `sub_1800953E0`, the step **XORed with `dword_1801C20B0`**. That is why a single
  `xor_key` reproduces every op_array mask and nothing else in the file.

### The hash hypothesis, tested and dead

Hashing was never needed and is not what happens: every record carries its pair in
its stub. The negative result stands as a closed route
(`scratch/probe74_hash_seed.py`): over five input variants (`name`, `name`+NUL,
`class\name`, `class`, the record's own body slice) × three masks (low 16, high
16, full) × both halves, the two loader hashes produce **0/92** matches against the
then-92 recovered pairs.

```
addSendGroup   hash 76e0(name) = 0x8ac2744f   hash 7730(name) = 0xa63e3ec9
               stored          s0 = 0x5043   s1 = 0x20dc
```

The "different key" sweep is closed for the same reason: `scratch/probe74_locked_seed.py`
matches a pair to a **mask**, and a mask that carries a sentinel byte matches
nothing, so its 92/112 is the sentinel count, not a key difference.

### The one-dword hypothesis, tested and dead

If `sub_180094B10` also seeded the op_array mask, one stored dword would have to
derive `(s0, s1)`. It does not. Across all **112** stubs
(`scratch/probe74_seed1.py`):

| Check | Result |
|---|---|
| both halves below `0x10000` (stored zero-extended) | 112/112 |
| `s1 == step(s0, 0x7689)`, `s0 == step(s1, 0x4650)`, or `s1 == rol16(s0)` | 0/112 |
| `(s1 << 16) | s0` present anywhere in the body | 0/112 |
| dword in front of the pair equal to any packing of `s0`/`s1` | 0/112 |

The layout is always the same, which is what the writer emits — the leading dword
is the record id, and it reappears at `+0x00` of the field block:

```
addSendGroup
  42 07 00 00 | 43 50 00 00 | dc 20 00 00 | 00 00 00 00 00 00 00 00
  id = 0x742    s0 = 0x5043   s1 = 0x20dc    eight zero bytes
```

So the mask seed is **two independent 16-bit values**, written as two dword-slots
behind the record id. No dword derivation and no packing: the single-dword seeder
is a different state entirely, which is why looking for an arithmetic relation
kept coming back empty.

### Where the keystream table attaches

```c
v13 = sub_1800955E0(kind);
sub_180094B10(dword_read_from_stream, v13);
if (qword_1801C2440 && (int)descriptor[2] >= 100000)
    sub_180094AF0(state, qword_1801C2440, (int)qword_1801C2448);
```

`qword_1801C2440` is the **licence** blob, a loader global — not a body field —
and the second condition is per descriptor, which is the only per-record switch
yet found that can route the mask through `sub_180094AC0`'s XOR path. Neither
input is available statically, so this stays a hypothesis until it is watched at
runtime.

Two results matter more than the map:

* **The `flags & 0x2C80` gate is closed for this sample.** `sub_180096720` writes
  stream word 1 straight into `struct+4`, and that word is `0x00000002` for all
  112 records (probe: `scratch/probe74_split.py`). So `sub_180098570` takes its
  `else` branch and emits `-1` for both mask slots — the array it builds from
  `header+40` is *not* what hides the opcode bytes in an encoder-15.0.1 file.
  The masking that `tools/ic74_mask.py` models is applied further down, in
  `sub_180097AA0`, which is why modelling it empirically (pair → stream) was the
  right call and why no header field predicts which records carry their pair.
* **A second mask path exists**: `sub_180094AC0` XORs the generator word with a
  keystream byte whenever `state+48` is set, and `sub_180094AF0` is the only
  writer of that slot. Nothing in the 108-byte header fills it, so it is unused
  for this sample — a record that did use it would need both the table and the
  seed from a licence blob, and no record here carries one.

## Open items, in order

1. Verify the stub envelope on a second artifact. Everything above is exact for
   one encoder-15.0.1 file (112/112 records, 6061/6061 opcodes, 27 escapes), but
   the fields that could move between encoders are the stub spacing (109..1342
   bytes here) and the escape index term (`ops + 2`). Run `--opcodes --truth`
   against a second 7.4 sample before treating the constants as fixed.

   Tried on `C:/Users/ezan/Documents/samples/next.php` (PHP 7.4, encoder 13.0.1,
   third-party "Rtl-Theme" wrapper): both container gates pass (`md4_matches`,
   `transition_checksum_matches`) and the body inflates to 9875 bytes, but it
   opens with a symbol table (`\x01\x00\x00\x00\x06\x00\x00\x00 <len> <name>\0`)
   and carries no `0x42020001` record mark anywhere, so the scan finds
   **0 op_arrays**. That is a different body layout, not a moved constant: the
   encoder-15 grammar above is unchanged and still needs a second encoder-15
   artifact to be measured against. Encoder 13.0.x 7.4 files stay on the runtime
   path until that layout is reversed.

   Reconfirmed while doing it: the dump path is not 92/112. `--opcodes --truth`
   on the sample reports `entry_count 112`, `opcodes_decoded 112`,
   `opcode_total 6061`, `matched 112`, `opcode streams 112/112`, and
   `tests/test_ic74_static_dump.py` asserts `unseeded == set()` — every record
   owns a stub blend. The 92/112 in `probe74_locked_seed.py` was that probe's
   sentinel count, not a decode gap.

2. Feed the result into `engines/ioncube/adapter.py` as an `icdump-ir-v1`
   document so `decompile.py` can run without the runtime bundle. The opcode
   bytes, the line numbers and the cache slots are all available now; the literal
   and static-variable tables are the next read.

## Tooling in this repo

| Tool | Use |
|---|---|
| `tools/ic74_static_dump.py` | container + body + op_array field block; `--opcodes` decodes every instruction, `--truth` diffs fields and opcode bytes |
| `tools/ic74_mask.py` | stub index, mask stream, `0x95` escape; `--truth` sweep, `--scan`, `--seed` decode |
| `tools/ic74_rea.py` | thin `rea --format json` wrapper that caches each IDA answer under `scratch/ida74/` |
| `scratch/ida74/f_builderA.c` | decompiler output for the record builder, kept as evidence |
| `scratch/probe74_full.py` | the 6061-opcode proof: every record from its stub, escape applied, zero mismatches |
| `scratch/probe74_stub_residual.py` | per-record residual map against the stub pair — that is how the single bad byte surfaced |
| `scratch/probe74_escape.py` | per-bad-byte evidence that the residual equals `A[i]` |
| `scratch/probe74_id.py` | locates every record id and dumps the stub envelope |
| `scratch/probe74_fields.py` | side-by-side field-block dump, decoded record vs former miss |
| `scratch/probe74_solve.rs` | 24-thread 2^32 seed solver — worked, then became unnecessary once the stub was read |
| `scratch/probe74_tail_header.py` | tail scan for a header image — 0 hits, superseded by the stub |
| `scratch/probe74_locked_seed.py` | exact-mask window sweep — its 92/112 is the sentinel count |
| `scratch/probe74_hash_seed.py` | reimplements `sub_1800076E0` / `sub_180007730` and tests them as the seed source |
| `scratch/probe74_seed1.py` | tests every one-dword derivation of the `(s0, s1)` pair — all negative |
| `scratch/probe74_split.py` | dumps every record's header dwords (that is how `flags == 2` was ruled out) |
| `scratch/ida_start_mcp.py` | starts the ida-pro-mcp plugin server without the menu (IDA `-S` script) |
