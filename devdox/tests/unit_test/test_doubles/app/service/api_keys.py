import hashlib
from typing import Optional

from app.services.api_keys import APIKeyManagerReturn, IAPIKeyManager
from app.services.git_tokens import mask_token
from models_src.repositories.api_key import IApiKeyStore


class FakeAPIKeyManager(IAPIKeyManager):
    def __init__(self, api_key_store: IApiKeyStore):
        self.api_key_store = api_key_store
        self.generated_key = ""
        self.received_calls = []
        self.exceptions = {}

    def set_fixed_key(self, key: str):
        self.generated_key = key

    def set_exception(self, method, exception: Exception):
        method_name = method.__name__
        self.exceptions[method_name] = exception

    @staticmethod
    def hash_key(unhashed_api_key: str) -> str:
        return hashlib.sha256(unhashed_api_key.encode("utf-8")).hexdigest()

    async def generate_unique_api_key(
        self, prefix: str = "dvd_", length: int = 32
    ) -> Optional[APIKeyManagerReturn]:
        
        method_name = self.generate_unique_api_key.__name__
        
        if method_name in self.exceptions:
            raise self.exceptions[method_name]

        self.received_calls.append((method_name, prefix, length))

        plain_key = self.generated_key or f"{prefix}mockkey"
        hashed_key = self.hash_key(plain_key)

        exists = await self.api_key_store.exists_by_hash_key(hashed_key)

        if exists:
            return None

        masked = mask_token(plain_key)
        return APIKeyManagerReturn(plain=plain_key, hashed=hashed_key, masked=masked)

class StubAPIKeyManager(IAPIKeyManager):
    def __init__(self):
        self.stubbed_outputs = {}
        self.exceptions = {}
        self.received_calls = []

    async def __stubify(self, method, **kwargs):
        method_name = method.__name__
        self.received_calls.append((method_name, kwargs))
        if method_name in self.exceptions:
            raise self.exceptions[method_name]
        return self.stubbed_outputs[method_name]

    def set_output(self, method, output):
        method_name = method.__name__
        self.stubbed_outputs[method_name] = output

    def set_exception(self, method, exception: Exception):
        method_name = method.__name__
        self.exceptions[method_name] = exception

    async def generate_unique_api_key(self, prefix: str = "dvd_", length: int = 32):
        return await self.__stubify(
            self.generate_unique_api_key, prefix=prefix, length=length
        )
