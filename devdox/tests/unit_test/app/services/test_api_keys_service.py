import hashlib
from uuid import uuid4

import pytest

from app.services.api_keys_service import (
    APIKeyManager,
    APIKeyManagerReturn,
    PostApiKeyService,
)
from app.services.git_tokens_service import mask_token
from app.utils.auth import UserClaims
from app.exceptions.custom_exceptions import BadRequest
from app.exceptions.exception_constants import (
    UNIQUE_API_KEY_GENERATION_FAILED,
    FAILED_GENERATE_API_KEY_RETRIES_LOG_MESSAGE,
)
from tests.unit_test.test_doubles.app.repository.api_key_repository_test_doubles import FakeApiKeyStore
from tests.unit_test.test_doubles.app.service.api_keys_service_test_doubles import FakeAPIKeyManager

@pytest.mark.asyncio
class TestAPIKeyManager:

    def setup_method(self):
        self.fake_store = FakeApiKeyStore()
        self.manager = APIKeyManager(api_key_store=self.fake_store)

    def test_hash_key_is_deterministic(self):
        unhashed = "my-api-key"
        hashed1 = self.manager.hash_key(unhashed)
        hashed2 = self.manager.hash_key(unhashed)
        assert hashed1 == hashed2
        assert isinstance(hashed1, str)

    def test_mask_key_adds_asterisks(self):
        plain = "abcdef123456"
        masked = self.manager.mask_api_key(plain)
        assert "*" in masked
        assert masked.endswith("56")

    @pytest.mark.asyncio
    async def test_find_hashes_if_exist_returns_existing(self):
        hash1 = "hash1"
        hash2 = "hash2"
        self.fake_store.set_existing_hashes([hash1])
        existing = await self.manager.find_hashes_if_exist([hash1, hash2])
        assert existing == {hash1}

    @pytest.mark.asyncio
    async def test_generate_unique_api_key_success(self, monkeypatch):
        # Force deterministic plain keys
        monkeypatch.setattr(self.manager, "_APIKeyManager__generate_plain_key", lambda prefix, length: "plainkey123456")
        monkeypatch.setattr(self.manager, "mask_api_key", lambda x: mask_token("plainkey123456"))
        monkeypatch.setattr(self.manager, "hash_key", lambda x: "hashedkey")

        self.fake_store.set_existing_hashes([])

        result = await self.manager.generate_unique_api_key(candidates=1)

        assert isinstance(result, APIKeyManagerReturn)
        assert result.plain == "plainkey123456"
        assert result.hashed == "hashedkey"
        assert result.masked == mask_token("plainkey123456")

    @pytest.mark.asyncio
    async def test_generate_unique_api_key_fails_when_all_conflict(self, monkeypatch):
        monkeypatch.setattr(self.manager, "_APIKeyManager__generate_plain_key", lambda prefix, length: "conflict")
        monkeypatch.setattr(self.manager, "hash_key", lambda x: "hashed_conflict")
        monkeypatch.setattr(self.manager, "mask_api_key", lambda x: "****flict")

        self.fake_store.set_existing_hashes(["hashed_conflict"])

        result = await self.manager.generate_unique_api_key(candidates=1)

        assert result is None


@pytest.mark.asyncio
class TestPostApiKeyService:
    def setup_method(self):
        self.fake_store = FakeApiKeyStore()
        self.fake_manager = FakeAPIKeyManager(api_key_store=self.fake_store)
        self.service = PostApiKeyService(
            api_key_store=self.fake_store,
            api_key_manager=self.fake_manager
        )
        self.user_claims = UserClaims(sub="user123")

    async def test_generate_api_key_success(self):
        # Arrange
        self.fake_manager.set_fixed_keys(["key123"])

        # Act
        result_id, result_plain = await self.service.generate_api_key(self.user_claims)

        # Assert
        assert result_plain == "key123"
        assert isinstance(result_id, uuid4().__class__)
        assert self.fake_store.stored_keys[0].user_id == "user123"

    async def test_generate_api_key_fails_after_retries(self):
        # Arrange
        self.fake_manager.set_fixed_keys(["key123"])
        self.fake_store.set_existing_hashes(["hashed_key123"])

        # Act & Assert
        with pytest.raises(BadRequest) as exc:
            await self.service.generate_api_key(self.user_claims)

        assert exc.value.user_message == UNIQUE_API_KEY_GENERATION_FAILED
        assert FAILED_GENERATE_API_KEY_RETRIES_LOG_MESSAGE.format(attempts=3) in exc.value.log_message

    async def test_generate_api_key_bubbles_up_store_error(self):
        # Arrange
        self.fake_manager.set_fixed_keys(["key123"])
        self.fake_store.set_exception("save_api_key", ValueError("fail"))

        # Act & Assert
        with pytest.raises(ValueError, match="fail"):
            await self.service.generate_api_key(self.user_claims)

    async def test_generate_api_key_bubbles_up_manager_error(self):
        # Arrange
        self.fake_manager.set_exception("generate_unique_api_key", RuntimeError("boom"))

        # Act & Assert
        with pytest.raises(RuntimeError, match="boom"):
            await self.service.generate_api_key(self.user_claims)
