from cryptography.fernet import Fernet
from app.config import settings


class EncryptionHelper:
    """Helper class for encrypting and decrypting tokens."""

    SECRET_KEY = settings.SECRET_KEY

    @classmethod
    def get_cipher(cls) -> Fernet:
        """Return a Fernet cipher instance using the secret key."""
        if not cls.SECRET_KEY:
            raise ValueError("Encryption key is not set.")
        return Fernet(cls.SECRET_KEY)

    @classmethod
    def encrypt(cls, plaintext: str) -> str:
        """Encrypt a string using Fernet."""
        cipher = cls.get_cipher()
        return cipher.encrypt(plaintext.encode()).decode()

    @classmethod
    def decrypt(cls, encrypted_text: str) -> str:
        """Decrypt an encrypted string using Fernet."""
        cipher = cls.get_cipher()
        return cipher.decrypt(encrypted_text.encode()).decode()
