from datetime import datetime
from types import SimpleNamespace
from typing import Any
from uuid import uuid4

from app.repositories.api_key_repository import IApiKeyStore
from app.schemas.api_key_schema import APIKeyCreate


class FakeApiKeyStore(IApiKeyStore):
    def __init__(self):
        self.stored_keys = []
        self.received_calls = []
        self.exceptions = {}
        self.existing_hash_set = set()

    def set_existing_hash(self, existing_hash: str):
        self.existing_hash_set.add(existing_hash)

    def set_exception(self, method_name: str, exception: Exception):
        self.exceptions[method_name] = exception

    async def query_for_existing_hashes(self, hash_key: str) -> bool:
        if "query_for_existing_hashes" in self.exceptions:
            raise self.exceptions["query_for_existing_hashes"]

        self.received_calls.append(("query_for_existing_hashes", hash_key))

        return hash_key in self.existing_hash_set

    async def save_api_key(self, create_model: APIKeyCreate) -> Any:
        if "save_api_key" in self.exceptions:
            raise self.exceptions["save_api_key"]

        self.received_calls.append(("save_api_key", create_model))

        fake_entry = SimpleNamespace(
            id=uuid4(),
            user_id=create_model.user_id,
            api_key=create_model.api_key,
            masked_api_key=create_model.masked_api_key,
            is_active=True,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            last_used_at=None,
        )
        self.stored_keys.append(fake_entry)
        return fake_entry