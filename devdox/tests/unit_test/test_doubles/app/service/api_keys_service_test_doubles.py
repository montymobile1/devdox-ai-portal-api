from typing import List, Optional, Set

from app.repositories.api_key_repository import IApiKeyStore
from app.services.api_keys_service import APIKeyManagerReturn


class FakeAPIKeyManager:
    def __init__(self, api_key_store: IApiKeyStore):
        self.api_key_store = api_key_store
        self.fixed_keys: List[str] = []
        self.received_calls = []
        self.exceptions = {}

    def set_fixed_keys(self, plain_keys: List[str]):
        self.fixed_keys = plain_keys

    def set_exception(self, method_name: str, exception: Exception):
        self.exceptions[method_name] = exception

    @staticmethod
    def hash_key(unhashed_api_key: str) -> str:
        return "hashed_" + unhashed_api_key

    @staticmethod
    def mask_api_key(unhashed_key: str) -> str:
        return "****" + unhashed_key[-4:]

    async def find_hashes_if_exist(self, hash_key_list: List[str]) -> Set[str]:
        if "find_hashes_if_exist" in self.exceptions:
            raise self.exceptions["find_hashes_if_exist"]

        self.received_calls.append(("find_hashes_if_exist", hash_key_list))
        existing = await self.api_key_store.query_for_existing_hashes(hash_key_list)
        return set(existing or [])

    async def generate_unique_api_key(
        self,
        prefix: str = "",
        candidates: int = 5,
        length: int = 16
    ) -> Optional[APIKeyManagerReturn]:
        if "generate_unique_api_key" in self.exceptions:
            raise self.exceptions["generate_unique_api_key"]

        self.received_calls.append(("generate_unique_api_key", prefix, candidates, length))

        # Use fixed keys for determinism
        plain_keys = self.fixed_keys[:candidates]

        hashed_keys = [self.hash_key(k) for k in plain_keys]
        existing_set = await self.find_hashes_if_exist(hashed_keys)

        for plain, hashed in zip(plain_keys, hashed_keys):
            if hashed not in existing_set:
                return APIKeyManagerReturn(
                    plain=plain,
                    hashed=hashed,
                    masked=self.mask_api_key(plain)
                )

        return None
