import os

import pytest
from cryptography.fernet import Fernet, InvalidToken
import base64
from app.utils import constants
from app.utils.encryption import FernetEncryptionHelper

class TestFernetEncryptionHelper:

    @pytest.fixture
    def helper(self):
        test_key = Fernet.generate_key().decode()
        return FernetEncryptionHelper(secret_key=test_key)

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

        with pytest.raises(ValueError) as exc:
            helper = FernetEncryptionHelper(secret_key=None)
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
