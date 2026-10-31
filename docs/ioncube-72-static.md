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
- Main record: offset `0x4`, blob at `0x54`, length 616, record ends at `0x2BC`.
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

## M3 - the sv5 envelope decodes statically (PHP 7.2 sample)

The earlier record-layer attempts read `blob[4..]` as if the payload were one
contiguous stream. It is not: the envelope is a **framed** stream, and the frames
have to be reassembled with the per-file PRNG before anything inflates. Once
that is done the entire envelope opens: header, metadata, and the program blob.

Sample: `binancepay_asli.php` (DHRU Fusion), PHP 7.2 loader.

### Gates

| gate | what is compared | result |
|---|---|---|
| transition | `adler-17(payload[4:transition])` vs transition dword | `0xE4FD6A41` = `0xE4FD6A41` |
| header | `MD4(plaintext)` vs `ROL3(last 16 ciphertext bytes)` | `f7 6f 80 29 b8 38 88 61` = same |
| frame #1 | adler-32 running value vs `0xA0` frame at `0x1FE6` | `0x0884C14B` = same |
| frame #2 | adler-32 running value vs `0xA0` frame at `0x2502` | `0x9AFB4D7F` = same |
| inflate | raw DEFLATE (windowBits -15) reaches BFINAL | eof, no unconsumed input |

Values that fall out of a verified decode:

```
format id       0x4FF571B7        format version 5
seed            0x967A1529        header 168 bytes, MD4 ok
php version     72                php flags 0x00048487
encoder         12.0.2            member id 0x00007B62
bytecode key    0x00364730        owner key 0xE9FC23B1
body seeds      0x05A3AEF6 / 0x8F03ED9E
body            25712 bytes from 9052 framed bytes
frames          75 encrypted chunks, 39 literals, 2 checksums, 0 control
```

### Frame grammar (`sub_1800A1090`)

```
flag < 0x80        encrypted chunk, `second` bytes, XOR low byte of PRNG
flag & 0xE0 == 0x80  one literal byte = `second`
flag & 0xE0 == 0xA0  checksum: 4 escape-decoded bytes starting AT `second`
flag & 0xE0 == 0xC0  literal 0x3C
flag & 0xE0 == 0xE0  no payload, the two header bytes are skipped
```

Two details cost hours and are worth stating plainly.

The checksum field does **not** start after the two-byte frame header. The loader
passes `frame + 1` to the escape decoder (`sub_1800A1050`), so the byte it read as
`second` is the first checksum byte. Reading four literal bytes from `frame + 2`
desynchronises the frame walk a few kilobytes in, which is exactly why earlier
sweeps saw a valid-but-truncated DEFLATE stream.

The running checksum is adler-32 seeded with **0**, not 1, and it covers the raw
frame bytes - the two header bytes plus the still-encrypted payload - for encrypted
chunks and just the two header bytes for the `0x80`/`0xC0` literals. `0xE0` control
frames contribute nothing. With seeded-1 adler nothing matches; with seeded-0 both
frames match to the byte.

### PRNG

`sub_18009D410` builds the generator type 5 used for both the header keystream and
the body frames. Its ring is filled with `a + b` only, and the accumulator folds
back through `-2 - value` on a slot array indexed `slots[i + 4]`, so regeneration
can touch slots `-4..-1`. Constant-for-constant that is the same stream `MT4IC`
already implements: seeded at `0x05A3AEF6` and at the odd seed `0x967A1529` the two
implementations agree on every byte past two full regenerations (9000 and 4200
bytes compared). No second generator is needed - the 7.2 factory differs in
bookkeeping, not in output.

### Reproduce

```
python tools/ic72_static_container.py sample.php --body-out body72.bin
```

The blob opens with a 616-byte block at `+0x54` and lands on the record area at
`0x2BC`, where names appear length-prefixed (`0x11 binancepay_config`). 292
identifier literals are visible in the first pass, so the remaining work is the
sv5 record walker - `OpArrayMetadata`, opcode blocks, and the `0x00364730`
bytecode XOR - not the envelope.

## M3.1 - what the sv5 record area actually holds

The record layer is not opaque, it is just not the 8.x layout. Walking the 7.2
loader rather than guessing gives the read order, and the body then reads as a
sequence of records whose names and literal pools are in the clear.

### Op_array head read order (sub_1800A0090, called from sub_1800A02A0)

`sub_1800A02A0` picks the branch from `php_flags & 0x8000` (dynamic keys) and,
when set, reads `u32 length`, two `u32` key words, then calls `sub_1800A0090`.
The head reads, in this order:

```
u16 name_len, name_len+1 bytes        -> op_array+8 / op_array+0x10 (sub_18009FFC0)
0x14 raw bytes                        -> descriptor handed to sub_180002560
u32                                   -> op_array+0x20
u32                                   -> op_array+0x24
u32 fn_flags (&~0x800)                -> op_array+4
sub_18009E500                         -> arg table
sub_18009E880                         -> reference-return fixup
u32 literal_count                     -> op_array+0x48
literals                              -> sub_18009DFE0: name string + 8-byte key each
u32 num_args                          -> op_array+0x18
u8 construct flag
u32 filename ref (0xFFFFFFFF = none)
```

`sub_18000B830` is the shared length-word reader: value `& ~0x20000000`, plus
one byte when bit 29 is clear. `sub_18009D610` is a two-instruction wrapper,
`mov edx, 14h` then `jmp sub_18000B830` - the 20-byte descriptor above.

### The 616-byte buffer is a stored blob, not the metadata

`sub_1800A02A0` finishes with `sub_18000B830(stream, length)`, then
`sub_18009D630(op_array, buffer, count)`. That function only stores the pointer
and length (`+64`, `+72`), so the buffer is carried into execution untouched.
Treating those bytes as 8.x op_array metadata is what made the checksum gate
fail earlier; the metadata lives on the stream, not in the blob.

Negative results for the blob, each tried and rejected on the sample:

| transform | result |
|---|---|
| raw DEFLATE at offsets 0..20 | no valid stream |
| chunk/escape decoder (`decode_escaped_block`) | not chunked |
| `decrypt_cipher0` with request/owner/body-seed keys | no structure |
| dword XOR with `PRNG6(outer keys)` (+-`request_key`) | no structure |
| reads as 8.x `read_inner_op_array_record` | metadata checksum mismatch |

### What is readable

Identifier names are `u32 length + bytes + NUL`, and literal pools use the same
compact zval grammar the 8.x reader already handles. On `binancepay_asli.php`
the pool at `0x457` decodes to the DHRU plugin configuration array:

```
{"name": {"Type": "System", "Value": "Binance Pay (https://merchant.binance.com/)"},
 "api_key": {"Name": "API Key", "Type": "text", "Size": "120", ...},
 "secret_key": {...}, "merchant_id": {...}, "proxy": {...}}
```

Name records mark the record groups: the main op_array variables
(`params`, `config`, `lng_languag`, `licinfo`, `bppaymentsuccess`,
`entityBody`, `LICENSE`, `_res_proxy`, ...) from `0x9C8`, then per-function
tables for `call_bp_proxy` (`0x3A45`) and `bp_call_api` (`0x4B22`), each with
its own `url` / `data` / `api_key` / `secret_key` locals.

```
python tools/ic72_body_scan.py body72.bin
python tools/ic72_body_scan.py body72.bin --json
```

The open work is unchanged in kind but now bounded: the record walker has to
reproduce the read order above, and the opcode lane has to be derived from the
buffer `sub_18009D630` stores.

## M3.2 - the 7.x buffer cipher, fully reversed

The cipher that carries the stored blob is not AES, not DEFLATE, and not the
8.x lane. It is a two-word LCG with a byte XOR, and the loader's own key
resolver feeds it. Every piece below was read out of the DLL, not guessed.

### The cipher (sub_180001E10)

```
prng = factory(6)                              # sub_18009D540 case 6
state = (seed0(key), seed1(key))               # sub_18009D2E0 stores both words
for i in range(count):
    out[i] = ct[i] ^ BYTE1(prng.next())        # BYTE1, not BYTE0
```

`sub_1800031B0` is the caller: it resolves the key with `sub_180004170`,
decrypts `a1+64` for `a1+16` bytes into a fresh `emalloc` buffer, then sets
`a1+64 = new`, `a1+16 = a1+72`. So the span at `+64` is a two-part buffer:
an already-decoded prefix of `+16` bytes, then ciphertext up to `+72`.

### PRNG 6 (sub_18009D2F0)

```
state1 = (state1 >> 16) + 30345 * (state1 & 0xFFFF)
state0 = (state0 >> 16) + 18000 * (state0 & 0xFFFF)
out    = state0 + rol16(state1)
```

The generator caches the last output and serves it once more on the next call
when the cache flag is set, so a naive re-implementation drifts if that branch
is ignored. `sub_18009D540` also exposes PRNG 4 and PRNG 5 (`MT4IC`), which is
why 7.2 headers and 7.2 bodies do not share a generator.

### Seeds (sub_180007340 / sub_180007390)

`seed0` is a djb2x: `h = 1025 * (h + signed_byte)`, `h = (h >> 6) ^ h`, final
`32769 * ((9h) ^ (9h >> 11))`. `seed1` is murmur3 over the same bytes with seed
31 (`fmix32` tail included). Both take the *key bytes*, so any key change moves
both words.

### Key generation (sub_18000C7C0)

```
key = bytes([0x0D]) + SHA1(material + extra)   # 21 bytes
```

SHA-1 here is the loader's own: `sub_18000BDF0` init, `sub_18000C3E0` update on
64-byte blocks (512 bits at a time), `sub_18000C590` final, 20-byte digest.

### Where the key material comes from (sub_180004170)

`sub_180004170` dispatches on a license mode and fills two out-params, buffer
and length. The modes are runtime lookups, not file constants:

| mode | resolver |
|---|---|
| 1 | `sub_180003570` - 16 bytes from four header dwords, each byte `+1` |
| 2 | `estrdup(*(license+8))` - a plain string already in the struct |
| 3 | `sub_180003AE0` - symbol-table lookup by name |
| 4 | `sub_180004080` - unpack the header license block, then a symbol lookup |
| 5 | `sub_180004140` - `sub_18007E170(*(license+8))` |

The lookup itself (`sub_180003BE0`) walks the PHP symbol table for a zend_string
built from the header name, and falls back to `sub_18000C7C0(name, ...)` with
the SHA-1 keygen when the table has no entry and `flags & 0x200` is set.

`binancepay_asli.php` carries the name `ioncube_event_handler` at header
`+0x4C` (length `0x15`) and `php_flags = 0x00048487` - the dynamic-key bit
`0x8000` is set, so the key is produced by the running application, and the
handler name in the header is exactly the callback the loader expects the
script to register. That is the wall: for dynamic-key files the cipher key is
*not* a function of the file bytes, and no static transform on the 616-byte
blob will resolve it. Non-dynamic files (mode 1 or 2) stay fully static, since
their material is either the header dwords or a plain string in the record.

### Tool

```bash
python tools/ic72_decrypt_span.py body72.bin --offset 0x4C --count 616 \
    --sample binancepay_asli.php          # tries every header-derived candidate
python tools/ic72_decrypt_span.py body72.bin --material <hex> [--shift 8] [--dump out.bin]
python tools/ic72_decrypt_span.py body72.bin --raw-key <hex>
```

`engines/ioncube/body72.py` holds the primitives (`Type6Rng`, `seed0`,
`seed1`, `derive_key`, `decrypt_buffer`, `keystream`) so the record walker can
call the cipher directly instead of re-deriving it.

Cross-check on the sample: the whole header-derived candidate set leaves the
blob at 36-38% printable, i.e. indistinguishable from random, which is the
expected fingerprint of a key that is not present in the file. A non-dynamic
sample is needed to close the opcode lane statically; the record walker itself
is independent of that and can proceed now.

## M3.3 - the sv5 record layout, byte-exact

The record layer is now walked, not guessed: `tools/ic72_record_walk.py` parses
the body and lands on the exact same boundaries the loader does. Two records
parse on `binancepay_asli.php`, and the second one validates every field
because its literal pool is in the clear.

### Framing (sub_1800A02A0, dynamic-key branch)

```
u32 payload_size          the byte count read back at the end
u32 key1                  record key words, per record
u32 key2
  sub_1800A0090 fields ... (see below)
u32 blob_len
blob[payload_size]        ASCII data segment for the record
```

`sub_18000B830(stream, payload_size)` reads the data segment; the second
`u32` before `sub_18009D630` is the length the loader stores alongside it.
The data segment is the record's string/opcode pool, and it is where the
literal text lives (record 2 keeps the whole DHRU config pool there).

### Field order (sub_1800A0090)

```
sub_180003730   u8 flag
                u32 n1, n1 bytes                (empty in both records)
                u32 n2, then n2 * (u32 len + len bytes)
                u32, u32
sub_18009FFC0   u16 name_len, name_len+1 bytes  (0 means no name)
20 bytes        descriptor (sub_18009D610 = B830(20))
u32             op_array +0x20
u32             op_array +0x24
u32             fn_flags (& ~8)
sub_18009E500   per argument: u32 flag, then a string when flag != 0
u32             literal count
sub_18009DFE0   per literal: string + 8-byte key
u32             num_args
u8              construct flag
u32             filename reference, 0xFFFFFFFF means none, else a string
```

`sub_18000B8A0` is the string reader: `u32 word`; a negative word means the
empty string, otherwise the length is `word & 0x9FFFFFFF` and the payload is
`length + 1` bytes when bit 29 is clear.

### What the walker produces

```
#0 0x004..0x2bc A=616  keys=0x4ec3cf8c/0x3481662b  blob@0x054
   name='' fn_flags=0 literals=0 filename=None
#1 0x2be..0x975 A=1575 keys=0x16022aed/0x0e258024  blob@0x34e
   name='binancepay_config' fn_flags=0x8000000
   literals=1 ('configarray', 0x0000000600000001)
   filename='binancepay_config'
```

Two details this settles:

- The main data segment is at `0x54`, not `0x4C`. The `0xFFFFFFFF` and
  `0x268` pair at `0x4C` is the *filename reference* followed by the *blob
  length*, both plaintext. Every earlier attempt to decode "the 616 bytes at
  `0x4C`" started two fields early and chewed on a length word.
- Record 2 carries `fn_flags = 0x08000000` and one literal named
  `configarray`, whose 8-byte key reads back as `0x0000000600000001` - i.e.
  the two small `u32`s we kept seeing between names are literal keys, not
  obfuscation.

### Where the walk stops

The next record does not start at `0x975`; the two bytes at `0x2BC` (`06 00`)
and the bytes at `0x975` belong to the group framing `sub_1800A16E0` drives,
which interleaves op_array groups, class groups (`sub_1800A0920`, with
`u16 method_count - sub_18009D850(...)`) and top-level counts. The walker
covers the op_array case; reproducing the group order is the next step.

```bash
python tools/ic72_record_walk.py body72.bin                 # records from 0x4
python tools/ic72_record_walk.py body72.bin --skip 0x2be    # record 2 only
python tools/ic72_record_walk.py body72.bin --json
```
