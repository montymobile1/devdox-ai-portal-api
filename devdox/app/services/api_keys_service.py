import dataclasses
import hashlib
import secrets
import string
from typing import Annotated, Optional

from fastapi import Depends

from app.exceptions.custom_exceptions import BadRequest
from app.exceptions.exception_constants import (
    FAILED_GENERATE_API_KEY_RETRIES_LOG_MESSAGE,
    UNIQUE_API_KEY_GENERATION_FAILED,
)
from app.repositories.api_key_repository import TortoiseApiKeyStore
from app.schemas.api_key_schema import APIKeyCreate
from app.services.git_tokens_service import mask_token
from app.utils.auth import UserClaims


@dataclasses.dataclass
class APIKeyManagerReturn:
    plain: str
    hashed: str
    masked: str


class APIKeyManager:

    DEFAULT_MAX_KEY_LENGTH = 32
    DEFAULT_PREFIX = "dvd_"

    def __init__(self, api_key_store: TortoiseApiKeyStore):
        self.api_key_store = api_key_store

    @staticmethod
    def hash_key(unhashed_api_key: str) -> str:
        return hashlib.sha256(unhashed_api_key.encode("utf-8")).hexdigest()

    @staticmethod
    def __generate_plain_key(
        prefix: str = DEFAULT_PREFIX, length: int = DEFAULT_MAX_KEY_LENGTH
    ) -> str:
        chars = string.ascii_letters + string.digits
        random_part = "".join(secrets.choice(chars) for _ in range(length - len(prefix)))
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
        
        return APIKeyManagerReturn(plain=plain_key, hashed=hashed_key, masked=masked_plain_key)


class PostApiKeyService:

    def __init__(
        self,
        api_key_store: TortoiseApiKeyStore,
        api_key_manager: APIKeyManager,
    ):
        self.api_key_store = api_key_store
        self.api_key_manager = api_key_manager

    @classmethod
    def with_dependency(
        cls,
        api_key_store: Annotated[TortoiseApiKeyStore, Depends()],
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
