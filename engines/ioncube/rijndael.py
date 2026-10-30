"""Rijndael block cipher used by the ionCube loaders.

The 7.2 loader (15.5.1, x64) expands its key schedule at ``arg3`` and runs
``(arg3[128] >> 1) - 1`` rounds over the Te0..Te3 tables at ``0x1800B8350``,
which is AES with 128/192/256-bit keys.  Opcode blobs are block-aligned
(608 bytes = 38 * 16 for the sample main record), so they are decrypted in a
16-byte block mode.
"""

from __future__ import annotations

SBOX = bytes.fromhex(
    "637c777bf26b6fc53001672bfed7ab76"
    "ca82c97dfa5947f0add4a2af9ca472c0"
    "b7fd9326363ff7cc34a5e5f171d83115"
    "04c723c31896059a071280e2eb27b275"
    "09832c1a1b6e5aa0523bd6b329e32f84"
    "53d100ed20fcb15b6acbbe394a4c58cf"
    "d0efaafb434d338545f9027f503c9fa8"
    "51a3408f929d38f5bcb6da2110fff3d2"
    "cd0c13ec5f974417c4a77e3d645d1973"
    "60814fdc222a908846eeb814de5e0bdb"
    "e0323a0a4906245cc2d3ac629195e479"
    "e7c8376d8dd54ea96c56f4ea657aae08"
    "ba78252e1ca6b4c6e8dd741f4bbd8b8a"
    "703eb5664803f60e613557b986c11d9e"
    "e1f8981169d98e949b1e87e9ce5528df"
    "8ca1890dbfe6426841992d0fb054bb16"
)
INV_SBOX = bytes(SBOX.index(i) for i in range(256))

RCON = (
    0x00000000,
    0x01000000, 0x02000000, 0x04000000, 0x08000000,
    0x10000000, 0x20000000, 0x40000000, 0x80000000,
    0x1B000000, 0x36000000, 0x6C000000, 0xD8000000, 0xAB000000, 0x4D000000,
)


def _xtime(value: int) -> int:
    return ((value << 1) ^ 0x1B) & 0xFF if value & 0x80 else (value << 1) & 0xFF


def _mul(value: int, factor: int) -> int:
    result = 0
    while factor:
        if factor & 1:
            result ^= value
        value = _xtime(value)
        factor >>= 1
    return result


_MUL = {f: bytes(_mul(v, f) for v in range(256)) for f in (2, 3, 9, 11, 13, 14)}


def _rot_word(word: int) -> int:
    return ((word << 8) | (word >> 24)) & 0xFFFFFFFF


def _sub_word(word: int) -> int:
    return (
        SBOX[(word >> 24) & 0xFF] << 24
        | SBOX[(word >> 16) & 0xFF] << 16
        | SBOX[(word >> 8) & 0xFF] << 8
        | SBOX[word & 0xFF]
    )


class Rijndael:
    """AES block cipher with a 16/24/32-byte key."""

    def __init__(self, key: bytes):
        if len(key) not in (16, 24, 32):
            raise ValueError("key must be 16, 24 or 32 bytes")
        self.rounds = {16: 10, 24: 12, 32: 14}[len(key)]
        words = [int.from_bytes(key[i : i + 4], "big") for i in range(0, len(key), 4)]
        key_words = len(words)
        total = 4 * (self.rounds + 1)
        for index in range(key_words, total):
            temp = words[index - 1]
            if index % key_words == 0:
                temp = _sub_word(_rot_word(temp)) ^ RCON[index // key_words]
            elif key_words > 6 and index % key_words == 4:
                temp = _sub_word(temp)
            words.append(words[index - key_words] ^ temp)
        self._round_keys = words

    @staticmethod
    def _add_round_key(state: list[int], words: list[int]) -> list[int]:
        out = []
        for word in words:
            out.extend((word >> 24, (word >> 16) & 0xFF, (word >> 8) & 0xFF, word & 0xFF))
        return [a ^ b for a, b in zip(state, out)]

    @staticmethod
    def _shift_rows(state: list[int]) -> list[int]:
        return [state[4 * ((column + row) % 4) + row] for column in range(4) for row in range(4)]

    @staticmethod
    def _inv_shift_rows(state: list[int]) -> list[int]:
        return [state[4 * ((column - row) % 4) + row] for column in range(4) for row in range(4)]

    @staticmethod
    def _mix_columns(state: list[int]) -> list[int]:
        out = []
        for column in range(4):
            a, b, c, d = state[4 * column : 4 * column + 4]
            out.extend((
                _MUL[2][a] ^ _MUL[3][b] ^ c ^ d,
                a ^ _MUL[2][b] ^ _MUL[3][c] ^ d,
                a ^ b ^ _MUL[2][c] ^ _MUL[3][d],
                _MUL[3][a] ^ b ^ c ^ _MUL[2][d],
            ))
        return out

    @staticmethod
    def _inv_mix_columns(state: list[int]) -> list[int]:
        out = []
        for column in range(4):
            a, b, c, d = state[4 * column : 4 * column + 4]
            out.extend((
                _MUL[14][a] ^ _MUL[11][b] ^ _MUL[13][c] ^ _MUL[9][d],
                _MUL[9][a] ^ _MUL[14][b] ^ _MUL[11][c] ^ _MUL[13][d],
                _MUL[13][a] ^ _MUL[9][b] ^ _MUL[14][c] ^ _MUL[11][d],
                _MUL[11][a] ^ _MUL[13][b] ^ _MUL[9][c] ^ _MUL[14][d],
            ))
        return out

    def encrypt_block(self, block: bytes) -> bytes:
        if len(block) != 16:
            raise ValueError("block must be 16 bytes")
        state = self._add_round_key(list(block), self._round_keys[:4])
        for round_index in range(1, self.rounds):
            state = [SBOX[b] for b in state]
            state = self._shift_rows(state)
            state = self._mix_columns(state)
            state = self._add_round_key(state, self._round_keys[round_index * 4 : round_index * 4 + 4])
        state = [SBOX[b] for b in state]
        state = self._shift_rows(state)
        state = self._add_round_key(state, self._round_keys[self.rounds * 4 :])
        return bytes(state)

    def decrypt_block(self, block: bytes) -> bytes:
        if len(block) != 16:
            raise ValueError("block must be 16 bytes")
        state = self._add_round_key(list(block), self._round_keys[self.rounds * 4 :])
        for round_index in range(self.rounds - 1, 0, -1):
            state = self._inv_shift_rows(state)
            state = [INV_SBOX[b] for b in state]
            state = self._add_round_key(state, self._round_keys[round_index * 4 : round_index * 4 + 4])
            state = self._inv_mix_columns(state)
        state = self._inv_shift_rows(state)
        state = [INV_SBOX[b] for b in state]
        state = self._add_round_key(state, self._round_keys[:4])
        return bytes(state)

    def decrypt_cbc(self, data: bytes, iv: bytes) -> bytes:
        if len(iv) != 16 or len(data) % 16:
            raise ValueError("CBC input must be block aligned with a 16-byte IV")
        out = bytearray()
        previous = iv
        for offset in range(0, len(data), 16):
            block = data[offset : offset + 16]
            plain = self.decrypt_block(block)
            out.extend(a ^ b for a, b in zip(plain, previous))
            previous = block
        return bytes(out)
