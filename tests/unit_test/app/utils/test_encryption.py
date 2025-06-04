from typing import Optional

import pytest
from cryptography.fernet import Fernet, InvalidToken

from app.utils import constants
from app.utils.encryption import EncryptionHelper

def patch_encryption_key(monkeypatch, key: Optional[bytes]=Fernet.generate_key()):
    monkeypatch.setattr(EncryptionHelper, "SECRET_KEY", key)
    return key

@pytest.fixture(autouse=True)
def patch_secret_key(monkeypatch):
    patch_encryption_key(monkeypatch)
    yield

class TestEncryptionHelper:
    def test_encrypt_decrypt_round_trip(self):
        original = "devdox-is-awesome"
        encrypted = EncryptionHelper.encrypt(original)
        decrypted = EncryptionHelper.decrypt(encrypted)
        assert decrypted == original

    def test_encrypted_string_format(self):
        plaintext = "secure-me"
        encrypted = EncryptionHelper.encrypt(plaintext)
        assert isinstance(encrypted, str)
        assert encrypted != plaintext
        assert "=" in encrypted or encrypted.endswith("==")

    def test_decrypting_invalid_token_should_raise(self):
        with pytest.raises(InvalidToken):
            EncryptionHelper.decrypt("not.a.valid.token")

    def test_encrypt_empty_string(self):
        encrypted = EncryptionHelper.encrypt("")
        decrypted = EncryptionHelper.decrypt(encrypted)
        assert decrypted == ""

    def test_encrypt_string_with_special_characters(self):
        special = "🔥💀🔒@!#%&()[]<>?你好世界"
        encrypted = EncryptionHelper.encrypt(special)
        decrypted = EncryptionHelper.decrypt(encrypted)
        assert decrypted == special

    def test_get_cipher_raises_if_key_missing(self, monkeypatch):
        patch_encryption_key(monkeypatch, key=None)

        with pytest.raises(ValueError, match=constants.ENCRYPTION_KEY_NOT_FOUND):
            EncryptionHelper.get_cipher()

    def test_different_keys_produce_different_outputs(self, monkeypatch):
        key1 = Fernet.generate_key()
        patch_encryption_key(monkeypatch, key=key1)

        encrypted = EncryptionHelper.encrypt("hello")

        key2 = Fernet.generate_key()
        patch_encryption_key(monkeypatch, key=key2)

        with pytest.raises(InvalidToken):
            EncryptionHelper.decrypt(encrypted)


class TestEncryptionHelperEdgeCases:
    def test_encrypt_none_should_raise(self):
        """Encrypting None should raise AttributeError (can't encode None)."""
        with pytest.raises(AttributeError):
            EncryptionHelper.encrypt(None)  # type: ignore

    def test_decrypt_none_should_raise(self):
        """Decrypting None should raise AttributeError (can't encode None)."""
        with pytest.raises(AttributeError):
            EncryptionHelper.decrypt(None)  # type: ignore

    def test_encrypt_numeric_string(self):
        """Should encrypt and decrypt a stringified number correctly."""
        value = str(1234567890)
        encrypted = EncryptionHelper.encrypt(value)
        decrypted = EncryptionHelper.decrypt(encrypted)
        assert decrypted == value

    def test_encrypt_very_long_string(self):
        """Should encrypt and decrypt a very long string (100_000+ chars)."""
        long_string = "🚀" * 100_000
        encrypted = EncryptionHelper.encrypt(long_string)
        decrypted = EncryptionHelper.decrypt(encrypted)
        assert decrypted == long_string

    def test_decrypt_truncated_token(self):
        """Should raise InvalidToken if token is missing characters."""
        encrypted = EncryptionHelper.encrypt("valid")
        truncated = encrypted[:-5]
        with pytest.raises(InvalidToken):
            EncryptionHelper.decrypt(truncated)

    def test_decrypt_mutated_token_should_raise(self):
        """Should raise InvalidToken if encrypted token is corrupted internally."""
        encrypted = EncryptionHelper.encrypt("valid")

        # Convert to bytearray, flip a byte inside (not just appending)
        token_bytes = bytearray(encrypted.encode())
        token_bytes[len(token_bytes) // 2] ^= 0xFF  # Flip a bit somewhere in the middle
        corrupted_token = token_bytes.decode(
            errors="ignore"
        )  # might still be decodable base64

        with pytest.raises(InvalidToken):
            EncryptionHelper.decrypt(corrupted_token)

    def test_encrypt_control_characters(self):
        """Should work with non-printable ASCII characters."""
        control_string = "".join([chr(i) for i in range(0, 32)])  # ASCII 0–31
        encrypted = EncryptionHelper.encrypt(control_string)
        decrypted = EncryptionHelper.decrypt(encrypted)
        assert decrypted == control_string

    def test_encrypt_high_unicode_characters(self):
        """Should handle characters beyond Basic Multilingual Plane."""
        fancy_unicode = "𐍈𐍉𐍊𐍋𐍌"  # Gothic unicode characters
        encrypted = EncryptionHelper.encrypt(fancy_unicode)
        decrypted = EncryptionHelper.decrypt(encrypted)
        assert decrypted == fancy_unicode

    def test_decrypt_empty_string(self):
        """Decrypting empty string (not base64) should raise InvalidToken."""
        with pytest.raises(InvalidToken):
            EncryptionHelper.decrypt("")

    def test_decrypt_random_garbage(self):
        """Decrypting random garbage text should raise InvalidToken."""
        with pytest.raises(InvalidToken):
            EncryptionHelper.decrypt("this_is_not_encrypted_text")

    def test_encrypt_whitespace_only(self):
        """Should preserve whitespace-only strings."""
        value = " \t\n\r  "
        encrypted = EncryptionHelper.encrypt(value)
        decrypted = EncryptionHelper.decrypt(encrypted)
        assert decrypted == value

    def test_encrypt_mixed_encoding_string(self):
        """Should work with strings mixing ASCII, Latin, Arabic, and emojis."""
        mixed = "DevDox123_¡Hola!_مرحبا_🚀"
        encrypted = EncryptionHelper.encrypt(mixed)
        decrypted = EncryptionHelper.decrypt(encrypted)
        assert decrypted == mixed

    def test_encrypt_binary_converted_to_string(self):
        """Should support binary-like string converted from bytes."""
        raw_bytes = b"\x00\x01\x02\xff\xfe"
        value = raw_bytes.hex()
        encrypted = EncryptionHelper.encrypt(value)
        decrypted = EncryptionHelper.decrypt(encrypted)
        assert decrypted == value

    def test_encrypt_and_decrypt_multiple_times_consistently(self):
        """Multiple roundtrips with different inputs should always match."""
        inputs = ["dev", "🔥", " " * 100, "مرحبا بالعالم", "😎👀🧠", "0"]
        for value in inputs:
            encrypted = EncryptionHelper.encrypt(value)
            decrypted = EncryptionHelper.decrypt(encrypted)
            assert decrypted == value


class TestEncryptionHelperKeyDerivation:
    def test_derive_key_with_valid_salt(self, monkeypatch):
        # Patch secret key as string
        monkeypatch.setattr(EncryptionHelper, "SECRET_KEY", "my-secret-key")
        salt = b"my_salt"

        key = EncryptionHelper.derive_key(salt)

        assert isinstance(key, bytes)
        # Should be valid base64-encoded Fernet key (length 44)
        assert len(key) == 44

    def test_derive_key_is_deterministic_for_same_input(self, monkeypatch):
        monkeypatch.setattr(EncryptionHelper, "SECRET_KEY", "fixed-key")
        salt = b"constant-salt"

        key1 = EncryptionHelper.derive_key(salt)
        key2 = EncryptionHelper.derive_key(salt)

        assert key1 == key2  # Deterministic with same SECRET_KEY and salt

    def test_derive_key_changes_with_different_salts(self, monkeypatch):
        monkeypatch.setattr(EncryptionHelper, "SECRET_KEY", "fixed-key")

        salt1 = b"salt-one"
        salt2 = b"salt-two"

        key1 = EncryptionHelper.derive_key(salt1)
        key2 = EncryptionHelper.derive_key(salt2)

        assert key1 != key2

    def test_derive_key_changes_with_different_secret_keys(self, monkeypatch):
        salt = b"same-salt"

        monkeypatch.setattr(EncryptionHelper, "SECRET_KEY", "key1")
        key1 = EncryptionHelper.derive_key(salt)

        monkeypatch.setattr(EncryptionHelper, "SECRET_KEY", "key2")
        key2 = EncryptionHelper.derive_key(salt)

        assert key1 != key2

    def test_derive_key_with_empty_salt(self, monkeypatch):
        monkeypatch.setattr(EncryptionHelper, "SECRET_KEY", "anykey")
        salt = b""

        key = EncryptionHelper.derive_key(salt)
        assert isinstance(key, bytes)
        assert len(key) == 44  # still valid base64
