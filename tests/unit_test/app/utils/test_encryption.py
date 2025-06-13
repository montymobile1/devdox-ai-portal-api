import os
from typing import Optional

import pytest
from cryptography.fernet import Fernet, InvalidToken
import base64
from app.utils import constants
from app.utils.encryption import EncryptionHelper, FernetEncryptionHelper


# ===================================================================================
# TODO: THIS SECTION WILL BE DEPRECATED SLOWLY AS WE GO IN FAVOR OF THE OTHER NEW PART
# ===================================================================================


def patch_encryption_key(monkeypatch, key: Optional[bytes] = Fernet.generate_key()):
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


class TestEncryptionHelperUserSpecific:
    """Test cases for user-specific encryption methods using salt-based key derivation."""

    def test_encrypt_for_user_decrypt_for_user_round_trip(self, monkeypatch):
        """Should encrypt and decrypt data for a specific user successfully."""
        monkeypatch.setattr(EncryptionHelper, "SECRET_KEY", "test-secret-key")

        plaintext = "user-specific-data"
        salt_b64 = base64.urlsafe_b64encode(b"user_salt_123").decode()

        encrypted = EncryptionHelper.encrypt_for_user(plaintext, salt_b64)
        decrypted = EncryptionHelper.decrypt_for_user(encrypted, salt_b64)

        assert decrypted == plaintext

    def test_encrypt_for_user_with_different_salts_produces_different_outputs(
        self, monkeypatch
    ):
        """Same data encrypted with different salts should produce different outputs."""
        monkeypatch.setattr(EncryptionHelper, "SECRET_KEY", "test-secret-key")

        plaintext = "sensitive-data"
        salt1_b64 = base64.urlsafe_b64encode(b"salt_user_1").decode()
        salt2_b64 = base64.urlsafe_b64encode(b"salt_user_2").decode()

        encrypted1 = EncryptionHelper.encrypt_for_user(plaintext, salt1_b64)
        encrypted2 = EncryptionHelper.encrypt_for_user(plaintext, salt2_b64)

        assert encrypted1 != encrypted2

    def test_decrypt_for_user_with_wrong_salt_should_raise(self, monkeypatch):
        """Decrypting with wrong salt should raise InvalidToken."""
        monkeypatch.setattr(EncryptionHelper, "SECRET_KEY", "test-secret-key")

        plaintext = "user-data"
        correct_salt = base64.urlsafe_b64encode(b"correct_salt").decode()
        wrong_salt = base64.urlsafe_b64encode(b"wrong_salt").decode()

        encrypted = EncryptionHelper.encrypt_for_user(plaintext, correct_salt)

        with pytest.raises(InvalidToken):
            EncryptionHelper.decrypt_for_user(encrypted, wrong_salt)

    def test_encrypt_for_user_with_empty_string(self, monkeypatch):
        """Should handle empty string encryption for user."""
        monkeypatch.setattr(EncryptionHelper, "SECRET_KEY", "test-secret-key")

        salt_b64 = base64.urlsafe_b64encode(b"user_salt").decode()

        encrypted = EncryptionHelper.encrypt_for_user("", salt_b64)
        decrypted = EncryptionHelper.decrypt_for_user(encrypted, salt_b64)

        assert decrypted == ""

    def test_encrypt_for_user_with_special_characters(self, monkeypatch):
        """Should handle special characters in user-specific encryption."""
        monkeypatch.setattr(EncryptionHelper, "SECRET_KEY", "test-secret-key")

        special_data = "🔥💀🔒@!#%&()[]<>?你好世界"
        salt_b64 = base64.urlsafe_b64encode(b"special_salt").decode()

        encrypted = EncryptionHelper.encrypt_for_user(special_data, salt_b64)
        decrypted = EncryptionHelper.decrypt_for_user(encrypted, salt_b64)

        assert decrypted == special_data

    def test_encrypt_for_user_with_long_string(self, monkeypatch):
        """Should handle very long strings in user-specific encryption."""
        monkeypatch.setattr(EncryptionHelper, "SECRET_KEY", "test-secret-key")

        long_data = "long_data_" * 10000
        salt_b64 = base64.urlsafe_b64encode(b"long_salt").decode()

        encrypted = EncryptionHelper.encrypt_for_user(long_data, salt_b64)
        decrypted = EncryptionHelper.decrypt_for_user(encrypted, salt_b64)

        assert decrypted == long_data

    def test_encrypt_for_user_is_deterministic_with_same_inputs(self, monkeypatch):
        """Same plaintext and salt should produce the same encryption key derivation but different tokens."""
        monkeypatch.setattr(EncryptionHelper, "SECRET_KEY", "test-secret-key")

        plaintext = "deterministic-test"
        salt_b64 = base64.urlsafe_b64encode(b"fixed_salt").decode()

        # Note: Fernet encryption includes random nonce, so outputs will differ
        # But both should decrypt to the same plaintext
        encrypted1 = EncryptionHelper.encrypt_for_user(plaintext, salt_b64)
        encrypted2 = EncryptionHelper.encrypt_for_user(plaintext, salt_b64)

        decrypted1 = EncryptionHelper.decrypt_for_user(encrypted1, salt_b64)
        decrypted2 = EncryptionHelper.decrypt_for_user(encrypted2, salt_b64)

        assert decrypted1 == plaintext
        assert decrypted2 == plaintext
        # Encrypted tokens will be different due to Fernet's random nonce
        assert encrypted1 != encrypted2

    def test_decrypt_for_user_with_invalid_base64_salt_should_raise(self, monkeypatch):
        """Should raise exception when decrypting with invalid base64 salt."""
        monkeypatch.setattr(EncryptionHelper, "SECRET_KEY", "test-secret-key")

        # First create valid encrypted data
        plaintext = "test-data"
        valid_salt = base64.urlsafe_b64encode(b"valid_salt").decode()
        encrypted = EncryptionHelper.encrypt_for_user(plaintext, valid_salt)

        # Then try to decrypt with invalid salt
        invalid_salt = "not_valid_base64!@#"

        with pytest.raises(Exception):  # base64 decode error
            EncryptionHelper.decrypt_for_user(encrypted, invalid_salt)

    def test_encrypt_for_user_with_empty_salt_should_work(self, monkeypatch):
        """Should work with empty salt (though not recommended in practice)."""
        monkeypatch.setattr(EncryptionHelper, "SECRET_KEY", "test-secret-key")

        plaintext = "test-data"
        empty_salt = base64.urlsafe_b64encode(b"").decode()

        encrypted = EncryptionHelper.encrypt_for_user(plaintext, empty_salt)
        decrypted = EncryptionHelper.decrypt_for_user(encrypted, empty_salt)

        assert decrypted == plaintext

    def test_encrypt_for_user_with_none_plaintext_should_raise(self, monkeypatch):
        """Should raise AttributeError when trying to encrypt None."""
        monkeypatch.setattr(EncryptionHelper, "SECRET_KEY", "test-secret-key")

        salt_b64 = base64.urlsafe_b64encode(b"test_salt").decode()

        with pytest.raises(AttributeError):
            EncryptionHelper.encrypt_for_user(None, salt_b64)  # type: ignore

    def test_decrypt_for_user_with_none_encrypted_text_should_raise(self, monkeypatch):
        """Should raise AttributeError when trying to decrypt None."""
        monkeypatch.setattr(EncryptionHelper, "SECRET_KEY", "test-secret-key")

        salt_b64 = base64.urlsafe_b64encode(b"test_salt").decode()

        with pytest.raises(AttributeError):
            EncryptionHelper.decrypt_for_user(None, salt_b64)  # type: ignore

    def test_encrypt_for_user_with_whitespace_salt(self, monkeypatch):
        """Should handle salt that contains whitespace when base64 encoded."""
        monkeypatch.setattr(EncryptionHelper, "SECRET_KEY", "test-secret-key")

        plaintext = "test-data"
        salt_with_spaces = base64.urlsafe_b64encode(b"salt with spaces").decode()

        encrypted = EncryptionHelper.encrypt_for_user(plaintext, salt_with_spaces)
        decrypted = EncryptionHelper.decrypt_for_user(encrypted, salt_with_spaces)

        assert decrypted == plaintext

    def test_encrypt_for_user_multiple_users_isolation(self, monkeypatch):
        """Verify that different users' data remains isolated."""
        monkeypatch.setattr(EncryptionHelper, "SECRET_KEY", "test-secret-key")

        # User 1 data
        user1_data = "user1_secret_token"
        user1_salt = base64.urlsafe_b64encode(b"user1_unique_salt").decode()

        # User 2 data
        user2_data = "user2_secret_token"
        user2_salt = base64.urlsafe_b64encode(b"user2_unique_salt").decode()

        # Encrypt data for both users
        user1_encrypted = EncryptionHelper.encrypt_for_user(user1_data, user1_salt)
        user2_encrypted = EncryptionHelper.encrypt_for_user(user2_data, user2_salt)

        # Each user can decrypt their own data
        assert (
            EncryptionHelper.decrypt_for_user(user1_encrypted, user1_salt) == user1_data
        )
        assert (
            EncryptionHelper.decrypt_for_user(user2_encrypted, user2_salt) == user2_data
        )

        # Users cannot decrypt each other's data
        with pytest.raises(InvalidToken):
            EncryptionHelper.decrypt_for_user(user1_encrypted, user2_salt)

        with pytest.raises(InvalidToken):
            EncryptionHelper.decrypt_for_user(user2_encrypted, user1_salt)

    def test_encrypt_for_user_with_binary_data_as_hex(self, monkeypatch):
        """Should handle binary data converted to hex string."""
        monkeypatch.setattr(EncryptionHelper, "SECRET_KEY", "test-secret-key")

        binary_data = b"\x00\x01\x02\xff\xfe\xfd"
        hex_data = binary_data.hex()
        salt_b64 = base64.urlsafe_b64encode(b"binary_salt").decode()

        encrypted = EncryptionHelper.encrypt_for_user(hex_data, salt_b64)
        decrypted = EncryptionHelper.decrypt_for_user(encrypted, salt_b64)

        assert decrypted == hex_data
        assert bytes.fromhex(decrypted) == binary_data

    def test_decrypt_for_user_with_corrupted_token_should_raise(self, monkeypatch):
        """Should raise InvalidToken when encrypted token is corrupted."""
        monkeypatch.setattr(EncryptionHelper, "SECRET_KEY", "test-secret-key")

        plaintext = "test-data"
        salt_b64 = base64.urlsafe_b64encode(b"test_salt").decode()

        encrypted = EncryptionHelper.encrypt_for_user(plaintext, salt_b64)

        # Corrupt the token
        corrupted = encrypted[:-5] + "XXXXX"

        with pytest.raises(InvalidToken):
            EncryptionHelper.decrypt_for_user(corrupted, salt_b64)

    def test_encrypt_for_user_with_very_long_salt(self, monkeypatch):
        """Should handle very long salts."""
        monkeypatch.setattr(EncryptionHelper, "SECRET_KEY", "test-secret-key")

        plaintext = "test-data"
        long_salt_bytes = b"very_long_salt_" * 100
        long_salt_b64 = base64.urlsafe_b64encode(long_salt_bytes).decode()

        encrypted = EncryptionHelper.encrypt_for_user(plaintext, long_salt_b64)
        decrypted = EncryptionHelper.decrypt_for_user(encrypted, long_salt_b64)

        assert decrypted == plaintext


# ===================================================================================
# TODO: This is the new easily testable, less complicated Auth system
# ===================================================================================

class TestFernetEncryptionHelper:

    @pytest.fixture
    def helper(self):
        return FernetEncryptionHelper()

    def test_encrypt_decrypt_round_trip(self, helper):
        plaintext = "super-secret"
        encrypted = helper.encrypt(plaintext)
        decrypted = helper.decrypt(encrypted)
        assert decrypted == plaintext

    def test_decrypt_invalid_data_raises(self, helper):
        with pytest.raises(InvalidToken):
            helper.decrypt("invalid-data")

    def test_user_specific_encrypt_decrypt_round_trip(self, helper):
        plaintext = "user-secret"
        salt = base64.urlsafe_b64encode(os.urandom(16)).decode()
        encrypted = helper.encrypt_for_user(plaintext, salt)
        decrypted = helper.decrypt_for_user(encrypted, salt)
        assert decrypted == plaintext

    def test_user_specific_decrypt_with_wrong_salt_fails(self, helper):
        plaintext = "user-secret"
        salt1 = base64.urlsafe_b64encode(os.urandom(16)).decode()
        salt2 = base64.urlsafe_b64encode(os.urandom(16)).decode()
        encrypted = helper.encrypt_for_user(plaintext, salt1)
        with pytest.raises(InvalidToken):
            helper.decrypt_for_user(encrypted, salt2)

    def test_get_cipher_fails_if_secret_missing(self, monkeypatch):
        monkeypatch.setattr("app.utils.encryption.FernetEncryptionHelper.SECRET_KEY", None)
        helper = FernetEncryptionHelper()
        with pytest.raises(ValueError) as exc:
            helper.encrypt("test")
        assert constants.ENCRYPTION_KEY_NOT_FOUND in str(exc.value)

    def test_key_derivation_is_consistent(self, helper):
        salt = os.urandom(16)
        key1 = helper._derive_key(salt)
        key2 = helper._derive_key(salt)
        assert key1 == key2

    def test_key_derivation_changes_with_salt(self, helper):
        salt1 = os.urandom(16)
        salt2 = os.urandom(16)
        key1 = helper._derive_key(salt1)
        key2 = helper._derive_key(salt2)
        assert key1 != key2