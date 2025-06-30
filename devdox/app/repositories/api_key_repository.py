from abc import abstractmethod
from typing import Any, List, Protocol

from models import APIKEY
from tortoise.expressions import Q

from app.schemas.api_key_schema import APIKeyCreate


class IApiKeyStore(Protocol):

    @abstractmethod
    async def query_for_existing_hashes(
        self, hash_key_list: List[str]
    ) -> None | List[str]: ...

    @abstractmethod
    async def save_api_key(self, create_model: APIKeyCreate) -> Any: ...


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
        self, hash_key_list: List[str]
    ) -> None | List[str]:

        if not hash_key_list:
            return None

        return await APIKEY.filter(Q(api_key__in=hash_key_list)).values_list(
            "api_key", flat=True
        )

    async def save_api_key(self, create_model: APIKeyCreate) -> APIKEY:
        return await APIKEY.create(**create_model.model_dump())
