import uuid
import datetime
from types import SimpleNamespace
from typing import Any, List
from uuid import uuid4

from app.repositories.api_key import IApiKeyStore
from app.schemas.api_key import APIKeyCreate


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
            created_at=datetime.datetime.now(datetime.UTC),
            updated_at=datetime.datetime.now(datetime.UTC),
            last_used_at=None,
        )
        self.stored_keys.append(fake_entry)
        return fake_entry

    async def set_inactive_by_user_id_and_api_key_id(
        self, user_id: str, api_key_id: uuid.UUID
    ) -> int:
        if "set_inactive_by_user_id_and_api_key_id" in self.exceptions:
            raise self.exceptions["set_inactive_by_user_id_and_api_key_id"]

        self.received_calls.append(
            ("set_inactive_by_user_id_and_api_key_id", user_id, api_key_id)
        )

        if not user_id or not user_id.strip() or not api_key_id:
            return -1

        updated = 0

        for key in self.stored_keys:
            if key.user_id == user_id and key.id == api_key_id and key.is_active:
                key.is_active = False
                updated += 1
        return updated

    async def get_all_api_keys(self, user_id) -> List[Any]:
        if "get_all_api_keys" in self.exceptions:
            raise self.exceptions["get_all_api_keys"]

        self.received_calls.append(("get_all_api_keys", user_id))

        if not user_id or not user_id.strip():
            return []

        return sorted(
            [
                key
                for key in self.stored_keys
                if key.user_id == user_id and key.is_active
            ],
            key=lambda k: k.created_at,
            reverse=True,
        )
