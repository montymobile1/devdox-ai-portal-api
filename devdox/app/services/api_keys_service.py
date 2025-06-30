import dataclasses
import hashlib
import random
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

    DEFAULT_MAX_KEY_LENGTH = 16
    DEFAULT_MAX_CANDIDATE_NUMBER = 5
    DEFAULT_PREFIX = ""

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
        random_part = "".join(random.choices(chars, k=length - len(prefix)))
        return prefix + random_part

    @staticmethod
    def mask_api_key(unhashed_key: str) -> str:
        return mask_token(unhashed_key)

    async def find_hashes_if_exist(self, hash_key_list) -> set:
        existing = await self.api_key_store.query_for_existing_hashes(hash_key_list)

        if not existing:
            return set()

        existing_set = set(existing)

        return existing_set

    async def generate_unique_api_key(
        self,
        prefix: str = DEFAULT_PREFIX,
        candidates: int = DEFAULT_MAX_CANDIDATE_NUMBER,
        length: int = DEFAULT_MAX_KEY_LENGTH,
    ) -> Optional[APIKeyManagerReturn]:
        # Generate candidates
        plain_keys = [
            self.__generate_plain_key(prefix=prefix, length=length)
            for _ in range(candidates)
        ]

        hashed_keys = [self.hash_key(k) for k in plain_keys]

        # Query existing hashes in DB
        # (disclaimer: It's rare to have similar hashes even for the same keys, but this is in place for edge cases)
        existing_set = await self.find_hashes_if_exist(hashed_keys)

        # Select a non-conflicting key
        for plain, hashed in zip(plain_keys, hashed_keys):
            if hashed not in existing_set:
                masked = self.mask_api_key(plain)
                return APIKeyManagerReturn(plain=plain, hashed=hashed, masked=masked)

        # If None that means it has failed to find any key, and it's left to the caller how to handle such a case
        return None


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

        max_generation_attempts = 3

        result = None
        for attempt in range(1, max_generation_attempts + 1):
            tmp_result = await self.api_key_manager.generate_unique_api_key(
                candidates=2
            )
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
