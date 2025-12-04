import datetime
import hashlib
import re
from typing import Optional
from uuid import uuid4

import pytest
from app.exceptions.local_exceptions import BadRequest, ResourceNotFound
from app.exceptions.exception_constants import (
    FAILED_GENERATE_API_KEY_RETRIES_LOG_MESSAGE,
    UNIQUE_API_KEY_GENERATION_FAILED,
)
from app.schemas.api_key import APIKeyPublicResponse
from app.schemas.basic import RequiredPaginationParams
from app.services.api_keys import (
    APIKeyManager,
    APIKeyManagerReturn,
    GetApiKeyService,
    PostApiKeyService,
    RevokeApiKeyService,
)
from app.services.git_tokens import mask_token
from app.utils.auth import UserClaims
from models_src import APIKeyRequestDTO, GenericFakeStore, InMemoryApiKeyBackend

from tests.unit_test.test_doubles.app.service.api_keys import (
    FakeAPIKeyManager,
    StubAPIKeyManager,
)


@pytest.mark.asyncio
class TestAPIKeyManager:
    
    IN_MEMO = InMemoryApiKeyBackend
    
    async def test_generate_unique_key_success(self):
        fake_label_store = GenericFakeStore(in_memory_backend=self.IN_MEMO())
        
        manager = APIKeyManager(api_key_repository=fake_label_store)

        result = await manager.generate_unique_api_key()

        assert result is not None
        assert result.plain.startswith("dvd_")
        assert result.hashed == hashlib.sha256(result.plain.encode("utf-8")).hexdigest()
        assert result.masked == mask_token(result.plain)

    async def test_returns_none_if_hash_exists(self, monkeypatch):
        fake_label_store = GenericFakeStore(in_memory_backend=self.IN_MEMO())
        
        
        manager = APIKeyManager(fake_label_store)

        precomputed_result: Optional[APIKeyManagerReturn] = (
            await manager.generate_unique_api_key()
        )

        await fake_label_store.save(
            APIKeyRequestDTO(
                user_id="user 1234",
                api_key=precomputed_result.hashed,
                masked_api_key=precomputed_result.masked
            )
        )
        
        # overriding what the hash_key method returns
        monkeypatch.setattr(manager, manager.hash_key.__name__, lambda key: precomputed_result.hashed)
        
        result = await manager.generate_unique_api_key()

        assert result is None

    async def test_handles_store_exception(self):
        fake_label_store = GenericFakeStore(in_memory_backend=self.IN_MEMO())
        fake_label_store.set_exception(fake_label_store.store.exists_by_hash_key, RuntimeError("DB error"))
        
        manager = APIKeyManager(fake_label_store)

        with pytest.raises(RuntimeError, match="DB error"):
            await manager.generate_unique_api_key()

    async def test_generate_key_respects_prefix_and_length(self):
        fake_label_store = GenericFakeStore(in_memory_backend=self.IN_MEMO())
        
        manager = APIKeyManager(fake_label_store)

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
    
    IN_MEMO = InMemoryApiKeyBackend
    
    async def test_generate_api_key_success(self):
        
        fake_label_store = GenericFakeStore(in_memory_backend=self.IN_MEMO())
        
        fake_manager = FakeAPIKeyManager(fake_label_store)
        fake_manager.set_fixed_key("dvd_mock_key")

        service = PostApiKeyService(
            api_key_repository=fake_label_store, api_key_manager=fake_manager
        )
        user_claims = DummyUserClaims("user-123")

        key_id, plain = await service.generate_api_key(user_claims)

        assert plain == "dvd_mock_key"
        assert any(k == "user-123" for k, v in fake_label_store.backend.data_store.items())
        assert key_id is not None

    async def test_generate_api_key_fails_after_retries(self):
        fake_label_store = GenericFakeStore(in_memory_backend=self.IN_MEMO())
        
        fake_manager = StubAPIKeyManager()
        
        fake_manager.set_output(
            fake_manager.generate_unique_api_key,
            output=None
        )
        
        service = PostApiKeyService(
            api_key_repository=fake_label_store, api_key_manager=fake_manager
        )
        user_claims = DummyUserClaims("user-123")

        with pytest.raises(BadRequest) as exc:
            await service.generate_api_key(user_claims)

        assert exc.value.user_message == UNIQUE_API_KEY_GENERATION_FAILED

        pattern = FAILED_GENERATE_API_KEY_RETRIES_LOG_MESSAGE.format(attempts="\d+")
        assert re.fullmatch(pattern, exc.value.log_message)


@pytest.mark.asyncio
class TestRevokeApiKeyService:
    
    In_MEMO = InMemoryApiKeyBackend
    
    async def test_successful_revoke(self):
        
        fake_label_store = GenericFakeStore(in_memory_backend=self.In_MEMO())
        
        user_id = "user123"
        
        generated_api_key_id = uuid4()
        
        saved_rec = await fake_label_store.save(APIKeyRequestDTO(
            user_id=user_id,
            api_key=str(generated_api_key_id),
            masked_api_key="masked_api_key_123",
            is_active=True
        ))
        
        service = RevokeApiKeyService(api_key_repository=fake_label_store)

        claims = UserClaims(sub=user_id)
        result = await service.revoke_api_key(claims, api_key_id=saved_rec.id)

        assert result == 1
        assert not saved_rec.is_active

    async def test_revoke_fails_when_key_not_found(self):
        fake_label_store = GenericFakeStore(in_memory_backend=self.In_MEMO())
        
        service = RevokeApiKeyService(api_key_repository=fake_label_store)
        claims = UserClaims(sub="user123")

        with pytest.raises(ResourceNotFound):
            await service.revoke_api_key(claims, api_key_id=uuid4())

    async def test_revoke_handles_store_exception(self):
        fake_label_store = GenericFakeStore(in_memory_backend=self.In_MEMO())
        fake_label_store.set_exception(
            fake_label_store.store.update_is_active_by_user_id_and_api_key_id, RuntimeError("DB Error")
        )
        
        service = RevokeApiKeyService(api_key_repository=fake_label_store)
        claims = UserClaims(sub="user123")

        with pytest.raises(RuntimeError, match="DB Error"):
            await service.revoke_api_key(claims, api_key_id=uuid4())


@pytest.mark.asyncio
class TestAPIKeyPublicResponse:

    def test_valid_instantiation(self):
        now = datetime.datetime.now(datetime.timezone.utc)
        response = APIKeyPublicResponse(
            masked_api_key="****abcd",
            created_at=now,
            last_used_at=now,
            id=uuid4(),
        )

        assert response.masked_api_key == "****abcd"
        assert response.created_at == now
        assert response.last_used_at == now

    def test_optional_last_used_at_none(self):
        now = datetime.datetime.now(datetime.timezone.utc)
        response = APIKeyPublicResponse(
            masked_api_key="****abcd",
            created_at=now,
            id=uuid4()
        )

        assert response.last_used_at is None


@pytest.mark.asyncio
class TestGetApiKeyService:
    
    IN_MEMO = InMemoryApiKeyBackend
    
    async def test_get_api_keys_by_user_returns_expected_models(self):
        fake_label_store = GenericFakeStore(in_memory_backend=self.IN_MEMO())
        
        _ = await fake_label_store.save(
            APIKeyRequestDTO(
                user_id="user123",
                api_key=str(uuid4()),
                masked_api_key="****abcd",
                is_active=True
            )
        )

        service = GetApiKeyService(api_key_repository=fake_label_store)
        claims = UserClaims(sub="user123")
        
        result = await service.get_api_keys_by_user(user_claims=claims, pagination=RequiredPaginationParams(
            offset=0, limit=20
        ))
        
        assert len(result["items"]) == 1
        assert isinstance(result["items"][0], APIKeyPublicResponse)

    async def test_returns_empty_list_when_no_keys(self):
        
        fake_label_store = GenericFakeStore(in_memory_backend=self.IN_MEMO())
        
        service = GetApiKeyService(api_key_repository=fake_label_store)
        claims = UserClaims(sub="user123")
        
        result = await service.get_api_keys_by_user(user_claims=claims, pagination=RequiredPaginationParams(
            offset=0, limit=20
        ))
        
        assert result == {
            "items": [],
            "total": 0,
            "page": 1,
            "size": 20,
        }

    async def test_get_api_keys_by_user_propagates_exception(self):
        fake_label_store = GenericFakeStore(in_memory_backend=self.IN_MEMO())
        fake_label_store.set_exception(fake_label_store.store.count_by_user_id, RuntimeError("store error"))
        
        service = GetApiKeyService(api_key_repository=fake_label_store)
        claims = UserClaims(sub="user123")

        with pytest.raises(RuntimeError, match="store error"):
            await service.get_api_keys_by_user(user_claims=claims, pagination=RequiredPaginationParams(
                offset=0, limit=20
            ))
