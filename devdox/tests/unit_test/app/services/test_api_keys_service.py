import datetime
import hashlib
import re
from types import SimpleNamespace
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.exceptions.custom_exceptions import BadRequest, ResourceNotFound
from app.exceptions.exception_constants import (FAILED_GENERATE_API_KEY_RETRIES_LOG_MESSAGE,
                                                UNIQUE_API_KEY_GENERATION_FAILED)
from app.schemas.api_key import APIKeyPublicResponse
from app.services.api_keys import (
    APIKeyManager,
    GetApiKeyService,
    PostApiKeyService,
    RevokeApiKeyService,
)
from app.services.git_tokens import mask_token
from app.utils.auth import UserClaims
from tests.unit_test.test_doubles.app.repository.api_key_repository_test_doubles import (
    FakeApiKeyStore,
)
from tests.unit_test.test_doubles.app.service.api_keys_service_test_doubles import (
    FakeAPIKeyManager,
)


@pytest.mark.asyncio
class TestAPIKeyManager:

    async def test_generate_unique_key_success(self):
        store = FakeApiKeyStore()
        manager = APIKeyManager(store)

        result = await manager.generate_unique_api_key()

        assert result is not None
        assert result.plain.startswith("dvd_")
        assert result.hashed == hashlib.sha256(result.plain.encode("utf-8")).hexdigest()
        assert result.masked == mask_token(result.plain)

    async def test_returns_none_if_hash_exists(self):
        store = FakeApiKeyStore()
        manager = APIKeyManager(store)

        precomputed_key = manager._APIKeyManager__generate_plain_key()
        precomputed_hash = manager.hash_key(precomputed_key)
        store.set_existing_hash(precomputed_hash)

        # Monkeypatch to return a known key
        manager._APIKeyManager__generate_plain_key = (
            lambda prefix, length: precomputed_key
        )

        result = await manager.generate_unique_api_key()

        assert result is None

    async def test_handles_store_exception(self):
        store = FakeApiKeyStore()
        store.set_exception("query_for_existing_hashes", RuntimeError("DB error"))
        manager = APIKeyManager(store)

        with pytest.raises(RuntimeError, match="DB error"):
            await manager.generate_unique_api_key()

    async def test_generate_key_respects_prefix_and_length(self):
        store = FakeApiKeyStore()
        manager = APIKeyManager(store)

        prefix = "test_"
        length = 20
        result = await manager.generate_unique_api_key(prefix=prefix, length=length)

        assert result is not None
        assert result.plain.startswith(prefix)
        assert len(result.plain) == length


class DummyUserClaims:
    def __init__(self, user_id):
        self.sub = user_id


@pytest.mark.asyncio
class TestPostApiKeyService:

    async def test_generate_api_key_success(self):
        fake_store = FakeApiKeyStore()
        fake_manager = FakeAPIKeyManager(fake_store)
        fake_manager.set_fixed_key("dvd_mock_key")

        service = PostApiKeyService(
            api_key_store=fake_store, api_key_manager=fake_manager
        )
        user_claims = DummyUserClaims("user-123")

        key_id, plain = await service.generate_api_key(user_claims)

        assert plain == "dvd_mock_key"
        assert any(k.user_id == "user-123" for k in fake_store.stored_keys)
        assert key_id is not None

    async def test_generate_api_key_fails_after_retries(self):
        fake_store = FakeApiKeyStore()
        fake_manager = FakeAPIKeyManager(fake_store)
        fake_store.set_existing_hash(fake_manager.hash_key("dvd_mock_key"))
        fake_manager.set_fixed_key("dvd_mock_key")

        service = PostApiKeyService(
            api_key_store=fake_store, api_key_manager=fake_manager
        )
        user_claims = DummyUserClaims("user-123")

        with pytest.raises(BadRequest) as exc:
            await service.generate_api_key(user_claims)

        assert exc.value.user_message == UNIQUE_API_KEY_GENERATION_FAILED

        pattern = FAILED_GENERATE_API_KEY_RETRIES_LOG_MESSAGE.format(attempts="\d+")
        assert re.fullmatch(pattern, exc.value.log_message)

    async def test_generate_api_key_raises_on_store_exception(self):
        fake_store = FakeApiKeyStore()
        fake_manager = FakeAPIKeyManager(fake_store)
        fake_manager.set_fixed_key("dvd_mock_key")
        fake_store.set_exception("save_api_key", RuntimeError("DB error"))

        service = PostApiKeyService(
            api_key_store=fake_store, api_key_manager=fake_manager
        )
        user_claims = DummyUserClaims("user-123")

        with pytest.raises(RuntimeError, match="DB error"):
            await service.generate_api_key(user_claims)


@pytest.mark.asyncio
class TestRevokeApiKeyService:

    async def test_successful_revoke(self):
        store = FakeApiKeyStore()
        user_id = "user123"
        fake_key_id = uuid4()
        key = SimpleNamespace(id=fake_key_id, user_id=user_id, is_active=True)
        store.stored_keys.append(key)
        service = RevokeApiKeyService(api_key_store=store)

        claims = UserClaims(sub=user_id)
        result = await service.revoke_api_key(claims, api_key_id=fake_key_id)

        assert result == 1
        assert not key.is_active

    async def test_revoke_fails_when_key_not_found(self):
        store = FakeApiKeyStore()
        service = RevokeApiKeyService(api_key_store=store)
        claims = UserClaims(sub="user123")

        with pytest.raises(ResourceNotFound):
            await service.revoke_api_key(claims, api_key_id=uuid4())

    async def test_revoke_handles_store_exception(self):
        store = FakeApiKeyStore()
        store.set_exception(
            "set_inactive_by_user_id_and_api_key_id", RuntimeError("DB Error")
        )
        service = RevokeApiKeyService(api_key_store=store)
        claims = UserClaims(sub="user123")

        with pytest.raises(RuntimeError, match="DB Error"):
            await service.revoke_api_key(claims, api_key_id=uuid4())
            

@pytest.mark.asyncio
class TestAPIKeyPublicResponse:

    def test_valid_instantiation(self):
        now = datetime.datetime.utcnow()
        response = APIKeyPublicResponse(
            user_id="user123",
            masked_api_key="****abcd",
            created_at=now,
            last_used_at=now,
        )

        assert response.user_id == "user123"
        assert response.masked_api_key == "****abcd"
        assert response.created_at == now
        assert response.last_used_at == now

    def test_optional_last_used_at_none(self):
        now = datetime.datetime.utcnow()
        response = APIKeyPublicResponse(
            user_id="user123",
            masked_api_key="****abcd",
            created_at=now,
        )

        assert response.last_used_at is None

    def test_missing_required_field_raises(self):
        now = datetime.datetime.utcnow()
        with pytest.raises(ValidationError):
            APIKeyPublicResponse(
                masked_api_key="****abcd", created_at=now
            )

@pytest.mark.asyncio
class TestGetApiKeyService:

    async def test_get_api_keys_by_user_returns_expected_models(self):
        store = FakeApiKeyStore()
        now = datetime.datetime.utcnow()
        store.stored_keys = [
            SimpleNamespace(
                id="1",
                user_id="user123",
                masked_api_key="****abcd",
                is_active=True,
                created_at=now,
                updated_at=now,
                last_used_at=None,
            )
        ]
        service = GetApiKeyService(api_key_store=store)
        claims = UserClaims(sub="user123")

        result = await service.get_api_keys_by_user(user_claims=claims)

        assert len(result) == 1
        assert isinstance(result[0], APIKeyPublicResponse)
        assert result[0].user_id == "user123"

    async def test_returns_empty_list_when_no_keys(self):
        store = FakeApiKeyStore()
        service = GetApiKeyService(api_key_store=store)
        claims = UserClaims(sub="user123")

        result = await service.get_api_keys_by_user(user_claims=claims)

        assert result == []

    async def test_get_api_keys_by_user_propagates_exception(self):
        store = FakeApiKeyStore()
        store.set_exception("get_all_api_keys", RuntimeError("store error"))
        service = GetApiKeyService(api_key_store=store)
        claims = UserClaims(sub="user123")

        with pytest.raises(RuntimeError, match="store error"):
            await service.get_api_keys_by_user(user_claims=claims)