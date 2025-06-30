import uuid
from abc import abstractmethod
from typing import Any, Protocol

from models import APIKEY

from app.schemas.api_key_schema import APIKeyCreate


class IApiKeyStore(Protocol):

    @abstractmethod
    async def query_for_existing_hashes(
        self, hash_key: str
    ) -> bool: ...

    @abstractmethod
    async def save_api_key(self, create_model: APIKeyCreate) -> Any: ...
    
    @abstractmethod
    async def set_inactive_by_user_id_and_api_key_id(self, user_id, api_key_id) -> int: ...

class TortoiseApiKeyStore(IApiKeyStore):

    def __init__(self):
        """
        Have to add this as an empty __init__ to override it, because when using it with Depends(),
        FastAPI dependency mechanism will automatically assume its
        ```
        def __init__(self, *args, **kwargs):
            pass
        ```
        Causing unneeded behavior.
        """
        pass
    
    async def query_for_existing_hashes(
        self, hash_key: str
    ) -> bool:

        if not hash_key or not hash_key.strip():
            return False

        return await APIKEY.filter(api_key=hash_key).exists()

    async def save_api_key(self, create_model: APIKeyCreate) -> APIKEY:
        return await APIKEY.create(**create_model.model_dump())
    
    async def set_inactive_by_user_id_and_api_key_id(self, user_id:str, api_key_id:uuid.UUID) -> int:
        if (not user_id or not user_id.strip()) or not api_key_id:
            return -1

        return await APIKEY.filter(user_id=user_id, id=api_key_id, is_active=True).update(is_active=False)
