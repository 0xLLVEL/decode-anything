"""Regression tests for the ionCube 7.x file-level record cipher.

The four dwords are the loader's program key words (``sub_180003570``); the
cipher is ``sub_180001E10`` driven by ``sub_18009CA40``, which steps the
two-word multiply-add once per byte instead of serving the cached dword twice.
"""

import hashlib
from pathlib import Path

import pytest

from engines.ioncube.body72 import decrypt_record, record_key
from tools.ic72_op_walk import walk_record

KEY_WORDS = [0xB8, 5, 0, 0x29806FF7]
KEY = bytes.fromhex("010101b901010106010101012a8170f800")
SAMPLE = Path(r"C:\Users\ezan\Documents\samples\binancepay_asli.php")
TRUTH = Path("scratch/rt/binancepay_asli.opcodes.json")


def test_record_key_increments_every_big_endian_byte():
    assert record_key(KEY_WORDS) == KEY
    assert len(KEY) == 17
    assert KEY[-1] == 0


def test_record_cipher_keystream():
    # Every byte of this stream was read back from the live loader.
    assert decrypt_record(bytes(8), KEY) == bytes.fromhex("fa29082618f94c83")


def test_record_cipher_is_an_involution():
    key = record_key(KEY_WORDS)
    payload = bytes(range(64))
    assert decrypt_record(decrypt_record(payload, key), key) == payload


def test_record_key_rejects_wrong_word_count():
    with pytest.raises(ValueError):
        record_key([1, 2, 3])


@pytest.mark.skipif(not SAMPLE.exists(), reason="sample file not available")
def test_file_level_record_matches_runtime_dump():
    from tools.ic72_record0 import FILE_LEVEL_HEAD
    from tools.ic72_record_walk import resync
    from tools.ic72_static_container import (
        decode_file,
        decode_payload_body,
        load_payload,
    )

    payload = load_payload(SAMPLE, 0)
    header, _ = decode_file(SAMPLE, payload_index=0)
    version = int(str(header["initial_header"]["version"]), 0)
    body = decode_payload_body(payload, int(header["body_offset"]), version).decompressed

    record = resync(body, 4)[0]
    ciphertext = body[record.payload_offset : record.payload_offset + record.payload_size]
    image = decrypt_record(ciphertext, record_key(KEY_WORDS))

    # The loader writes the same image into a fresh page-aligned buffer; this
    # digest pins the decrypted form.
    assert hashlib.sha1(image).hexdigest() == IMAGE_SHA1

    walked = walk_record(image, 0, head=FILE_LEVEL_HEAD, fixed_aux=True)
    assert walked["ops"] == 11
    assert walked["cells"] == 12
    assert walked["aux_consumed"] == 165
    if TRUTH.exists():
        import json

        truth = json.loads(TRUTH.read_text(encoding="utf-8"))["op_arrays"]["main"]
        assert [op["opcode"] for op in truth["opcodes"]] == [
            59, 116, 131, 47, 79, 52, 0, 0, 0, 0, 62
        ]


IMAGE_SHA1 = "6abb790c7f90e61988250a9486d3db6b89b80967"
