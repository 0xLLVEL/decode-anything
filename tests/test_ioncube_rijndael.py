from engines.ioncube.rijndael import Rijndael


def test_aes_128_fips_197_vector():
    cipher = Rijndael(bytes.fromhex("000102030405060708090a0b0c0d0e0f"))
    plain = bytes.fromhex("00112233445566778899aabbccddeeff")
    expected = bytes.fromhex("69c4e0d86a7b0430d8cdb78070b4c55a")
    assert cipher.encrypt_block(plain) == expected
    assert cipher.decrypt_block(expected) == plain


def test_aes_256_fips_197_vector():
    cipher = Rijndael(bytes.fromhex("000102030405060708090a0b0c0d0e0f101112131415161718191a1b1c1d1e1f"))
    plain = bytes.fromhex("00112233445566778899aabbccddeeff")
    expected = bytes.fromhex("8ea2b7ca516745bfeafc49904b496089")
    assert cipher.encrypt_block(plain) == expected
    assert cipher.decrypt_block(expected) == plain


def test_aes_256_cbc_nist_vector():
    cipher = Rijndael(bytes.fromhex("603deb1015ca71be2b73aef0857d77811f352c073b6108d72d9810a30914dff4"))
    iv = bytes.fromhex("000102030405060708090a0b0c0d0e0f")
    block = bytes.fromhex("f58c4c04d6e5f1ba779eabfb5f7bfbd6")
    assert cipher.decrypt_cbc(block, iv) == bytes.fromhex("6bc1bee22e409f96e93d7e117393172a")
