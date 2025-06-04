from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from app.config import settings
from app.utils import constants
import base64


class EncryptionHelper:
    """Helper class for encrypting and decrypting tokens."""

    SECRET_KEY = settings.SECRET_KEY

    @classmethod
    def derive_key(cls, salt: bytes) -> bytes:
        """Derives a Fernet-compatible key from password and salt."""
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(cls.SECRET_KEY.encode()))
        return key

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

    @classmethod
    def encrypt_for_user(cls, plaintext: str, salt_b64: str) -> str:
        """
        Encrypts data for a specific user using their stored salt.

        Args:
            plaintext: Data to encrypt
            salt_b64:  Base64-encoded salt for key derivation

        Returns:
            Encrypted string
        """
        # Get user's salt from database
        salt_bytes = base64.urlsafe_b64decode(salt_b64.encode())

        # Derive key and encrypt
        key = cls.derive_key(salt_bytes)
        cipher = Fernet(key)

        return cipher.encrypt(plaintext.encode()).decode()

    @classmethod
    def decrypt_for_user(cls, encrypted_text: str, salt_b64: str) -> str:
        """
        Decrypts data for a specific user using their stored salt.

        Args:
            encrypted_text: Data to decrypt
            user_id: User's ID

        Returns:
            Decrypted string
        """

        # Get salt and derive key
        salt_bytes = base64.urlsafe_b64decode(salt_b64.encode())
        key = cls.derive_key(salt_bytes)
        cipher = Fernet(key)

        return cipher.decrypt(encrypted_text.encode()).decode()
