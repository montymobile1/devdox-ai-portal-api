from app.utils.encryption import IEncryptionHelper


class FakeEncryptionHelper(IEncryptionHelper):
    def __init__(self):
        self.encrypted_store = {}
        self.received_calls = []

    def encrypt(self, plaintext: str) -> str:
        self.received_calls.append(("encrypt", plaintext))
        return f"enc:{plaintext}"

    def decrypt(self, encrypted_text: str) -> str:
        self.received_calls.append(("decrypt", encrypted_text))
        return encrypted_text.replace("enc:", "")

    def encrypt_for_user(self, plaintext: str, salt_b64: str) -> str:
        self.received_calls.append(("encrypt_for_user", plaintext, salt_b64))
        return f"enc:{salt_b64}:{plaintext}"

    def decrypt_for_user(self, encrypted_text: str, salt_b64: str) -> str:
        self.received_calls.append(("decrypt_for_user", encrypted_text, salt_b64))
        return encrypted_text.replace(f"enc:{salt_b64}:", "")
