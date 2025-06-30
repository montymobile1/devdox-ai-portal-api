import hashlib
from typing import Optional

from app.repositories.api_key_repository import IApiKeyStore
from app.services.api_keys_service import APIKeyManagerReturn
from app.services.git_tokens_service import mask_token


class FakeAPIKeyManager:
    def __init__(self, api_key_store: IApiKeyStore):
        self.api_key_store = api_key_store
        self.generated_key = ""
        self.received_calls = []
        self.exceptions = {}

    def set_fixed_key(self, key: str):
        self.generated_key = key

    def set_exception(self, method_name: str, exception: Exception):
        self.exceptions[method_name] = exception

    @staticmethod
    def hash_key(unhashed_api_key: str) -> str:
        return hashlib.sha256(unhashed_api_key.encode("utf-8")).hexdigest()

    async def generate_unique_api_key(
        self, prefix: str = "dvd_", length: int = 32
    ) -> Optional[APIKeyManagerReturn]:
        if "generate_unique_api_key" in self.exceptions:
            raise self.exceptions["generate_unique_api_key"]

        self.received_calls.append(("generate_unique_api_key", prefix, length))

        plain_key = self.generated_key or f"{prefix}mockkey"
        hashed_key = self.hash_key(plain_key)

        exists = await self.api_key_store.query_for_existing_hashes(hashed_key)

        if exists:
            return None

        masked = mask_token(plain_key)
        return APIKeyManagerReturn(plain=plain_key, hashed=hashed_key, masked=masked)
