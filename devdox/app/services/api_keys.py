import dataclasses
import hashlib
import secrets
import string
import uuid
from typing import Annotated, Optional

from fastapi import Depends

from app.exceptions.custom_exceptions import BadRequest, ResourceNotFound
from app.exceptions.exception_constants import (
    FAILED_GENERATE_API_KEY_RETRIES_LOG_MESSAGE,
    INVALID_APIKEY,
    UNIQUE_API_KEY_GENERATION_FAILED,
)
from app.repositories.api_key import TortoiseApiKeyStore as ApiKeyStore
from app.schemas.api_key import APIKeyCreate, APIKeyPublicResponse
from app.services.git_tokens import mask_token
from app.utils.auth import UserClaims


@dataclasses.dataclass
class APIKeyManagerReturn:
    plain: str
    hashed: str
    masked: str


class APIKeyManager:

    DEFAULT_MAX_KEY_LENGTH = 32
    DEFAULT_PREFIX = "dvd_"

    def __init__(self, api_key_store: ApiKeyStore):
        self.api_key_store = api_key_store

    @staticmethod
    def hash_key(unhashed_api_key: str) -> str:
        return hashlib.sha256(unhashed_api_key.encode("utf-8")).hexdigest()

    @staticmethod
    def __generate_plain_key(
        prefix: str = DEFAULT_PREFIX, length: int = DEFAULT_MAX_KEY_LENGTH
    ) -> str:
        chars = string.ascii_letters + string.digits
        random_part = "".join(
            secrets.choice(chars) for _ in range(length - len(prefix))
        )
        return prefix + random_part

    async def generate_unique_api_key(
        self,
        prefix: str = DEFAULT_PREFIX,
        length: int = DEFAULT_MAX_KEY_LENGTH,
    ) -> Optional[APIKeyManagerReturn]:

        plain_key = self.__generate_plain_key(prefix=prefix, length=length)

        hashed_key = self.hash_key(plain_key)

        # Query existing hashes in DB
        key_exists = await self.api_key_store.query_for_existing_hashes(hashed_key)

        if key_exists:
            return None

        masked_plain_key = mask_token(plain_key)

        return APIKeyManagerReturn(
            plain=plain_key, hashed=hashed_key, masked=masked_plain_key
        )


class PostApiKeyService:

    def __init__(
        self,
        api_key_store: ApiKeyStore,
        api_key_manager: APIKeyManager,
    ):
        self.api_key_store = api_key_store
        self.api_key_manager = api_key_manager

    @classmethod
    def with_dependency(
        cls,
        api_key_store: Annotated[ApiKeyStore, Depends()],
    ) -> "PostApiKeyService":

        api_key_manager = APIKeyManager(api_key_store=api_key_store)

        return cls(
            api_key_store=api_key_store,
            api_key_manager=api_key_manager,
        )

    async def generate_api_key(self, user_claims: UserClaims):

        max_generation_attempts = 6

        result = None
        for _ in range(1, max_generation_attempts + 1):
            tmp_result = await self.api_key_manager.generate_unique_api_key()
            if tmp_result:
                result = tmp_result
                break

        if not result:
            raise BadRequest(
                reason=UNIQUE_API_KEY_GENERATION_FAILED,
                log_message=FAILED_GENERATE_API_KEY_RETRIES_LOG_MESSAGE.format(
                    attempts=max_generation_attempts
                ),
            )

        saved_api_key = await self.api_key_store.save_api_key(
            APIKeyCreate(
                user_id=user_claims.sub,
                api_key=result.hashed,
                masked_api_key=result.masked,
            )
        )

        return saved_api_key.id, result.plain


class RevokeApiKeyService:

    def __init__(
        self,
        api_key_store: ApiKeyStore,
    ):
        self.api_key_store = api_key_store

    @classmethod
    def with_dependency(
        cls,
        api_key_store: Annotated[ApiKeyStore, Depends()],
    ) -> "RevokeApiKeyService":

        return cls(
            api_key_store=api_key_store,
        )

    async def revoke_api_key(self, user_claims: UserClaims, api_key_id: uuid.UUID):

        deleted_api_key = (
            await self.api_key_store.set_inactive_by_user_id_and_api_key_id(
                user_id=user_claims.sub, api_key_id=api_key_id
            )
        )

        if deleted_api_key <= 0:
            raise ResourceNotFound(reason=INVALID_APIKEY)

        return deleted_api_key


class GetApiKeyService:

    def __init__(
        self,
        api_key_store: ApiKeyStore,
    ):
        self.api_key_store = api_key_store

    @classmethod
    def with_dependency(
        cls,
        api_key_store: Annotated[ApiKeyStore, Depends()],
    ) -> "GetApiKeyService":

        return cls(
            api_key_store=api_key_store,
        )

    async def get_api_keys_by_user(self, user_claims: UserClaims):

        api_keys_list = await self.api_key_store.get_all_api_keys(
            user_id=user_claims.sub
        )

        api_keys_response = [
            APIKeyPublicResponse.model_validate(api_key) for api_key in api_keys_list
        ]

        return api_keys_response
