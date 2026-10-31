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
                u32 n1, then B830(n1) bytes
                u32 n2, then n2 * (u32 len + B830(len) bytes)
                u32 -> +64
                u32 -> +68
sub_18009FFC0   u16 name_len, name_len+1 bytes  (0 means no name)
20 bytes        descriptor (sub_18009D610 = B830(20))
u32             -> +32, seeds the argument count
u32             -> +36
u32             fn_flags, then `&= ~8`
sub_18009E500   argument table, count from sub_18000C8D0(op_array):
                per argument u32 flag, string when set,
                u32 flag, string when set, then 4 raw bytes
u32             -> +72, the literal count
sub_18009DFE0   per literal: string + 8-byte key
u32             -> +24
u8              construct flag
u32             filename reference, 0xFFFFFFFF means none, else a string
```

`sub_18000B8A0` is the string reader: `u32 word`; a negative word means the
empty string, otherwise the length is `word & 0x9FFFFFFF` and the payload is
`length + 1` bytes when bit 29 is clear.

`sub_18000C8D0(op_array)` is the argument count: `op_array+32`, plus one when
`fn_flags & 0x40000000`, plus one more when `fn_flags & 0x01000000`. Each
argument is 11 bytes minimum - two flag words that may each carry a string,
then four raw bytes for the type hint and default.

Reading the argument count out of `fn_flags` instead of the stream is what
unlocked records 3 to 5: the first two records have zero arguments, so the
byte accounting looked identical either way.

### What the walker produces

```
#0 0x004..0x2bc  payload=616   keys=0x4ec3cf8c/0x3481662b  name=''
#1 0x2be..0x975  payload=1575  keys=0x16022aed/0x0e258024  name='binancepay_config'
#2 0x975..0x3977 payload=11778 keys=0x543db7bd/0x3fb79803  name='binancepay_link'
#3 0x3977..0x496a payload=3855  keys=0x1b085114/0x19a1a159  name='call_bp_proxy'
#4 0x496a..0x646e payload=6456  keys=0x4cabc358/0x5b37e0a7  name='bp_call_api'
```

The only gap is two bytes at `0x2BC` (`06 00`): the `u16` function count that
`sub_1800A16E0` reads between the file-level op_array and the function loop.
Every record after that is back to back, and the body ends at `0x646E` of
`0x6470` bytes.

Three details this settles:

- The main data segment is at `0x54`, not `0x4C`. The `0xFFFFFFFF` and
  `0x268` pair at `0x4C` is the *filename reference* followed by the *blob
  length*, both plaintext. Every earlier attempt to decode "the 616 bytes at
  `0x4C`" started two fields early and chewed on a length word.
- Records 1-4 carry `fn_flags = 0x08000000` and a literal whose 8-byte key
  reads back as `0x0000000600000001` - the two small `u32`s between names are
  literal keys, not obfuscation.
- The 20-byte descriptor is `[literal_count][opcode_count][0][0][0]`:
  `binancepay_link` is `17 / 0x80`, `call_bp_proxy` is `4 / 0x16`,
  `bp_call_api` is `14 / 0x36`, and both counts match the fields that follow.

```bash
python tools/ic72_record_walk.py body72.bin --resync --strings 3
python tools/ic72_record_walk.py body72.bin --json
```

## M3.4 - the body is five records, and four data segments are readable

The body map above is the whole file. There is no class section: the `u16`
after the last record is zero, so `sub_1800A0920` is never entered on this
sample.

The interesting split is in the payloads.

| record | payload | printable | content |
| --- | --- | --- | --- |
| `''` (file level) | 616 | 0.38 | opaque, uniform entropy |
| `binancepay_config` | 1575 | 0.84 | literal pool plus the DHRU config blob |
| `binancepay_link` | 11778 | 0.26 | literal pool plus opcode stream |
| `call_bp_proxy` | 3855 | 0.30 | literal pool plus opcode stream |
| `bp_call_api` | 6456 | 0.25 | literal pool plus opcode stream |

The four function payloads all start with the same eight bytes,
`02 ac df 5b 00 00 00 08`, and the next dword climbs with the record order
(`0x5b28c0c0`, `0x5b2a3820`, `0x5b2d2320`, `0x5b2d25f0`). Those `0x5b......`
words are base plus offset into the encoder's data layout, not heap pointers.

Readable, straight out of the segment:

```
config  binancepay_config | configarray | [4'name[4'Types6'System5126;...
        ... 5'Values43'Binance Pay (https://merchant.binance.com/) ...
        s7'API Key ... 11'Descrip...
link    binancepay_link | params | config | lng_languag | licinfo | paybp |
        bppaymentsuccess | entityBody | LICENSE | _res_proxy | _order_status
proxy   call_bp_proxy | data | token | curl_init | curl_setopt_array |
        CURLOPT_URL | https://api.dhru.com//integration/api/v1/proxy |
        CURLOPT_RETURNTRANSFER
api     bp_call_api | url | data | api_key | secret_key | _entityBody |
        length | headers | payload | json_encode
```

So the literal and identifier layer of every function is plaintext in the
file. Only the file-level payload is opaque, which is consistent with M3.2:
that one segment is produced with the runtime license key.

### The interpreter is versioned, not universal

`sub_180001EB0(mode, variant)` builds the bytecode engine object. Mode 0
installs `sub_180001E10` - the M3.2 buffer cipher - as the decrypt handler.
Modes 1 through 6 instead resolve a handler table through
`sub_18009A7B0(&off_1800B4A00)`, `&off_1800AED10`, `&off_1800B05F0`,
`&off_1800ACC80`, `&off_1800B8F50` and `&off_1800B16D0`.

Each table is one encoder generation's opcode dispatch, so the VM reversal has
to pick the table that matches this file's encoder version (12.0.2) before any
opcode stream can be decoded. That is the next milestone, and it is the only
step between the current state and PHP output: the record layer, the literal
tables, the argument lists and the opcode counts are all known.

## M3.5 - inside a data segment

The segment a record carries is not opaque bytes: it is a dword header
followed by the literal pool and a packed instruction sub-area. The header is
verifiable against the record fields the walker already produces, which is how
the map below is pinned rather than guessed.

| offset | meaning | config | link | proxy | api |
| --- | --- | --- | --- | --- | --- |
| `+00` | magic `0x5bdfac02` | ok | ok | ok | ok |
| `+04` | `fn_flags` | `0x08000000` | same | same | same |
| `+14` | argument count | 0 | 1 | 2 | 4 |
| `+18` | argument count, second copy | 0 | 1 | 2 | 4 |
| `+2c` | literal count | 1 | 17 | 4 | 14 |
| `+30` | opcode count | 1 | 128 | 22 | 54 |
| `+50` | packed sub-area offset | 5 | 36 | 184 | 209 |
| `+60` | packed sub-area size | 2 | 158 | 56 | 88 |

Five independent cross-checks per segment: the magic, `fn_flags` against
record `fn_flags`, the argument count against the parsed argument table, the
literal count against the literal table length, and the opcode count against
the descriptor's second dword. All five agree on all four function segments.

The file-level segment fails every one of them - its first dword reads
`0x7dd785f8`, not the magic - which is the same conclusion M3.2 and M3.4
reached from entropy: that segment is the one produced with the runtime
license key and is not a readable image.

### The packed sub-area

For `call_bp_proxy`, `+50` is `184`, and the bytes at `184` are exactly where
packed four-byte tokens start:

```
00b8  f2 07 b8 00 4b 07 b8 00 8a 07 ba 00 0d 07 ba 00
00c8  65 07 ba 00 98 1f bb 00 02 00 00 00 6d 07 bb 00
00d8  31 1f bc 00 10 00 00 00 dc 1f bc 00 28 00 00 00
00e8  f9 1f bd 00 10 00 00 00 9f 07 bc 00 25 1f be 00
```

Two token shapes alternate: `xx 07 yy 00` and `xx 1f yy 00`, where `xx` is a
payload byte value, `yy` climbs monotonically (`b8`, `b8`, `ba`, `ba`, `ba`,
`bb`, ...) and a bare little-endian operand (`02`, `10`, `28`) is spliced in
between them. The climbing byte is a cursor into the segment, so the tokens
are a delta-coded stream over the payload rather than an instruction array.
The four larger segments end in a table of `(u32 offset, 0xFFFFFFFF)` pairs,
which is the jump/label table for the same stream.

The same field is not the stream start on the other segments - `link` reports
`36` and lands inside a nested descriptor block - so the offset is a
sub-area pointer, not a fixed "instruction area begins here" field. That is
the open question the interpreter will answer, and it is the reason the
segment image below stops at "the payload is structured and its metadata is
exact" rather than claiming an instruction decode.

### Addresses inside the segment

Every remaining dword is either zero or a `0x5b......` value. The same word
`0x5b3b0f60` appears at `+4c` in all four segments, and the words at `+08`
climb with the record order (`0x5b28c0c0`, `0x5b2a3820`, `0x5b2d2320`,
`0x5b2d25f0`). They are the encoder's own address space carried along so the
loader can relocate them, not offsets into the segment.

```bash
python tools/ic72_payload72.py body72.bin --resync
python tools/ic72_payload72.py body72.bin --resync --name call_bp_proxy --dump-instr 96
python tools/ic72_payload72.py body72.bin --resync --index 4 --strings 20
```

### The 20-byte descriptor feeds the op_array directly

`sub_180002140(descriptor, op_array, persistent)` takes the descriptor as five
dwords and stores them straight into the op_array:

```
descriptor[0]  -> op_array+72    literal count
descriptor[1]  -> op_array+76    opcode count
descriptor[4]  -> op_array+160 = 8 * descriptor[4]
                -> op_array+168 = zeroed array of that size
```

So the descriptor is `[literals][opcodes][0][0][table]`, and the only non-obvious
field is the last one, which sizes an 8-byte-per-entry table that the loader
allocates and zeroes. Measured on the sample:

```
<file level>          literals=0  opcodes=2   table=1
binancepay_config     literals=1  opcodes=1   table=0
binancepay_link       literals=17 opcodes=128 table=25
call_bp_proxy         literals=4  opcodes=22  table=17
bp_call_api           literals=14 opcodes=54  table=25
```

The literal and opcode counts match the record's literal table and the data
segment header `+2c`/`+30` on every record, which closes the loop: the record
says how big the function is, the segment's header says the same thing, and
the descriptor says it a third time. The `table` field does not correlate with
either count, so it stays unnamed until the interpreter names it.

## M3.6 Execution model: opcode spec table, handler dispatch, packed op records

The loader does not interpret the payload as its own instruction set. It builds
zend-style op arrays and runs them through a handler table it ships itself. Two
functions in the loader name every piece:

- `sub_18006F1A0` is PHP's `zend_vm_get_opcode_handler`, reimplemented. It reads
  a 32-bit spec word for the opcode, folds in the op's type bytes, and returns
  `handler_table[offset + (spec & 0xffff)]`.
- `sub_18006F0B0` binds the two globals the dispatcher reads: `qword_1800E9848`
  (handler table) = `off_1800DA650`, `qword_1800E9858` (spec array) =
  `dword_1800A8D70`.

### Spec word

```
spec = flags << 16 | base
```

`base` is the first handler slot for that opcode; each flag multiplies the
number of slots, and the offset is accumulated left to right:

| flag | dimension | slots |
|------|-----------|-------|
| 0x01 | `op+29` (op1_type) via `type_map[]` | 5 |
| 0x02 | `op+30` (op2_type) via `type_map[]` | 5 |
| 0x04 | `op+61` via `type_map[]` | 5 |
| 0x08 | `op+31 != 8` | 2 |
| 0x10 | `u32 at op+12 < 12` | 2 |
| 0x20 | `op+60 == 43` / `== 44` | 3 |
| 0x40 | `u32 at op+20 == 147` / `== 136` | 3 |

`type_map` is `dword_1800A91E0`, indexed by the raw type byte, giving 0..4.

### Measured geometry

```
spec array      0x1800A8D70   220 dwords, 199 implemented
type map        0x1800A91E0   7 distinct type bytes
handler table   0x1800DA650   4922 code pointers in .data
```

Opcode 23 is a worked example: `spec 0x004301d7`, base 471, flags `0x43`, so
`5 * 5 * 3 = 75` slots — and opcode 24 starts at exactly 471 + 75 = 546.
Opcodes 1..99 tile the table without a gap, ending at slot 2332. The array ends
at index 220: index 220 begins a byte ramp `00 01 02 03`, which is data, not
spec. Opcodes 0, 199, 202..215 and 217 are zero; 200, 201, 218 and 219 are
`0xFFFFFFFF` (marked unimplemented); 216 holds a stray `1`.

Tooling: `tools/ic72_vm_table.py` dumps the spec table with the slot arithmetic
and reports the tiling check.

### The packed op record is 32 bytes

`sub_18002B670` executes one op and does `*a1 += 32`, and `sub_18006EF30` — the
bad-opcode handler — reports `op[28]`, `op[29]`, `op[30]` and also advances 32.
From those two the record layout is:

```
+00 .. +07   frame data copied as an 8-byte pair
+08          int32 offset into the record area (callee-side copy source)
+12          int32 literal index, 1-based, tested against count at ctx+32
             with 24-byte entries at ctx+40
+16          int32 offset applied to the executor frame
+28          opcode
+29          op1_type
+30          op2_type
+31          result_type
```

Offsets are stored as integers, not pointers, so the record area is position
independent; that is why the payload's `0x5b...` dwords never need relocation.

### The payload does not contain 32-byte records

Brute force over every start offset of every function segment, requiring all
`opcode_count` records to satisfy `op[28] <= 200`, `literal <= lits + 1`,
`type bytes <= 12` and `int32 at +8 % 4 == 0`, returns **zero** candidates for
`binancepay_link` (128 ops), `call_bp_proxy` (22) and `bp_call_api` (54). So the
segment holds a packed encoding that is expanded into these records at load
time, not the records themselves. Locating that expander is the remaining gap
before the stream at `+0x50` can be turned into opcodes.

## M3.7 Record reader: byte callbacks, literal construction, op_array layout

The record parser does not memcpy a struct image. It pulls bytes through a
callback stored at `ctx+168`:

```
(*(ctx + 168))(ctx, dst, n)        raw byte read
sub_18000B830(ctx, n)              allocates, reads n bytes, returns the block
sub_18000B8A0(ctx, &size)          length-prefixed blob (the reader that masks 0x9FFFFFFF)
sub_18009FFC0(ctx, &ptr, &len)     u16 length, then len+1 bytes, wrapped as a string
```

That is why the payload reads like a stream of tokens rather than an array: the
loader walks it with a cursor and decodes as it goes.

### Literal array

`sub_18009DFE0(ctx, op_array)` fills `op_array+80` with `8 * literal_count`
bytes and loops the count from `op_array+72`. Per literal it reads a blob, wraps
it in a zend_string (`refcount 1`, `type 6`, `len`, bytes), and then overwrites
the first eight bytes with a second read of exactly 8 bytes:

```
s[0..7] = *(u64 *) sub_18000B830(ctx, 8)
```

Those eight bytes are `refcount` and `type`, which is exactly the
`0x0000000600000001` word every literal in the sample carries: refcount 1,
`IS_STRING`. M3.5 recorded that word as unexplained; it is a copied string
header, not obfuscation.

### op_array constructor

`sub_180002560(dest, ..., descriptor)` allocates the 224-byte op_array and
installs, in order:

```
+08   48-byte header copy, three 16-byte blocks from the record header
+32   parser callback
+40   (*(uint8 *)callback != 0)
+48   literal table (filled by sub_18009DFE0)
+64   payload buffer
+72   literal count        +76  opcode count
+112  engine               +120 engine word
+160  8 * descriptor[4]    +168 zeroed table of that size
+200  inner struct, +136 set by sub_180002550
```

The 20-byte descriptor is copied, applied, then `efree`d, so it exists only to
size the object. `sub_18009E400(op_array)` runs first and zeroes the tail fields
`+176..+200` before anything is installed.

### Function extents without IDA

`tools/ic72_loader_map.py` reads `.pdata` and reports all 3673 function ranges,
with `--at`, `--range` and `--largest` filters. Decompiling through IDA costs a
300 s round trip per function; this costs nothing and pins down which function
owns an address before spending one.

### Still open

The 32-byte op record builder has not been located yet. The reader family above
suggests the straight-line candidate: one call that reads `32 * opcode_count`
bytes through the `ctx+168` callback and then walks the result. Everything else
in the record — header, arguments, literals, flags — is now accounted for, so
that read is the only unexplained consumer of the segment.

## M3.8 Line map and the instruction word grammar

Two corrections and one measurement.

### +0x50 / +0x54 is the line range, not a stream offset

`+0x50` and `+0x54` hold the first and last source line the function occupies:

| record | lines | opcodes | literals |
|---|---|---|---|
| `binancepay_config` | 5..34 | 1 | 1 |
| `binancepay_link` | 36..181 | 128 | 17 |
| `call_bp_proxy` | 184..206 | 22 | 4 |
| `bp_call_api` | 209..255 | 54 | 14 |

The ranges do not overlap, they ascend in record order, and together they tile
lines 5..255 of the original file. The file-level record (`#0`, 616 bytes, empty
name) is the only one without a range, which fits: it is the pseudo-function that
holds the file-scope statements and its segment is the encrypted one.

Earlier work read `+0x50` as an offset into the payload and started decoding at
`0xb8` for `call_bp_proxy` because `0xb8` happened to be the value stored there.
That was a coincidence of the value also being a valid line number — the
instruction stream starts at `+0x90` for every record.

### Instruction stream

`+0x74` is a fixed seven-word name record: `1, 6, 2, name_len, 0, a, b` — the
`1, 6` pair is a zend_string image (`refcount 1`, `IS_STRING`), the same pair the
literal reader copies out of the stream (M3.7). It is the only `(1,6)` pair in
the payload, so the function name is stored once and referenced by index.

The stream begins immediately after it at `+0x90` and runs to the first
`0xffffffff` word:

| record | stream | bytes | words | tokens | immediates | words/op |
|---|---|---|---|---|---|---|
| `binancepay_config` | `0x090..0x09c` | 12 | 3 | 3 | 0 | 3.00 |
| `binancepay_link` | `0x090..0x4c4` | 1076 | 269 | 234 | 35 | 2.10 |
| `call_bp_proxy` | `0x090..0x1b8` | 296 | 74 | 49 | 25 | 3.36 |
| `bp_call_api` | `0x090..0x2ec` | 604 | 151 | 111 | 40 | 2.80 |

The instruction records are therefore variable length — between two and three
and a bit words per opcode — so the earlier uniform 32-byte stride search over
the payload could never have matched. That negative result is now explained
rather than open.

### Word grammar

Most words are operand tokens:

```
[u8 value] [u8 class] [u16 line]
```

* `class` is one of exactly three values: `0x07`, `0x0f`, `0x1f` — the low *n*
  bits set for n = 3, 4, 5. Nothing else occurs across 397 tokens in four
  records, so this byte is a length or shape marker, not a free operand.
* `line` is a full `u16` and always lands inside the range at `+0x50/+0x54`.
  Every token's line is in range without exception, which is what pins the
  interpretation down: with `call_bp_proxy` the fifty line values observed span
  184..206 and the declared range is 184..206.

Remaining words are raw immediates spliced between tokens: small integers
(`2`, `8`, `0x10`, `0x28`) and, after `class 0x1f` tokens, the value `0x10` in
fourteen of sixteen cases.

### Open

How an opcode boundary is derived from the token sequence. The class alphabet of
three values and the immediate-after-`0x1f` rule are the handles: a `0x1f` token
with a following immediate looks like an operand carrying a payload, and the
`0x0f` tokens form a minority (12/234, 3/49, 9/111) that may mark the slot that
closes a record. `tools/ic72_tokens.py` dumps the stream in order for testing
that against the next candidate rule.

## M3.9 The record builder chain

`sub_18009FC70` is the function that turns a payload record into an op_array.
It is reached from `sub_1800A0620`, which the record dispatcher installs as the
callback at `op_array+32`. Read order inside it, with the reader at `ctx+168`
called directly:

```
sub_18009E240  reads exactly 112 bytes in one call -> the function header
sub_18009DDB0
sub_18009DD90
sub_18009E770
sub_18009ED60
sub_18009DF10  16 * literal_count bytes -> the literal table
sub_18009E110
reader(ctx, &dword, 4)
reader(ctx, &dword, 4)
reader(ctx, dword)            -> a separate blob, freed after sub_18009F710
sub_18009F710  argument table
sub_18009FA20, sub_18009F1B0  finalise, then the temp op_array is emitted
```

That is the whole file-to-op_array path. It also settles a framing question from
M3.6: nothing in this chain ever reads `32 * opcode_count`. The 32-byte record
described from `sub_18002B670` is the VM's own in-memory form, not a structure
present in the payload, which is why every stride search over the payload failed.

### The 112-byte header

`sub_18009E240` performs one 112-byte read and then assigns fields to the
op_array by fixed offset. The mapping, loader-side:

| payload | op_array | note |
|---|---|---|
| `+00..+03` | `+00..+03` | four bytes copied individually |
| `+04` | `+04` | |
| `+08` | `+08` | non-zero gates reading the name entry |
| `+0C` | `+10` | |
| `+10` | `+18` | |
| `+14` | `+20` | argument count, matches the descriptor |
| `+18` | `+24` | argument count, again |
| `+1C` | `+28` | |
| `+20` | `+30` | |
| `+24` | `+38` | |
| `+28` | `+40` | |
| `+2C` | `+48` | literal count, proven three ways |
| `+30` | `+4C` | opcode count, proven three ways |
| `+34` | `+50` | |
| `+38` | `+58` | |
| `+3C` | `+5C` | |
| `+40` | `+68` | |
| `+44` | `+70` | |
| `+48` | `+80` | |
| `+4C` | `+84` | |
| `+50` | `+88` | non-zero gates a second 16-byte entry |
| `+54` | `+90` | |
| `+58` | `+94` | |
| `+5C` | `+98` | |
| `+60` | `+A0` | stored doubled |

`+64..+6F` of the header is never read — the 112-byte read is padded out.

### Entry sizes are 16 bytes

Every table in the record is 16-byte entries, not 24:

* `sub_18009DF10` reads `16 * literal_count` bytes, then for each entry calls
  `sub_18009DEB0(dest, entry[12], entry[8])` and copies `entry[4..11]` over the
  first eight bytes of the new string. Entry layout is
  `[u32][u64 zend string header][u32]`, and the `u64` is
  `0x0000000600000001` — `refcount 1`, `IS_STRING`.
* `sub_18009F710` reads `16 * arg_count`, then `arg_count` bytes, then
  `4 * arg_count` offsets, and stores `2 * offset` into entry `+12`.
* `sub_1800A4CD0` reads one 16-byte entry, hands `entry[8]` and `entry[12]` to
  `sub_1800A4C80`, and copies `entry[0..7]` into the result.

For `binancepay_config` the first entry sits at `+0x74` and reads
`[1, 6][2][17]` — refcount 1, `IS_STRING`, flags 2, length 17, which is exactly
`'binancepay_config'`.

### Correction to M3.8

`+0x50` is tested for non-zero by the loader as a guard before reading that second
16-byte entry, so it is not purely a line number. The tiling of 5..34, 36..181,
184..206, 209..255 across the four records in source order still stands as the
only explanation offered for the values, but the field is also a presence flag
and the two uses have not been reconciled.

### Open

The opcode stream itself. The chain above accounts for header, name, literals,
arguments and one trailing blob; opcodes are the only consumer left, and the blob
read immediately before `sub_18009F710` is the obvious candidate.

## M3.10 The op stream: sub_18009ED60 and sub_18009F1B0

The opcode section is read by `sub_18009ED60`, which `sub_18009FC70` calls with the
container struct. It is three counted reads:

```
u32 opcode_count                       -> container+0x08
u32 word_count                         -> container+0x28
word_count * 4 bytes                   -> container+0x20   the word array
u32 aux_count                          -> container+0x38
aux_count * 5 bytes                    -> container+0x30   five bytes per op
```

`sub_18009F1B0` then expands it. In full:

```
v6 = container+0x08                       opcode_count
op = emalloc(32 * v6)                     the zend_op array
cursor = 0
while cursor < container+0x28:            word_count, not opcode_count
    word = ((u32*) container+0x20)[cursor++]
    opcode = sub_18009E8B0(op, op_index, word, flags, base, ctx)
    if opcode > 0xC5: fail
    push opcode into the handler map
    sub_18009E910, sub_18009E9E0, sub_18009EA30, sub_18009EAA0(literal_count),
    sub_18009EAE0
    op += 32; ++op_index
if (op - start) / 32 != opcode_count: zend_error
```

So the loop bound is the **word count**, the allocation is the **opcode count**, and
the equality of the two after the walk is checked before the op_array is used. A
record that does not divide exactly is rejected, which is why nothing has to be
guessed: the counts and the widths have to close.

### Word fields

The word is `[value:u8][class:u8][line:u16]`, little endian, and each field lands in
a different slot of the 32-byte op:

| word field | slot | meaning |
|---|---|---|
| `value` (byte 0) | `+28` | opcode, xor-decoded when `flags < 0` |
| `class & 0x18` (bits 11..12) | `+20` | result-type selector |
| `line` (bytes 2..3) | `+24` | line number |

`sub_18009E8B0` stores the raw byte at `+28`, then:

```
if (flags >= 0) return raw
mode = ctx+0x10
if (mode >= 3 && raw == 0x95) { base[op_index] = 0 }
result = raw ^ base[op_index]
if (mode >= 3 && result == 0x95) { base[op_index] = 0; return raw }
return result
```

`base` is indexed by **op index**, not by byte offset, so it is the five-byte-per-op
array from `sub_18009ED60`. `0x95` is the escape that means "no key for this op".

`sub_18009E9E0` turns the class byte into `+20`:

| `class & 0x18` | `+20` |
|---|---|
| `0x00` | 0 |
| `0x08` | 1 |
| `0x10` | 60 |
| `0x18` | next word from the array |

That is the answer to the `0x1f` observation from M3.8: `0x1f & 0x18 == 0x18`, so
class `0x1f` is exactly the case that pulls a following word. `0x07 & 0x18 == 0`
and `0x0f & 0x18 == 0x08`, which is why the other two classes are never followed by
an immediate.

`sub_18009EA30` does the same for the line: high half goes to `+24`, and `0xffff`
pulls the next word instead.

### The boundary rule

One op consumes one word for itself plus one word per operand bit set in its spec
entry:

| spec flag | operand |
|---|---|
| `0x0001` | op1 |
| `0x0002` | op2 |
| `0x0004` | result |

So `width = 1 + popcount(spec[opcode] & 7)`, plus one extra word for each word in
the op that carries a `0x1f` class or a `0xffff` line.

`binancepay_config` is the clean check: 1 opcode, 3 words, and its spec entry has
two operands set, so `1 + 2 = 3` and the record closes on the terminator exactly.

`tools/ic72_op_split.py` sweeps a single xor pad over all 256 values and reports
which ones make every record close on its own word count:

| record | words | ops | closes |
|---|---|---|---|
| `binancepay_config` | 3 | 1 | yes, many pads (1 op, so almost anything fits) |
| `binancepay_link` | 269 | 128 | no single pad |
| `call_bp_proxy` | 74 | 22 | pad 178, both escape modes |
| `bp_call_api` | 151 | 54 | no single pad |

Two records closing exactly at their declared opcode count proves the width model.
Two failing proves the pad is **not** a per-record constant, which matches
`sub_18009E8B0`: the key is `base[op_index]`, one byte per op, taken from the
`aux_count * 5` array. The sweep assumed one pad for the whole record and is
therefore only expected to close by luck.

Open: the internal layout of the five-byte entry, and which byte of it is the key.

## M3.11 The rest of the read chain, and where it breaks

Four more readers in `sub_18009FC70`'s sequence, all now disassembled.

### sub_18009DDB0 — the name table

Called with the record context. It reads one `u32` count, clamps it at 0x2710, then
loops building a `zend_hash` with `zend_hash_init` / `zend_hash_str_add`. Each entry
is **two** strings read by `sub_18000B8A0`: a name and a value. The hash is returned
and held by the caller.

This is the resolved-name table — the mechanism that lets a record refer to a
function or class name by index instead of spelling it out.

### sub_18009DD90 — sixteen bytes each

```
result = read_bytes(ctx, 16 * *(int *)(op_array + 92))
*(op_array + 104) = result
```

`op_array+92` is payload `+0x3C`. That field is zero in all four records here, so
this reader consumes nothing and `+104` stays null.

### sub_18009E770 — the argument table

`count = sub_18000C8D0(op_array)`, then `read_bytes(ctx, 20 * count)`. Each 20-byte
entry is

| offset | field |
|---|---|
| `+0` | `u32`, offset of the name string |
| `+4` | `u32`, length of the name string |
| `+8` | `u32`, offset of the default value |
| `+12` | `u32`, length of the default value |
| `+16` | `u8`, flags |
| `+17` | `u8` |
| `+18` | `u8` |
| `+19` | `u8` |

The two `(offset, length)` pairs go through `sub_1800A4C80`, and the results are
stored in 24-byte runtime entries at `op_array+40`. If `+16` is set or a default
value exists, `fn_flags |= 0x10000000`.

### sub_18000B8A0 / sub_18000B930 — the string reader

```
word = u32
if word < 0: empty
length = word & 0xBFFFFFFF
if word & 0x20000000 == 0: length += 1
bytes = read_bytes(ctx, length)
buffer[word & 0x9FFFFFFF] = 0
```

So bit 31 means null, bit 29 means "no terminator was stored", and the length is
masked out of the low 30 bits. `sub_18000B930` is the same call with the length
discarded.

### The break

`sub_18009ED60` reads `u32 opcodes; u32 words; 4*words; u32 aux; 5*aux`. It is
called after the name table and the argument table, so its two counts should sit
immediately before the word array at `+0x90`. They do not.

Measured in all four records, `+0x84` is zero, `+0x88` is one small number and
`+0x8C` is another:

| record | `+0x88` | `+0x8C` | actual words in `+0x90..` |
|---|---|---|---|
| `binancepay_config` | 3 | 4 | 3 |
| `binancepay_link` | 18 | 6 | 269 |
| `call_bp_proxy` | 16 | 4 | 74 |
| `bp_call_api` | 14 | 3 | 151 |

Using `+0x8C` as the word count puts the aux array on top of the word stream and
the rest of the walk explodes. It is not the word count.

What the word array actually is, is settled: `call_bp_proxy` from `+0x130` to
`+0x17C` is a run of words whose line fields climb `0xC2, 0xC3, 0xC4, 0xC5, 0xC6,
0xC7` in order, and `bp_call_api` does the same with `0xE0` throughout. The array is
the whole `+0x90..terminator` span, as M3.10 measured by size.

So two of the counts `sub_18009ED60` reads are still unaccounted for. Either it runs
earlier in the stream than its call site implies, or the reader the walker models is
not the one used for these records. Unresolved, not guessed.

`tools/ic72_record_layout.py` walks a record in this order and prints every span, so
the disagreement is a number on screen rather than a theory. With `--header-args` it
also skips `20 * header[0x14]` before the opcode section, which is what
`sub_18009E770` does; without it the word array lands at `+0x90` for every record.

## M3.12 The record is fully partitioned, and the counts were in the op header

M3.11 recorded a negative: the two `u32` at `+0x88`/`+0x8C` are not the word
count, because using them as such lands the aux array on top of the word stream.
The reason was the offset. Those two words are not a header at all in the larger
records — they are the first eight bytes of the argument table. The op header is
somewhere else, and once it is placed correctly the whole record closes.

### The map

```
0x0000  112       header
0x0070    4       copied to op_array+24
0x0074   16       name entry, a zend string header plus two u32
0x0084    4       name-table count for sub_18009DDB0
0x0088   20*n     argument table, n from sub_18000C8D0
?         8       op header: [ slots, cells ]
?      4*cells    word array, closed by a 0xFFFFFFFF cell
?         4       slot-table byte size, always 3 * slots
?        3*slots  slot table
```

Measured:

| record | args | op header | cells | escapes | slots | terminator | slot table |
|---|---|---|---|---|---|---|---|
| `binancepay_config` | 0 | `0x88` | 4 | 1 | 3 | `0x9C` | 9 |
| `binancepay_link` | 1 | `0x9C` | 265 | 31 | 234 | `0x4C4` | 702 |
| `call_bp_proxy` | 2 | `0xB0` | 65 | 16 | 49 | `0x1B8` | 147 |
| `bp_call_api` | 4 | `0xD8` | 132 | 21 | 111 | `0x2EC` | 333 |

Four for four on three independent checks:

- the word array begins at `0x88 + 20*args + 8`
- the cell at the end of `4*cells` bytes is `0xFFFFFFFF` in every record
- the `u32` field that follows is exactly `3 * slots` in bytes

### What the two header words are

`cells` counts the terminator. `slots = cells - escapes`, where an escape is a
cell whose class byte is `0x1F` or whose line field is `0xFFFF`; those cells
extend the preceding slot instead of starting one. The header's first word is
the slot count and equals `payload[0x24]` in every record, so the same number is
written twice and the two copies agree.

The slot table is three bytes per slot, so a slot that carries more than one
operand still gets one entry. That is the first measurement that ties the number
of `zend_op` structures `sub_18009F1B0` allocates to the file: it uses
`cells` and asserts the expanded count against the header, while the slots are
what the table is indexed by.

### Consequence for the opcode count

`desc[1]` (1, 128, 22, 54) is not the cell count and not the slot count. Against
the slots it gives 1.0, 1.8, 2.2 and 2.1 slots per instruction, which is the
range of one, two and three operand instructions — so `desc[1]` remains the best
candidate for the opcode count, and it is consistent with the minimum-width rule
(`2 * ops <= cells - 1` holds for all four). Not proven by closure yet, because
the opcode byte is still XOR-masked per slot.

`tools/ic72_record_layout.py` prints this map and checks all three invariants.

## M3.13 The record closes, and the string pool proves it

M3.12 read the dword after the word array as a table size of `3 * slots` and
looked for a three-byte-per-slot table. It is not that. It is the **aux entry
count** that `sub_18009ED60` reads, each entry is five bytes, and the count is
three times the opcode count because every opcode carries three operand entries:
op1, op2 and result. Fifteen bytes per opcode.

That makes the section map complete, and the string pool at the end is the
proof rather than an inference: the name entry and every literal entry hold
`(offset, length)` pairs, all relative to the pool, so a wrong offset anywhere
above resolves to garbage text instead of a plausible number.

### The map

```
0x0000  112       header
0x0070    4       copied to op_array+24
0x0074   16       name entry: [refcount, type, offset, length]
0x0084    4       name-table count for sub_18009DDB0
0x0088   20*n     argument table
?         8       op header: [ops, cells]
?      4*cells    word array, closed by a 0xFFFFFFFF cell
?         4       aux count, always 3 * ops
?       5*count   aux array, 15 bytes per opcode
?      16*lits    literal table, entries shaped exactly like the name entry
?      12*consts  constant pool
?         4       unused
?         4       pool size
?       size      string pool
?     16*args2    trailing table keyed by header[0x58]
```

| record | args | op header | ops | cells | escapes | aux | literals | consts | pool |
|---|---|---|---|---|---|---|---|---|---|
| `binancepay_config` | 0 | `0x88` | 3 | 4 | 1 | 9 | 1 | 0 | `0xE9` |
| `binancepay_link` | 1 | `0x9C` | 234 | 265 | 31 | 702 | 17 | 11 | `0x141E` |
| `call_bp_proxy` | 2 | `0xB0` | 49 | 65 | 16 | 147 | 4 | 5 | `0x523` |
| `bp_call_api` | 4 | `0xD8` | 111 | 132 | 21 | 333 | 14 | 6 | `0xAA5` |

`cells = ops + escapes` in every record, and `aux = 3 * ops` in every record.

### Entry shape

Both the name entry and every literal entry are the same sixteen bytes:

```
u32 refcount   1
u32 type       6, IS_STRING
u32 offset     into the pool
u32 length
```

The name entry at `+0x74` and literal table entries are therefore the same
structure, and the pool starts with a two-byte prefix before the first string —
the name sits at offset 2 in all four records.

### Resolution

All thirty-six literals across the four records resolve to printable ASCII, and
they name exactly what the functions touch:

- `binancepay_config`: `configarray`
- `binancepay_link`: `params`, `config`, `lng_languag`, `licinfo`, `paybp`,
  `bppaymentsuccess`, `entityBody`, `LICENSE`
- `call_bp_proxy`: `data`, `token`, `curl`, `response`
- `bp_call_api`: `url`, `data`, `api_key`, `secret_key`, `_entityBody`,
  `length`, `headers`, `x`

That is a check no wrong offset survives. If the arg table, op header, word
array, aux array or literal table were mis-sized by even four bytes, these
strings would be rubble.

### Correction to M3.12

`ops` is `payload[0x24]` — 3, 234, 49 and 111 — and it is written twice, once in
the header and once in the op header. `desc[1]` (1, 128, 22, 54) is **not** the
opcode count. M3.12's claim that it was the best candidate is withdrawn.

`tools/ic72_record_layout.py` now prints the full partition and resolves every
literal against the pool.

## M3.14 The aux array is three operand descriptors per opcode

`sub_18009E910` is the consumer, and it settles the shape. It is called once per
opcode and reads up to three five-byte entries, each shaped

```
u8   operand type    1 IS_CONST, 2 IS_TMP_VAR, 4 IS_VAR, 8 IS_UNUSED, 16 IS_CV
u32  node index
```

gated by the opcode's flags:

| gate | slot | loader field |
|---|---|---|
| `0x100` | operand 1 | type `+31`, node `+16` |
| `0x200` | operand 2 | type `+29`, node `+8` |
| `0x400` | result | type `+30`, node `+12` |

When a gate is clear the type is written as `8` (`IS_UNUSED`) and no bytes are
consumed. In this sample all three gates are set on every opcode, so the array is
consumed at exactly fifteen bytes per opcode, which is why the count is `3 * ops`
and the literal table behind it lines up.

The type alphabet came out of the data, not out of the disassembly: every type
byte in all four records is one of `1, 2, 4, 8, 16`, and nothing else.

### Reading one opcode

`binancepay_config`, three opcodes:

| op | value | line | operand 1 | operand 2 | result |
|---|---|---|---|---|---|
| 0 | `0x71` | 8 | `IS_UNUSED` 0 | `IS_CV` 0 | `IS_CONST` 0 |
| 1 | `0xF0` | 33 | `IS_UNUSED` 0 | `IS_CV` 0 | `IS_UNUSED` 0 |

The value byte is still masked, so the opcode names are not final, but the
operands are decoded.

### The mask path

`sub_18009F1B0` passes `*(int *)(op_array + 4)` to `sub_18009E8B0` as the flag
that decides whether to mask. Positive means the opcode byte is used raw;
negative means it is XORed with `op_array[64][op_index]`. `sub_18009E8B0` also
zeroes that byte and returns the raw value when the decoded opcode is `0x95` and
the version field is at least 3.

`op_array + 64` is written in two places:

- `sub_18009E240` stores a header field there
- `sub_18009FA20` stores a freshly built array of `ops + 1` `u32` read through
  `sub_18009CA60`, but only when `payload[0x04] & 0x2C80` is set

In this sample `payload[0x04]` is `0x08000000`, so `0x08000000 & 0x2C80` is zero
and the built array never happens. Whatever mask is in play here comes from the
header field, not from the stream.

### One open point

Grouping the word array by the class/line escape rule yields `ops - 1` groups in
every record, and the fixed `0xFFFFFFFF` word that closes the array is itself the
last opcode slot. So either the escape rule needs the sentinel carved out, or the
last opcode has no operands and carries the terminator. Both readings are
consistent with the byte counts; nothing yet separates them.

## M3.15 The class byte is a flag byte, and the walk closes

M3.14 left the word walk one group short in every record. The missing piece was
in the escape test itself: `class & 0x18` is truthy for `0x0F`, and `0x0F` is not
an escape. The loader tests the pair, not either bit.

`sub_18009E9E0` takes the word's low sixteen bits, masks `0x1800`, and switches:

| flags | stored at `+20` |
|---|---|
| `0x0000` | `0` |
| `0x0800` | `1` |
| `0x1000` | `60` |
| `0x1800` | the next word |

`sub_18009EA30` takes the same low sixteen bits: `flags & 0x800` stores line `0`,
otherwise the line is `word >> 16`, and a line of `0xFFFF` consumes one more word.

Both masks sit on bits 8..12 of the word, so **the second byte is the flag byte**
and the third and fourth are the line. The class values the loader computes map
straight onto the second byte's bits 3 and 4. The full byte:

| bit | mask | meaning |
|---|---|---|
| 0 | `0x01` | operand 1 present, five aux bytes, type to `+31`, node to `+16` |
| 1 | `0x02` | operand 2 present, type to `+29`, node to `+8` |
| 2 | `0x04` | result present, type to `+30`, node to `+12` |
| 3 | `0x08` | line suppressed, stored as `0` |
| 4 | `0x10` | class selector, paired with bit 3 |

Bits 3 and 4 together mean the class is the next word. Bits 0..2 are always set
in this sample, which is why every opcode carries exactly three aux entries and
the array is consumed at fifteen bytes per opcode, never less.

### The walk, byte exact

`tools/ic72_op_walk.py`, escape test `(class & 0x18) == 0x18`, stop at `cells`:

| record | ops | cells | walked | word cursor | aux bytes |
|---|---|---|---|---|---|
| config | 3 | 4 | 3 | 4 | 45 |
| link | 234 | 265 | 234 | 265 | 3510 |
| proxy | 49 | 65 | 49 | 65 | 735 |
| api | 111 | 132 | 111 | 132 | 1665 |

All four land on `ops` opcodes, on `cells` words, and on `15 * ops` aux bytes. No
spec table is needed for widths. The fixed `0xFFFFFFFF` word is not an opcode; it
is the extension word of the final opcode, which is why `cells = ops + escapes`
counts it.

### The operands agree with the argument table

The first opcodes of each record read `op1 = IS_CV`, one per declared argument:

| record | arguments | first opcodes |
|---|---|---|
| config | 0 | none |
| link | 1 | `CV(0)` |
| proxy | 2 | `CV(0)`, `CV(1)` |
| api | 4 | `CV(0)`, `CV(1)`, `CV(2)`, `CV(3)` |

That is the receive sequence for the declared parameters, counted exactly. The
operand half of the decode is therefore correct, independently of the opcode
names.

### The mask, in assembly

`sub_18009E8B0` at `0x18009E8B0`:

```
mov  byte ptr [rcx+0x1c], r8b     ; store the opcode byte first
test r9b, r9b
jns  0x18009E909                  ; flags non-negative -> return the byte raw
...
movzx eax, byte ptr [r10+rdx]     ; base[index]
xor   al, byte ptr [rcx+0x1c]     ; opcode ^ base[index]
```

`r10` is the opcode index, `rdx` is the base pointer, so the mask is exactly
`stored ^ base[index]`, one byte per opcode. `0x95` is special: the loader zeroes
`base[index]` and returns the stored byte unchanged, but only when the version
field at `context + 16` is at least 3.

`base` is `op_array + 64`. Two writers:

- `sub_18009E240` stores a sign-extended header dword from `payload + 0x28`
- `sub_18009FA20` stores `malloc(4 * (ops + 1))` filled by `sub_18009CA60` from a
  reader at `context + 40`, gated on the compiler flags having `0x2C80`

In this sample `payload + 0x28` is `0x5B28B120`, `0x5B2D0000`, `0x5BA4B200`,
`0x5B2D5000` - encoder address-space values, not pointers here. So the base array
must come from the builder, not from that field. `sub_18009CA60` reads four bytes
through the reader and hands them to `sub_18009C9E0`, which XORs a keystream byte
in when `reader + 48` is set. The base array is therefore cipher material, not
plaintext in the payload.

### Where the mask falls out

The stored byte for the first receive opcode of each record:

| record | stored | count |
|---|---|---|
| link | `0xA0` | 1 |
| proxy | `0xF2`, `0x4B` | 2 |
| api | `0x3F`, `0xA8`, `0x34`, `0xFB` | 4 |

Those seven stored bytes must all decode to the same opcode, which pins seven key
bytes at once. Under the cipher hypothesis the key sequence is keystream output,
so the seven keys can be checked against the generator instead of searched.

## M3.16 One field decides both the build and the mask

`sub_18009FA20` is called from `sub_18009FC70` line 96 with the same context that
`sub_18009F1B0` receives. Its first instruction reads that context's flag word:

```
mov  r13d, dword ptr [rcx + 4]
test r13d, 0x2c80
jne  0x18009fa5a                  ; build the base array
mov  dword ptr [rdx + 0x20], -1
mov  dword ptr [rdx + 0x14], -1
ret
```

`0x2c80` is bits 7, 10, 11 and 13. Bit 7 is exactly the sign bit of the low byte
that `sub_18009E8B0` tests with `test r9b, r9b; jns`. So the build and the mask are
driven by one flag, and they switch on together. A record with the mask off has
no base array at all, and its stored opcode bytes are already final.

### The base array

Inside the branch: `malloc(4 * (ops + 1))`, then `ops + 1` u32 values from
`sub_18009CA60(readers[context + 40])`, stored at `op_array + 64`. `CA60` reads
four bytes through the reader's function pointer at `+24` and hands them to
`sub_18009C9E0`, which XORs keystream material in when `reader + 48` is set.

`context + 40` is a cursor into an array of 24 byte entries, advanced by 24 bytes
in `sub_18009E880` when `context + 4` has `0x40000000`. It is not a byte stream.

`sub_18009E8B0` indexes the base **as bytes**, one per opcode index, so only the
first `ops` bytes of the built array are ever read - one quarter of what is
allocated. Whatever the reader produces, the mask consumes it as a flat byte
string.

### What the base is not

Three negative results, each cheap to re-run:

- not plaintext in the payload: the four receive bytes of `api` pin the
  keyset delta `0x97, 0x0B, 0xC4` regardless of the opcode, and no four
  consecutive bytes anywhere in the 25712 byte body carry that delta
- not keystream: 600k bytes from the `api` record key at shifts 0, 8, 16 and 24
  hold no such window
- not the header's other material: the same scan over all twenty ordered pairs of
  `owner_key`, `member_id`, `bytecode_xor_key`, seed, format and the two
  `config` record keys, four shifts each, holds no such window either

So the base bytes are ciphertext that lives outside the record payload, or
material produced by a generator seeded from something not yet identified.

### Operand nodes are ordinals, not literals

The receive opcodes read `op1 = IS_CV(i)` in argument order and `op2 = IS_UNUSED`
with a node of `i + 1`. `IS_CONST` operands do index the literal table, one based:
`config` op2 reads `CONST(1)` and resolves to `"configarray"`, `link` op2 reads
`CONST(3)` and resolves to `"lng_languag"`. `tools/ic72_op_walk.py` now resolves
`IS_CONST` nodes inline and leaves the rest as raw ordinals.

## M3.17 The mask family is xorshift, but not a chain

`sub_18009D040` is the assignment that turns a bare object into a reader: it
stores `sub_18009D020` or `sub_18009D000` at `object + 24` depending on one flag.
Those are the two pure 32 bit xorshift steps `sub_18009CA60` calls.

The surrounding family, all recovered:

| function | operation |
|---|---|
| `sub_18009CFF0` | `69069 * x + 1234567` |
| `sub_18009D0D0` | `x = 69069 * x + 123`, `s = xorshift(s)`, `array[i] = x + s` |
| `sub_18009D060` | the xorshift step applied `seed % 9` times |
| `sub_18009D410` | 72 byte context, inner state `{4096, 4097, 1236789, 521288629, 362}` and five entry points |

`sub_18009D0D0` is the array filler: count at `+0`, LCG seed at `+8`, xorshift
state at `+12`, step function at `+24`, array at `+32`, and it writes
`array[i] = lcg + xorshift` for `i < count`, with `xorshift` fed back through
`+12` every round. Two independent streams summed.

### Why the chain sweep fails anyway

The natural reading is that `CA60` feeds the step function its own previous
output, making the whole mask array a chain from one starting word. The receive
run pins that start: in each record the first `args` opcodes are the same
opcode, so their stored bytes XOR one value, giving
`base_u32[0] = stored_le ^ opcode * 0x01010101`.

`tools/ic72_mask_chain.py` sweeps all 198 opcodes for `binancepay_link`,
`call_bp_proxy` and `bp_call_api` and requires every later opcode to stay inside
`0..0xC5`. Survivors: **zero** in all three.

A wider sweep is also zero: six step compositions (`a`, `b`, `aa`, `bb`, `ab`,
`ba`), a seventh using `D060`'s xorshift, plus 0 to 3 pre-applications of the
step and both byte orders - `0 / 0 / 0` survivors again.

So the array is either fed from two streams at once, the way `D0D0` does it, or
seeded per word from somewhere else. It is not one chain.

### Three more negatives

- not a static table: the pinned delta for `api` is `97 0B C4`; no four
  consecutive bytes in the 995840 byte loader carry it
- not payload plaintext (M3.16)
- not keystream of the record or header keys (M3.16)

### What this leaves

`base` is built from `ops + 1` u32 values through a xorshift step into a byte
array that is only ever read as its first `ops` bytes. The step is known. What is
missing is the seed, and no file-local material tested so far produces it. Until
the seed source is identified, the opcode byte stays masked and the operand half
of every opcode remains the only trustworthy output.

## M4.0 The runtime path already finishes this file

The static work in M3.1 through M3.17 was never the only route. `engines/ioncube/
runtime_dump.py` drives the vendored PHP 7.2 bundle at
`scratch/refs/ic72dump-opcodes` (PHP 7.2.34 NTS x86, `php_opcodedump.dll`,
`ioncube_loader_win_7.2.dll`) and reads the op arrays the loader builds in
memory. `available_versions()` reports `[71, 72, 74]`.

Run on `binancepay_asli.php`:

```
python decompile.py binancepay_asli.php -o out --php-version 72
    runtime opcode dump: PHP 7.2
    -> Output saved: bp72_out (5039 bytes)
    [+] Validation: PASS (valid PHP)
```

Five op arrays, four functions and the main block:

| op array | opcodes |
|---|---|
| main | 11 |
| `binancepay_config` | 3 |
| `binancepay_link` | 234 |
| `call_bp_proxy` | 49 |
| `bp_call_api` | 111 |

Those four counts are exactly what `tools/ic72_op_walk.py` derives from the raw
payload, which makes the static walk an independent check on the loader rather
than a substitute for it.

The emitted file decodes the file-level 616 byte segment too: the main block
opens with `exit('<h1 ...>Restricted Access</h1>')`, so the block M3.x could not
touch from file bytes alone is resolved at runtime like everything else.

Output is `sha1 97EB984CB848BFA3DA99B46EDC07C2ADC2C1F463`, byte identical to the
reconstruction already sitting beside the sample. The decode was already
complete; what was missing was the record of how to reproduce it on demand.

### Rule going forward

For any ionCube sample with a runtime bundle for its PHP version, run the bundle
first. Static reversing is for versions with no bundle, for the segment the
runtime refuses to load, and for the record of what the bytes mean.

## M4.1 The mask is not in the file, and now that is measured, not assumed

M3.17 could only test guesses. The runtime dump gives ground truth: XOR each
`stored` payload byte with the opcode the loader actually produced and the mask
array falls out exactly.

`tools/ic72_mask_truth.py`:

| record | mask bytes | words | distinct |
|---|---|---|---|
| config | 3 | 0 | 0 |
| link | 234 | 58 | 58 |
| proxy | 49 | 12 | 12 |
| api | 111 | 27 | 27 |

Every word distinct. First sixteen bytes:

```
link   9f f4 ff 2d d5 9b 7f af 48 b2 41 a6 3e cc 31 99
proxy  cd 74 b1 8e 43 a3 2f 52 9b 9a d7 46 dc 08 f8 80
api    00 97 0b c4 2c 80 d1 f6 ef 25 80 ca 0c ce 06 00
```

Note `api` opens `00 97 0b c4`: the receive run decodes to opcode 63, so the
pinned delta from M3.17 was right, the start was not.

### Tested against real data, not guessed

| hypothesis | link | proxy | api |
|---|---|---|---|
| `u[i+1] = 69069*u[i] + 123` | 0/57 | 0/11 | 0/26 |
| `u[i+1] = xorshift_a(u[i])` | 0/57 | 0/11 | 0/26 |
| `u[i+1] = xorshift_b(u[i])` | 0/57 | 0/11 | 0/26 |
| record keystream, 4 shifts, both key orders, 300k bytes | no | no | no |
| present in the decoded body | no | no | no |
| present in the raw encoded file | no | no | no |

The file search went down to four bytes and still found nothing, so the array is
not stored anywhere in the artifact by any packing we tested.

### Why that closes the static route for this sample

The mask cannot be random per load - the stored bytes would then decode to a
different program every time. It must be a deterministic function of file
material. The only file material never accounted for is the 616 byte segment at
`0x54..0x2BC`, and that segment is produced by the application at runtime in this
sample (the key resolver `sub_180004170` takes the dynamic path).

So the mask is a function of the license-key-encrypted segment. Static decoding
cannot reach it here; runtime decoding does not need to.

### What the static path is still for

1. versions with no runtime bundle
2. samples whose keys are file local (resolver modes 1 and 2) - there the segment
   is derivable and the mask with it
3. the record of what every byte means, which is what made this conclusion
   provable instead of a hunch

`ic72_mask_truth.py` also gives us a harvester: run it on any sample we can
execute and the `(stored byte, true opcode, mask byte)` triples accumulate. Given
enough of them, the derivation stops being a guess even for the dynamic samples.

## M4.2 Static decode, measured instead of argued

`tools/ic72_static_dump.py` decodes a body the way the artifact actually permits:
every field except the opcode byte, no invention.

### What it gets exactly

`walk_record` against the payload, checked against the runtime dump:

| record | word cursor | aux bytes | operands matching loader |
|---|---|---|---|
| config | 0x8C cells | 45/45 | 3/3 |
| link | 265/265 | 3510/3510 | 234/234 |
| proxy | 65/65 | 735/735 | 49/49 |
| api | 132/132 | 1665/1665 | 111/111 |

397 of 397 operand descriptors agree with the loader - type and node - and the
`IS_CONST` nodes resolve to real source strings (`lng_languag`, `licinfo`,
`entityBody`, `_invoice_id`, `OrderURL`). Class byte, line number, extension
words, literal table: all exact. That half of the decoder is finished, not
pending.

### What it cannot get

The opcode byte is `stored ^ mask`. The mask is 3/234/49/111 bytes so far
recovered only by having the runtime answer, and M4.1 measured that the array
appears nowhere in the artifact, is not keystream from any record or header key,
and continues from no LCG and no 8-bit xorshift family. A wider sweep - 28 seeds
derived from the header and every record key, four byte lanes, 400k bytes each -
also misses.

Guess from operand shape, measured leave-one-record-out (train the
`(operand types, class)` -> opcode map on three records, predict the fourth):

| held out | exact | wrong | unseen shape |
|---|---|---|---|
| config | 0/3 | 3 | 0 |
| link | 100/234 (43%) | 85 | 49 |
| proxy | 39/49 (80%) | 4 | 6 |
| api | 73/111 (66%) | 25 | 13 |

62% overall, per-opcode, with training data we only obtain by running the loader.
A decoder at 62% is not a decoder.

### Verdict

For this sample static decoding stops at the opcode byte, and the reason is
structural: the mask is a deterministic function of file material that this
sample produces at runtime (the resolver takes the dynamic path, so the 616 byte
segment is generated by the application). Static reaches everything the encoder
wrote in the clear and nothing the loader regenerates in memory.

Static is not dead - for a sample whose keys are file local the segment is
derivable, and with it the mask. Those samples decode fully offline. This one
does not, and no amount of further reversing changes that without the key.

## M4.3 Why PHP 8 decodes statically and 7.2 does not

Not a version difference in difficulty. A difference in where the seed is stored.

PHP 8.x (`build_php81_opcode_xor_stream`, serialization v15):

```
key_bytes[i] = (PRNG6(seed_a, seed_b).next() ^ request_key) lane byte
opcode       = key_bytes[i] ^ raw_opcode
seed_a, seed_b = outer.outer_key_words[0], [1]
```

`outer_key_words` are words the dynamic main record carries in the artifact, and
`request_key` is read from the file too. Every input to the mask is file data, so
the mask is derivable and the opcode isn't needed from outside. That is the whole
reason the 8.x decompiler is static.

PHP 7.2 (`sub_18009D0D0`):

```
a2[2] = LCG seed          set by sub_18009CFF0 at load
a2[3] = xorshift state    set by sub_18009D060 at load
array[i] = (69069*a2[2]+123) + xorshift(a2[3])
```

The structure is the same idea - a two-stream PRNG whose sum lane becomes the
mask. What differs is the plumbing: the 7.2 seeds are written at load time from
the license segment, not read from the record key words.

Measured against real mask bytes recovered from the runtime, with the 8.x style
constant XOR per dword applied and 64 stream offsets and both key orders tried:

| record | constant-key dword match |
|---|---|
| config | none |
| link | none |
| proxy | none |
| api | none |

So the 7.2 record keys are not the mask seed, and no amount of translating the
8.x routine across will make them the seed.

Same encoder family, though: 7.2 has the `0x95` no-key escape in `sub_18009E8B0`
and 8.x v6+ has the `0x95` sentinel in `_b3c0_opcode_sentinel`. Identical
sentinel, different seed source.

Short version: 8.x ships the key in the file. 7.2 ships it in the licence.

## M4.4 The 32-bit loader, live: the 69069 family is not the mask

The build that actually runs is x86. `ioncube_loader_win_7.2.dll` in
`scratch/refs/ic72dump-opcodes/runtime/ext` is PE32, image base `0x10000000`,
and ships an IDA database beside it. Every routine below is that build.

### Recovered, executed, and observed

| RVA | semantics |
|---|---|
| `0x100890D0` | `eax = ecx * 69069 + 1234567` |
| `0x100890E0` | xorshift A: `x^=x<<13; x^=x>>17; x^=x<<5` |
| `0x10089100` | xorshift B: `x^=x>>9; x^=x*2; x^=x>>7` |
| `0x10089120` | `[edx+0x14] = (ecx & 1) ? A : B` |
| `0x10089140` | xorshift C, `(ecx % 9) + 1` rounds |
| `0x10089190` | generator, context `[0]=count [4]=cursor [8]=lcg [0xc]=xs [0x10]=? [0x14]=fn [0x18]=array` |
| `0x10089220` | `lcg = 69069*lcg + 123; xs = fn(xs); array[i] = lcg + xs` |

Two facts fall out that the x64 read could not settle:

1. **Both streams come from one seed.** `CFF0` and `D060` are not two
   independent inputs - the LCG seed is `69069*S+1234567` and the xorshift state
   is `C^(S mod 9 + 1)(S)`, with the A/B variant chosen by `S & 1`. One 32-bit
   seed drives the whole array.
2. **It is called three times, always with `count = 4096`.** Observed seeds:
   `0x967A1529`, `0x05A3AEF6`, `0x8F03ED9E`. The first is the file header seed
   verbatim, so this family is file-seeded.

### What that rules out

The 4096-dword pools were dumped from memory (16 KB each) and searched for the
recovered mask bytes: no 8-byte window, and no stride mapping (lanes 0-3, steps
1/2/3/4/8/-1, every offset). The opcode mask is **not** taken from these pools.

So M3.17's premise was wrong: the `69069 + xorshift` family that `sub_18009D0D0`
runs is a general 4096-word random source with a cursor, not the opcode mask
generator. It is seedable from the file, which is why it looked like the answer.

### Next target

The mask is written to the op-array local struct and read back at `+64` by the
`E8B0` twin. Hook the x86 `E8B0` consumer, take its `base` pointer, and walk one
frame back to whoever filled it. That is the only remaining unknown.

`tools/ic72_mask_hook.js` holds the working hook set; `ic72_mask_hook_run.py`
drives `php.exe` from the vendored runtime with `scratch/hook_wrapper.php` to keep
the process alive long enough for the module observer to land.

## M4.5 The static decoder is finished; only the mask input is missing

`tools/ic72_static_dump.py --mask <json>` now emits the full program: word walk,
class byte, line, operands, literals, and opcodes `stored ^ mask`. Given the mask
file it prints **397 of 397 slots with a known opcode** for
`binancepay_asli.php`, and the numbers match the runtime dump byte for byte.

```
python tools/ic72_static_dump.py scratch_body72.bin --mask scratch/bp72.masks.json
slots printed with an opcode: 397
slots still unknown     : 0
```

So the pipeline is not missing a stage. It is missing one 32-bit number per
record, and everything downstream already works.

### Negative results that narrowed the seed

The mask bytes are not in the recovered 4096-dword pools, with or without a
stride (four lanes, steps 1/2/3/4/8/-1). They are not the 69069 family output
under the observed seeds, and the XOR of mask against that family shows no
period under 20. The mask byte stream itself has no period under 20 either.

### Live memory

The mask is not present in the process in plain form after the op arrays are
built: a scan of all 102 writable ranges for the first sixteen known mask bytes
of api, link and proxy missed on all three. It is built, applied, and released,
which is why static analysis has nothing to point at and why the writer has to be
caught in the act rather than read afterwards.

### Helper that exists now

`tools/ic72_seed_brute.ps1` brute forces the seed against the family model with
`Add-Type` C# (no compiler on this box), four lanes, 2^32 seeds, checked against
eight mask bytes. If the family is right the seed falls out; if it is wrong the
negative is equally useful because it retires the model for good.

## M4.6 The mask source object, found

The x86 loader implements the opcode mask as a *repeating buffer with a cursor*,
which is exactly the `C9A0` "repeating cycle byte" M3.16 described from the x64
build. Three tiny routines, RVA base `0x10000000`:

```
0x10088BC0  next():   al = buf[[0x20]]
                      cursor wraps: [0x20] = (cursor == len-1) ? 0 : cursor+1
0x10088BF0  decrypt(stored):  [0x18] ? next() ^ stored : stored
0x10088C10  set_key:  __fastcall(this=ecx, buf=edx, len=[esp+4])
                      [0x18]=buf  [0x1c]=len  [0x20]=0
```

So mask[i] = buf[i mod len]. Not a PRNG stream: a lookup table of arbitrary
length that the loader carries around. That is why no recurrence fits - the
array is data, not output.

Hooked live, `0x10088BF0` fires constantly with `[0x18] == 0`, i.e. the no-key
path returning the stored byte unchanged. The call sites that matter are the ones
where `set_key` has run first, and `0x10088C10` did not fire in that run, so the
instrumented instantiation is the unkeyed one.

### What this changes

The search space collapses. There is no seed to brute force for the mask itself -
there is a buffer to read. Hook `0x10088C10` on the instantiation that serves the
op array, take `buf`/`len`, and the mask is in hand. `len` should be one of
111/234/49/3 for this sample; that is the filter to apply.

The 69069 family (`0x100890D0`..`0x10089190`) is confirmed to be a separate
4096-word random source: its callers are `0x88C38` and `0x8CCEC`, both unrelated
to `set_key`.

## M4.7 The 69069 family is retired, by exhaustion

`tools/ic72_seed_brute.ps1` ran the full 2^32 seed space against eight known
mask bytes of `bp_call_api`, lane 0:

```
lane 0 : no seed in 2^32 (151.2s)
```

So the mask is not the output of `0x100890D0`..`0x10089190` under any seed. That
closes the family M3.17 proposed and M4.4 found running: it is a 4096-word random
source, full stop.

### The mask looks like data, not output

Recovered mask bytes per record, distinct count against slot count:

| record | distinct mask bytes | slots |
|---|---|---|
| config | 3 | 3 |
| link | 152 | 234 |
| proxy | 46 | 49 |
| api | 94 | 111 |

No period under 64, under any of xor / sub / sub-reversed / add against the true
opcodes. A per-record table of random bytes is what a mask with those statistics
is; a formula would leave repetition somewhere and there is none.

### The consumer shape is right, the instantiation is not

`0x10088BF0` (XOR the next buffer byte into the stored opcode, guarded by the key
flag at `+0x18`) ran **10029 times with `keyed=0`** in a full load. Every call took
the no-key path. `0x10088C10`, the installer, never ran at all.

So that pair is a generic keyed byte source used elsewhere; the op array's mask
goes through a different routine in this build. Everything M4.6 measured about the
shape still holds - buffer, length, wrapping cursor - but the address is wrong.

### Where that leaves static

Operands, lines, literals, class bytes, cursors: complete and verified 397/397.
Opcodes: one buffer of random bytes per record, produced by a routine not yet
located. The pipeline consumes a mask and emits the full program
(`ic72_static_dump.py --mask`), so locating that routine finishes the static
decoder without any further work downstream.

## M4.8 The E8B0 twin, found and then ruled out

The x64 `sub_18009E8B0` twin in the 32-bit build is at RVA `0x100897D0`.
Disassembly matches the decompiled x64 body line for line:

```
0x100897D0  decode(self=ecx, index=edx, base=[esp+4])
              bl = self->[0x18]
              if (bl == 0x95 || bl == 0x8E) { base[index] = 0; return }
              al = base[index + index] ^ bl        ; base + edx
              if (al == 0x95 || al == 0x8E) { base[index] = 0; return }
              self->[0x18] = al                    ; mask byte chains forward
              return
```

Two sentinels, `0x95` and `0x8E` - the second one is the piece the x64 reading
missed. The mask byte is not a parameter; it is carried on the object at `+0x18`
and replaced by each result, so the sequence is a running XOR chain.

### Only one of its two callers ever runs

`0x100897D0` has exactly two direct callers:

```
0x1008AD9E   the string/text layer   -> runs, 11 times
0x1008DC6E   the op array layer      -> never runs for this sample
```

Hooked live, every call returns to `0x1008ADA3`. The `0x1008DC40` function that
contains the op array caller was never entered at all, and the `0x1008E3B4` store
that installs the mask pointer on the 0x88-byte decoder context never executed
either. So this sample does not take that branch: whatever decodes its opcodes is
a different routine.

### The 11 bytes were the wrong 11 bytes

Dumping the buffer behind those calls gives

```
e1 e6 b3 ec 20 60 50 38 60 0b e1 72 6e a4 49 a1 ...
```

for eleven entries, with the per-entry structs spaced 28 bytes apart and each one
carrying version `3` at `+0x14`. That looked like plumbing for eleven opcodes, but
the surrounding structure holds ASCII the same way - this is the text layer
walking a decoded blob, and the eleven entries are not main's opcode table.

### Consequence

The `+0x18` running-XOR chain is real and is not the opcode mask. It has been
removed from the candidate list along with the 69069 family. What remains true:
the opcode transform consumes one byte per opcode from somewhere, the result is a
Zend opcode, and the routine that does it has not been located in this build.
