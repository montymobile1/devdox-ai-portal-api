from datetime import datetime
from types import SimpleNamespace
from typing import Any, List, Optional
from uuid import uuid4

from app.repositories.api_key_repository import IApiKeyStore
from app.schemas.api_key_schema import APIKeyCreate


class FakeApiKeyStore(IApiKeyStore):
    def __init__(self):
        self.stored_keys = []
        self.existing_hashes = set()
        self.received_calls = []
        self.exceptions = {}

    def set_existing_hashes(self, hashes: List[str]):
        self.existing_hashes = set(hashes)

    def set_exception(self, method_name: str, exception: Exception):
        self.exceptions[method_name] = exception

    async def query_for_existing_hashes(self, hash_key_list: List[str]) -> Optional[List[str]]:
        if "query_for_existing_hashes" in self.exceptions:
            raise self.exceptions["query_for_existing_hashes"]

        self.received_calls.append(("query_for_existing_hashes", hash_key_list))

        matches = [hk for hk in hash_key_list if hk in self.existing_hashes]
        return matches if matches else None

    async def save_api_key(self, create_model: APIKeyCreate) -> Any:
        if "save_api_key" in self.exceptions:
            raise self.exceptions["save_api_key"]

        self.received_calls.append(("save_api_key", create_model))

        fake_entry = SimpleNamespace(
            id= uuid4(),
            user_id= create_model.user_id,
            api_key= create_model.api_key,
            masked_api_key= create_model.masked_api_key,
            is_active= True,
            created_at= datetime.utcnow(),
            updated_at= datetime.utcnow(),
            last_used_at= None,
        )
        self.stored_keys.append(fake_entry)
        return fake_entry
