# ionCube 7.2 — static decode status and plan

Target: turn `engines/ioncube` into a static 7.2 decompiler (no PHP runtime, no opcode-dump DLL).
Current 7.x path is runtime-only (`engines/ioncube/runtime_dump.py`); `dumper.SUPPORTED_BODY_LAYOUTS` stops at 81–84.

## Loader map (ioncube_loader_win_7.2.dll)

| Item | Value |
|---|---|
| Build | 15.5.1, PE x86_64, image base `0x180000000` |
| `zend_extension_entry` | `0x1800DA140` |
| startup / shutdown | `0x180070D90` / `0x180071030` |
| module entry | `0x1800E46F0` (name `ionCube Loader`, version `15.5.1`) |
| MINIT / RINIT | `0x180073240` / `0x180073540` |
| RINIT body | `0x180073640` (auto-globals, license checks) |
| RINIT key init | `0x1800710C0`: `srand((uint16)time(NULL))` once, then `time64()` stored at `0x1800E62F8` and copied to `0x1800E6300` |
| compile wrapper | `0x180014A40` (opens stream, calls the original `zend_compile_file`; not a decoder) |
| crypto init | `0x18000B010` (seeds `srand`, calls `0x18009A7B0`, `0x1800923E0`, `0x18009C4D0`) |
| compile hook install | `0x180071040` — saves `zend_compile_file`/`zend_execute_ex`, installs `0x180070870`/`0x180070B70` |
| compile hook restore | `0x180071080` |
| encoded-file compile entry | `0x180070870` → `0x18007D560`; plain PHP falls back to `0x180070830` |
| header/body parser | `0x18007BA00`, called from `0x18007D560` |
| compiler contexts | `0x1800085E0` (file handle), `0x18000BD70` (stream) |
| AES decrypt schedule | `0x1800979A0` — Td tables `0x1800B4E90`, `0x1800B5F20`, `0x1800B6B50`, `0x1800B7350`, `0x1800B7F50` |
| AES decrypt block | `0x180098A70`; wrapper `0x180099050` |
| Rijndael Te0 table | `0x1800B8350` (Te1 `0x1800B7B50`, Te2 `0x1800B6720`, Te3 `0x1800B8750`) |
| AES block encrypt | `0x1800984B0` — key schedule in arg3, loop count `arg3[128] >> 1`, i.e. AES-256 |
| AES wrapper | `0x180098A50` → `0x1800984B0`, called through the pointer table at `0x1800F3E98` |
| MD5 | T1 constant at `0x18009A913` (implementation around `0x18009A000`) |
| SHA-1 | init constants at `0x18000BDF2`, `0x18009B095` |

## What the static blob looks like

Sample: `binancepay_asli.php`, header `php_version_code = 72`, `serialization version = 5`, `bytecode_xor_key = 0x00364730`, `php_flags = 0x00048487`.

- Body length: 25712 bytes.
- Main record: offset `0x0`, blob at `0x4C`, length 616, record ends at `0x2B4`.
- Blob layout: 8-byte header (tag `0x268` + 4 bytes), then 608 bytes payload.
- `608 = 38 * 16` exactly; payload entropy 7.668 bit/byte. Block alignment is consistent with a 16-byte cipher, but it does **not** prove AES: the loader's AES routines are not reachable from the decode path by xref, so AES may serve licensing/signatures instead.
- The 8.x inner-record parser rejects it: `metadata checksum mismatch: stored 0x865D, calculated 0xE56D` → the 124-byte metadata layout is 8.x-specific.
- The function section at `0x2B4` does not parse with `extract_dynamic_main_record` for any offset `0x2B4..0x2DC`, so sv5 record framing differs from 8.x.

## Three unknowns block a static decoder

1. **Key derivation** — how `bytecode_xor_key`, `owner_key`, header trailer fields, and loader constants produce the AES-256 key/IV for each op_array blob.
2. **sv5 record framing** — metadata block size/layout and checksum; function/class section boundaries.
3. **Opcode stream encoding** — the loader materializes and re-encodes opcodes at request time; the static stream must be decoded with the loader's own algorithm, not the runtime key.

None of the three can be recovered from the runtime dump: the dump is produced after the loader already decrypted and materialized the op arrays.

## Milestones

| # | Deliverable | Acceptance |
|---|---|---|
| M0 | Loader map + crypto primitives identified | this document, addresses verified in IDA |
| M1 | AES-256 decrypt ported to Python — **done**, `engines/ioncube/rijndael.py` | 3 known-answer tests pass: FIPS-197 C.1, C.3, NIST SP 800-38A CBC |
| M2 | Key derivation ported — **in progress** | main blob decrypts; bytes 0..123 form a plausible metadata block with a matching checksum |
| M3 | sv5 record walker | main + 4 functions enumerated in the same order as `scratch/rt/binancepay_asli.opcodes.json` |
| M4 | Opcode stream decoder | opcode counts/names equal the runtime dump for all 5 op_arrays |

Exit criterion for the whole effort: `python decompile.py samples/binancepay_asli.php --php-version 72` produces PHP that passes `php -l`, with zero unusable jump targets, without any runtime bundle.

## Cipher dispatch (found in M2)

The loader does not call AES from the decode path directly; it builds a cipher object from a
numeric id and then dispatches through a vtable.

| Item | Value |
|---|---|
| Cipher factory | `0x180001EB0(cipher_id, mode)` — jump table at `0x180002028`, ids `0..6` |
| id `0` init | `0x180001EFF` sets vtable slot `+0xA0` to `0x180001E10` (cipher0, no key schedule) |
| id `1..6` init | resolve a class id via `0x18009A7B0`, then class table `base+0xE6D64` (stride `0x88`) and mode table `base+0xE7E5C` (stride `0x78`); init call at `[class + 0xE6D98]` |
| key/block sizes | class descriptor `+0x14` block size, `+0x18` schedule bytes (16/40/56 for the 128/192/256-bit AES descriptors); one descriptor at `0x1800B4980` embeds the DER OID `06 09 60 86 48 01 65 03 04 02` = AES-256-CBC |
| mode `0` | auto-select: `0x180001F84` → `0x1800923E0` + `0x1800958A0` |
| dispatch site | `0x18000324E` `call [cipher + 0xA0]` inside the stream decoder `0x1800031B0` |
| cipher selector | `[reader + 0x20] + 0x40` = id, `+0x44` = mode |

### cipher0 (`id 0`) is byte-exact and already ported

`0x180001E10` is the whole primitive, and it matches `engines/ioncube/body.py` exactly:

- state = `PRNG6(0x180007340(key, klen), 0x180007390(key, klen))`;
- `0x180007340` is the `1025`/`>>6`/`9x`/`>>11`/`32769` hash (`hash_10006680`);
- `0x180007390` is MurmurHash3 x86-32 with seed `0x1F` (`hash_100066c0`);
- per byte: `next()` from `0x18009CA40`, output byte `(value >> 8) & 0xFF`, XORed in place;
- 5th arg is the key length (no implicit NUL), 6th arg is the output pointer.

So M1's cipher0 port needs no correction — the open problem is only *which* id/mode the record
uses and what key bytes reach it.

## Runtime instrumentation (32-bit loader)

The working runtime (`scratch/refs/ic72dump-opcodes/runtime`) is **PHP 7.2.34 NTS x86**, so it loads
the 32-bit `ioncube_loader_win_7.2.dll` (809,984 bytes), not the 64-bit build mapped above.  The
same primitives exist with different addresses:

| Item | 32-bit address |
|---|---|
| `hash_10006680` | `0x10006200` (`imul ..., 0x401`, `imul ..., 0x8001`) |
| `hash_100066c0` (Murmur3, seed `0x1F`) | `0x10006240` |
| PRNG6 / keystream step | `0x100088C40` |
| cipher0 init (xor loop) | `0x10001BB0`, loop body at `0x10001C07` |
| cipher factory | `0x10001C40`, jump table `0x10001D60`, case 0 sets `[esi+0xA0] = 0x10001BB0` |
| MT4IC constants (`0x10DCD`, `0x495E`, `0x12D687`) | around `0x10089000` |

Two tools were added to observe the loader instead of guessing:

- `tools/ic72_cipher_trace.py` — a WOW64 debugger.  It launches `php -l`/`php -r include`, finds
  the loader by scanning for the cipher0 loop signature, arms `int3` breakpoints on the factory and
  the cipher0 init, and logs `id`/`mode`/key bytes through `Wow64GetThreadContext`.  WOW64 reports
  `#BP`/`#DB` as `0x4000001F`/`0x4000001E`, and a 32-bit thread needs `Wow64GetThreadContext` with
  `WOW64_CONTEXT_*` flags and a real `OpenThread` handle.  Verified with a breakpoint on the PE entry
  point: the hit arrives and `ecx`/`edx`/`esp` read back correctly.
- `tools/ic72_memdump.py` — includes the encoded file behind a shutdown `sleep()`, then reads the
  live process with `ReadProcessMemory` and saves regions that contain decoded text.

### Result: the cipher factory is never used for this file

With both breakpoints armed during a successful compile (`Restricted Access` HTML is printed), neither
`0x10001C40` nor `0x10001BB0` is ever hit.  The sv5 body of this sample therefore does **not** go
through the cipher factory, which is why every cipher0/AES trial in M2 failed: the wrong subsystem was
being attacked.

### What the decoded data looks like in memory

`scratch/mem72/region_15200000.bin` contains the decoded literal pool in clear text at offset `0x5e7eb`:

```
... \x0b binancepay_config \0 \x0a configarray \0 [4'name [4'Type s6'System
    5126;4294967295;1;6;5'Value s43'Binance Pay (https://merchant.binance.com/) ...
```

That is the ionCube literal serialization (length-prefixed strings plus `5126;...` descriptors), i.e.
the loader really did decode this record.  At the same time, `region_15400000.bin` offset `0x9659c`
holds the **original 616-byte ciphertext record verbatim**, so decryption does not happen in place in
that buffer.  No plaintext copy of the record framing (`FF FF FF FF 68 02 00 00`) exists in either
dumped region, and a rolling Fletcher-16 scan (the `_metadata_checksum` used by `read_inner_op_array_record`)
finds no plausible plaintext metadata block — so the loader parses fields on the fly instead of
materializing a decrypted record image.

## M2 log

- Compile hook chain located: `0x180071040` → `0x180070870` → `0x18007D560` → `0x18007BA00`.
- AES key schedule and both block functions located (addresses above).
- Cipher factory and cipher0 disassembled; cipher0 verified byte-identical to the Python port (hashes, seeding, `>>8` byte extraction).
- The main record blob is **not** cipher0. `decrypt_cipher0` over the 616-byte record was tried with:
  - key = `bytecode_xor_key` / `owner_key` / `member_id` as text, LE bytes, BE bytes, with and without trailing NUL;
  - key = decrypted-header slices `4/8/16/20/24/32/40/48/64/168` bytes, with and without NUL;
  - key = 16×`0x01`+NUL (the dynamic fallback) and `hashlib` MD5/SHA-1/SHA-256 derivations of the header;
  - every candidate at data offsets `0`, `8`, `16` — no checksum match.
- AES was likewise ruled out for those keys and IVs: ECB and CBC with key = header slices,
  MD5/SHA-1/SHA-256 of header/prefix, the 16-byte stored MD4, `rol8(MD4)`, and IV = zero,
  `blob[0:16]`, `blob[8:24]`, header tail.
- Continuation of the header PRNG was ruled out: `MT4IC(seed)` advanced by `0`, `header_size-16`,
  `header_size`, `+8`, `+16`, `+32` words with and without the `rol8(MD4)` keystream XOR.
- The record is not a plaintext block with a different checksum either: CRC-16/CCITT (init `0xFFFF`
  and `0`), CRC-16/IBM, Adler-16, CRC-32 low/high halves, `sum16`, `xor16` over offsets `0..8`
  and lengths `120/124/128/132` never equal `0x865D`.
- Re-ran the whole matrix against a **content oracle** instead of the checksum (needles `Binance`,
  `Restricted`, `merchant.binance.com`, `$configarray`, `api_key`) so a wrong sv5 checksum cannot
  hide a good decrypt: still no hit. That run also swept every printable string of length 4..80
  from the loader DLL as a cipher0 key (4053 keys × NUL/no-NUL × offsets `0/4/8`, 16212 trials)
  plus AES-ECB/CBC with each of those as a key — nothing.
- Implication: the key is produced at runtime (installation/licence state), not from a constant or
  a header field. Static decode of the body therefore needs the runtime key, or an emulation of the
  licence key derivation.
- Runtime breakpoints settled the question differently: the cipher factory (`0x10001C40`) and cipher0
  init (`0x10001BB0`) are never called while the sample compiles, so the sv5 body uses neither.  The
  next target is the decode path that produces the literal pool found in memory.
- Remaining unknown: which `(id, mode)` the sv5 record selects and where its key string comes from.
  The selector lives at `[reader+0x20]+0x40/+0x44`; that reader is built in the `0x18007BA00`
  header parse, but the assignments are indirect (`0x180078BE0` / `0x18007A400` write `[rbp+0x40]`
  for other structures), so a single runtime breakpoint on `0x180001EB0` reading `ecx`/`edx`
  is cheaper than continuing static xref work.
- Next: break at the factory during a real compile of the sample and record `(id, mode)` plus the
  key pointer/length handed to `0x1800039A0`; then implement that cipher.

## Parallel, cheaper path to correct output

The runtime dump already returns correct opcode numbers; its bad jumps come from `step1` being skipped in the dumper. Rebuilding `php_opcodedump.dll` with `step1` forced (or fixing its gating) corrects control flow without any static decode. That does not replace M1–M4, but it is the shortest route to `php -l`-clean output today.

## M2.1 — runtime watchpoint campaign (32-bit loader)

The 64-bit addresses above belong to a different build. The runtime that actually executes the
sample is **PHP 7.2.34 NTS x86**, so the live loader is the 32-bit `ioncube_loader_win_7.2.dll`
(809,984 bytes). Everything below refers to that image, ImageBase `0x10000000`.

| Item | RVA |
|---|---|
| factory signature probe (`A1 A0 CB 0B 10`) | `0x1C40` |
| `hash_10006680` / `hash_100066c0` call sites | `0x1BCD` / `0x1BDD` |
| PRNG6 `next` (thiscall, state pointer in `ecx`) | `0x88C40` |
| PRNG6 call sites | `0x1C09`, `0x7F1E`, `0x8205`, `0x82A8`, `0x694D2`, `0x69C52`, `0x6B2DA`, `0x8C98B`..`0x8CA16` |

New instrument: [ic72_blob_watch.py](../tools/ic72_blob_watch.py). It attaches as a WOW64
debugger, locates the loader by the factory signature, can int3 any loader RVA (`--bp`), and polls
committed regions for the record signature (`FF FF FF FF 68 02 00 00 F8 85 D7 7D 18 F9 4C 83`).
On a hit it arms `Dr0..Dr3` over the record's first 16 bytes on every thread, so the first reader
is reported with EIP, stack and register state.

### What the watchpoint proved

- The body buffer is a private region of ~`0xB7000` bytes; the record sits at `region+0xAD6D4`
  (+`0xAD87C` on another run) and the surrounding region base moves per run, so absolute addresses
  cannot be pre-armed. The literal pool is materialised separately, in a 2 MiB Zend MM chunk at
  `chunk+0x5E7EB`.
- The record bytes stay **byte-identical** to the file copy in memory, i.e. the loader does not
  decode in place. The decoded form is built field-by-field or in a scratch buffer.
- `0x10088C40` (PRNG6) is **never called** during compile + include of this sample, so the record
  layer does not use the PRNG6 family at all. That rules out cipher0 and the C3D0 stream for it.
- Static reading of the PRNG6 call sites: `0x69C52` and `0x6B2DA` are inside the cipher class -
  they copy a 16-byte block through `0x1006F520`, `rol 3` every byte, then XOR a PRNG6 stream, and
  the surrounding code runs `0x1000A580` over `0x200`/`0x40` blocks (an AES-style block loop). Those
  are the cipher objects, not the record parser.
- `find_export(loader, "zend_compile_file")` returns nothing on this build, so the compile hook
  cannot be used as a trigger; the loader entry has to be reached through the factory signature or
  an exported data pointer.

### Keystream, derived and verified

[ic72_keystream.py](../tools/ic72_keystream.py) rebuilds the sv5 body keystream byte for byte:
75 encrypted frames, **9,233 keystream bytes**, seed `0x05A3AEF6`. A fresh `MT4IC(0x05A3AEF6)`
reproduces the whole stream (`True`), the two in-stream checksums match, and the resulting deflate
stream inflates to 25,712 bytes. The bytes are written to `scratch/ic72_body_keystream.bin`.

So the body layer is closed: seed + MT4IC + frame walker is the complete keystream. The open piece
is only the 608-byte record payload that follows the `FF FF FF FF <len>` marker; its checksum
(stored `0x865D` at +124) never matches the plaintext bytes under Fletcher-16, Adler-32, CRC-16 or
CRC-32 over any prefix, which is what makes the "encoded metadata" reading solid.

### Next

Hook `0x62E80` (the real compile body) and `0x6D970` from the compile-hook wrapper, log their call
tree during `include`, and stop on the first routine that reads the record marker. That gives the
parse function directly instead of inferring it from cipher geometry.

## M2.2 — record layer: negative results and the guard tool

Two more attacks on the 608-byte record payload, both negative, and one new instrument.

**Seed sweep.** For every combination of the header key material (`bytecode_xor_key`, `owner_key`,
`member_id`, both outer key words, the body and secondary seeds, and their pairwise XORs) the payload
was XORed with a 16-byte table (`rol3` of the first or last 16 bytes, or zeros) and either an
`MT4IC` or `PRNG6` stream. 735 combinations, checksum checked at every start offset 0..16: **0 hits**.
A separate `cipher0` sweep over 254 header-derived keys (slices of the decrypted header at 11 lengths
x 10 offsets, body slices, blob slices, plus MD5 of each) also produced **0 hits**.

**Hook probes.** The documented compile-hook RVA `0x62F30` does hit under
[ic72_cipher_trace.py](../tools/ic72_cipher_trace.py), but the same breakpoint armed from the DLL-load
event in the newer tool never fires, and neither does `0x62E80` (the compile body the hook calls)
nor `0x6D970`. The byte is still `0xCC` at exit, so the code path is not taken in that run - the
hook that the older tool reached must be installed later in startup than the load event.

**New tool.** [ic72_record_guard.py](../tools/ic72_record_guard.py) arms `PAGE_GUARD` on the body
region and walks the guard forward with the region's committed frontier, so the fault lands while
the body is still inflating; once the record signature is complete it arms `Dr0..Dr3` on it. It
also keeps `int3` bytes re-armed (the loader unpacks over early patches) and accepts arbitrary
`--bp` RVAs. Two limits found: the loader's own guard pages collide with ours when a foreign
fault is passed through, and guarding perturbs the target, so the worker is opt-in (`--guard`).

Status: the body layer stays closed and verified; the record layer still has no confirmed transform.
The probe that followed this note (arm the compile hook from the export pointer, break on the first
`call`, read the `zend_file_handle`) is written up in the next section, and it did not find a record
transform there — the compile path never touches the bytecode layer.

## Compile-hook chain, traced (32-bit 7.2, `--auto`)

`--auto` in [ic72_record_guard.py](../tools/ic72_record_guard.py) now resolves the chain end to end.
Three details mattered; each was a wrong assumption before:

1. **The shim is installed after `LOAD_DLL`, not at load time.** The `zend_compile_file` export slot in
   `php7.dll` reads `0x6eaff700` at load and only later becomes `loader + 0x62F30`. A breakpoint armed at
   the load event therefore never fires. `--auto` polls the export slot every 2 ms and arms on the
   transition; observed transition at ~t+0.18 s, hit ~40 ms later.
2. **The `bp_worker` thread was dead.** Its loop condition included `module_base`, which is `None` when
   the thread starts, so the body never ran. That is why the older tool's `int3` bytes appeared to
   survive untouched at exit: nobody was re-arming them.
3. **The `zend_file_handle` is not in `ecx` at `0x62F30`.** The shim is `push esi; push edi;
   mov edi, [esp+0xC]`, i.e. a plain cdecl `(zend_file_handle *fh)`. Read `edi`. The filename is the
   C string at `fh+0x2C` (not a `zend_string` at `fh+0`).

Chain, confirmed with real register values:

| Step | RVA | Evidence |
|---|---|---|
| `zend_compile_file` shim | `0x62F30` | `edi = 0x6dfec1c`, `path = ...\binancepay_asli.php` |
| filename filter, `call` at `0x63005` | `0x62E80` | `ecx` = same handle, returns bool, tail-jumps `0x62E40` |
| real loader compile | `0x6D970` | `ecx` = same handle, `ret = 0x63015` |
| raw source buffer handed to `zend_compile_string` | `0x7190` | `ecx = 0x14e76000`, `edx = 0x373D` |
| op_array postprocess | `0x6C340`, `0x6D500` | `0x6D500` receives `edx = 0x00048487` = the file's `php_flags` |

The buffer at `0x7190` is **byte-identical to the file on disk** (14 141 bytes, same md5):
`<?php //00407` + header + base64 blob. So the compile path does not decode the record at all —
it compiles the ionCube stub as ordinary PHP source and the bytecode layer never appears here.
Reproduced with:

```bash
python tools/ic72_record_guard.py \
  --php scratch/refs/ic72dump-opcodes/runtime/php.exe \
  --loader scratch/refs/ic72dump-opcodes/runtime/ext/ioncube_loader_win_7.2.dll \
  --target scratch/rt/binancepay_asli.php \
  --auto --bp 0x7190 --dump-bp 0x7190 --dump-to scratch/ic72_plain_buffer.php
```

Consequence for M3/M4: the record decoder is a **runtime** component (the loader's own opcode
handler), not part of `zend_compile_file`. Any further breakpoints belong on the execute path
(`execute_internal`, the `zend_vm` handlers the loader swaps in), not on the compile hook.

Loader/CPU note: `loader/ioncube_loader_win_7.2.dll` is the **x64** build (machine `0x8664`,
image base `0x180000000`) and cannot load into the 32-bit CLI. The 32-bit build used above is
`scratch/refs/ic72dump-opcodes/runtime/ext/ioncube_loader_win_7.2.dll` (machine `0x14C`,
base `0x10000000`), which is the one all the `0x1xxxxx` RVAs refer to.

## The text layer is base64 — located and proven

Found through IDA Pro (attached session, ~/Documents/decode-anything/loader/ioncube_loader_win_7.2.dll)
driven by REA:

```bash
REA_IDA_MCP_CONFIG=scratch/rea-ida.json rea decompile \
  loader/ioncube_loader_win_7.2.dll 0x18007BA00 --provider ida --format json
```

### Record parser

| Build | Function | Size | Role |
|---|---|---|---|
| x64 | `sub_18007BA00` | `0x753` | record parser / dispatcher |
| x86 | `0x6C340` | — | same function (identical magic list at `0x6C4CF`..`0x6C517`) |

It requires `[ctx+48] >= 0xE`, reads a 14-byte tag and compares it with the constant returned by
`sub_18007EBB0(&unk_1800C5EF8)`. On mismatch it decodes a 5-character `isxdigit`/`tolower` field
(`v15 = 16*v15 + digit`, `-39` for `a`..`f`) into a 20-bit seek offset, seeks, and reads a 4-byte
magic. The dispatch table, read straight off the pseudocode:

| Magic | Bytes as ASCII | Action |
|---|---|---|
| `0x632B5248` | `HR+c` | **base64 mode**: `emalloc`, `sub_180074140(text, len, out)`, then continue parsing |
| `0xDEADC0DE` | — | older record family |
| `0x3FBC2883` | — | older record family |
| `0x882BC103` | — | older record family |
| `0x0217582F` | — | older record family |
| `0x149FEC13` | — | older record family |
| `0x67A6BF45` | — | inner record magic (what the sample decodes to) |
| `0x9EB67AC2` | — | older record family |

For anything in the second group it scans up to 64 dwords for one of
`0x632B5248`(`HR+c`) / `0x566F2B34` / `0x4E577242` / `0x68347930` / `0x7367646D`, rewinds to the
start of the collected segment, and hands it to `sub_18000B830` (x86: `sub_10009BB0`), which is a
buffer allocator plus read; the CR stripping loop (`al == 13`) follows immediately.

### The base64 decoder

| Build | Address | Notes |
|---|---|---|
| x64 | `sub_180073F90` (thunk `sub_180074140`) | `char *in, int len, char *out` |
| x86 | `sub_10065D50` (thunk `sub_10065EC0`, helper `sub_10065D30` maps error codes) | `ecx = in`, `edx = len`, `out` as 3rd argument |
| x64 table | `0x1800A92A0` | 256-byte reverse map, `0xFF` = invalid |
| x86 table | `byte_10093BC0` (VA `0x10093BC0`, RVA `0x93BC0`) | byte-identical to the x64 table |

The x86 pseudocode from IDA (`rea decompile ... 0x10065D50`) states the algorithm literally:
`out[i] = 4 * tab[c]`, `out[i] |= tab[c2] >> 4`, `out[i+1] = 16 * tab[c2]`, and so on, with an
`isspace` skip loop before each character and a `break` on `'='` (61).

### Call site, verified by xref

`rea xrefs` on the 32-bit binary gives exactly two callers of the thunk:

```
0x1006C753  inside sub_1006C340   <- the record parser (the one 0x6D970 calls)
0x1006DE40  inside sub_1006DD70
```

At `0x6C523` the parser compares the 4-byte magic with `0x632B5248` and jumps to `0x6C720`,
which seeks back 4, `emalloc`s `len`, and calls the decoder at `0x6C753`. Right after it
(`0x6C766`) re-reads a 4-byte header from the decoded buffer and XORs it with `0x2853CEF2`.
The other magic group (`0x632B5248 / 0x566F2B34 / 0x4E577242 / 0x68347930 / 0x7367646D`) branches
to `0x6C5CD`, which calls `sub_10009BB0` — that one is a **buffer allocator**, not an inflate
(`v5 = alloc((len & 0xDFFFFFFF) + flag)` then reads `len = alloc(sizeof(out_buffer))`), so the
decompressed-body step is still a separate, unidentified routine.

The table is the **standard** base64 reverse map (`A-Z`→0..25, `a-z`→26..51, `0-9`→52..61,
`+`→62, `/`→63), built as a 256-entry lookup so validation and decoding are one load. Decode:

```c
while (isspace(c = *in++)) ;        // whitespace skipped anywhere
if (c == '=') break;                // '=' terminates the stream
v0 = tab[c]; out[0]  = 4 * v0;
if (c == '=') break; v1 = tab[c]; out[0] |= v1 >> 4; out[1]  = 16 * v1;
if (c == '=') break; v2 = tab[c]; out[1] |= v2 >> 2; out[2]  = v2 << 6;
if (c == '=') break; v3 = tab[c]; out[2] |= v3;
```

### Proof

The sample's text starts with the literal `HR+c`, which **is** the `0x632B5248` base64 marker. Decoding
the blob from that marker with the table above yields **9 699 bytes** whose first dword is
`0x67A6BF45` — the inner record magic, accepted by the same parser on its next pass. Reproduce:

```python
img = pe.get_memory_mapped_image()
tbl = img[0xA92A0:0xA92A0 + 256]        # x64 table at VA 0x1800A92A0
vals = []
for ch in blob:                     # blob = bytes after '?>\n'
    if ch in b" \t\r\n":
        continue
    if ch == 0x3D:                  # '=' ends the stream
        break
    if tbl[ch] < 64:
        vals.append(tbl[ch])
out = bytearray()
for k in range(0, len(vals) - 3, 4):
    a, b, c, d = vals[k : k + 4]
    out.append((a << 2 | b >> 4) & 0xFF)
    out.append(((b & 0xF) << 4 | c >> 2) & 0xFF)
    out.append(((c & 3) << 6 | d) & 0xFF)
```

`base64.b64decode` instead returns 9 700 bytes at a one-byte offset and misses the magic. The loader
skips whitespace *anywhere* in the stream and stops at the first `=` instead of treating the text as
one contiguous block — that difference is why every earlier attempt at the record layer failed.

What the decoded blob is not: a zlib stream. Raw-deflate over `blob[0..512]` at every start offset
produces nothing, so the base64 layer is only the outer text envelope — the binary underneath is
still the encrypted sv5 record, same conclusion as the earlier cipher sweeps.

The helper at `0x49C0` that fires first inside `0x6D970` is a basename/extension comparison, not a
decoder; the `0x6F620` cluster is a `[...]`/`=`-aware pattern matcher used by the licence check.
