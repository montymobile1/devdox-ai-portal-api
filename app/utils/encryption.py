from cryptography.fernet import Fernet
from app.config import settings
from app.utils import constants


class EncryptionHelper:
    """Helper class for encrypting and decrypting tokens."""

    SECRET_KEY = settings.SECRET_KEY

    @classmethod
    def get_cipher(cls) -> Fernet:
        """
        Returns a Fernet cipher instance initialized with the class's secret key.
        
        Raises:
            ValueError: If the secret key is not set.
        """
        if not cls.SECRET_KEY:
            raise ValueError(constants.ENCRYPTION_KEY_NOT_FOUND)
        return Fernet(cls.SECRET_KEY)

    @classmethod
    def encrypt(cls, plaintext: str) -> str:
        """
        Encrypts a plaintext string using Fernet symmetric encryption.
        
        Args:
            plaintext: The string to encrypt.
        
        Returns:
            The encrypted string, encoded in UTF-8.
        """
        cipher = cls.get_cipher()
        return cipher.encrypt(plaintext.encode()).decode()

    @classmethod
    def decrypt(cls, encrypted_text: str) -> str:
        """
        Decrypts an encrypted string using the Fernet symmetric encryption scheme.
        
        Args:
            encrypted_text: The encrypted string to decrypt.
        
        Returns:
            The original plaintext string after decryption.
        """
        cipher = cls.get_cipher()
        return cipher.decrypt(encrypted_text.encode()).decode()
