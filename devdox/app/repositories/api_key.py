import uuid
from abc import abstractmethod
from enum import Enum
from typing import Any, List, Protocol

from models import APIKEY

from app.exceptions.base_exceptions import DevDoxAPIException
from app.exceptions.exception_constants import MISSING_USER_ID_LOG_MESSAGE_API_KEY, \
    MISSING_USER_ID_TITLE, SERVICE_UNAVAILABLE
from app.schemas.api_key import APIKeyCreate

def internal_error(log_message: str, error_type: str, **kwargs):
    return DevDoxAPIException(
        user_message=SERVICE_UNAVAILABLE,
        log_message=log_message,
        error_type=error_type,
        log_level="exception",
        **kwargs
    )

class IApiKeyStore(Protocol):

    @abstractmethod
    async def query_for_existing_hashes(self, hash_key: str) -> bool: ...

    @abstractmethod
    async def save_api_key(self, create_model: APIKeyCreate) -> Any: ...

    @abstractmethod
    async def set_inactive_by_user_id_and_api_key_id(
        self, user_id, api_key_id
    ) -> int: ...

    @abstractmethod
    async def get_all_api_keys(self, offset, limit, user_id) -> List[Any]: ...
    
    @abstractmethod
    async def count_all_api_keys(self, user_id:str) -> int: ...
    

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

    class InternalExceptions(Enum):
        MISSING_USER_ID = {
            "error_type": MISSING_USER_ID_TITLE,
            "log_message": MISSING_USER_ID_LOG_MESSAGE_API_KEY,
        }

    async def query_for_existing_hashes(self, hash_key: str) -> bool:

        if not hash_key or not hash_key.strip():
            return False

        return await APIKEY.filter(api_key=hash_key).exists()

    async def save_api_key(self, create_model: APIKeyCreate) -> APIKEY:
        return await APIKEY.create(**create_model.model_dump())

    async def set_inactive_by_user_id_and_api_key_id(
        self, user_id: str, api_key_id: uuid.UUID
    ) -> int:
        if (not user_id or not user_id.strip()) or not api_key_id:
            return -1

        return await APIKEY.filter(
            user_id=user_id, id=api_key_id, is_active=True
        ).update(is_active=False)

    def __get_all_api_keys_query(self, user_id:str):
        if not user_id or not user_id.strip():
            raise internal_error(**self.InternalExceptions.MISSING_USER_ID.value)

        query = APIKEY.filter(user_id=user_id, is_active=True)

        return query

    async def count_all_api_keys(self, user_id:str) -> int:
        query = self.__get_all_api_keys_query(user_id)
        return await query.count()

    async def get_all_api_keys(self, offset, limit, user_id: str) -> List[APIKEY]:

        query = self.__get_all_api_keys_query(user_id)

        git_labels = (
            await query.order_by("-created_at").offset(offset).limit(limit).all()
        )

        return git_labels

