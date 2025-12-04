import uuid

import pytest
from devdox_ai_git.test_doubles.repo_fetcher_doubles import FakeRepoFetcher
from encryption_src.test_doubles import FakeEncryptionHelper

from app.exceptions.local_exceptions import BadRequest, ResourceNotFound
from app.exceptions.exception_constants import (
    GENERIC_ALREADY_EXIST,
    TOKEN_MISSING,
    TOKEN_NOT_FOUND,
    USER_RESOURCE_NOT_FOUND,
)
from app.schemas.basic import PaginationParams, RequiredPaginationParams
from app.schemas.git_label import GitLabelBase
from app.services.git_tokens import (
    DeleteGitLabelService,
    GetGitLabelService,
    PostGitLabelService,
)
from app.utils.auth import UserClaims
from models_src import GenericFakeStore, GitLabelResponseDTO, GitHosting, GitLabelErrors, \
    InMemoryGitLabelBackend, InMemoryUserBackend, internal_error, make_fake_git_label, make_fake_user


@pytest.mark.asyncio
class TestGetGitLabelServiceGetGitLabelsByUser:
    
    IN_MEMO_GIT_LABEL = InMemoryGitLabelBackend
    
    def setup_method(self):
        self.user_claims = UserClaims(sub="user123")

    async def test_returns_empty_if_store_count_is_zero(self):
        
        fake_label_store = GenericFakeStore(in_memory_backend=self.IN_MEMO_GIT_LABEL())
        fake_label_store.backend.set_data_store([])
        
        service = GetGitLabelService(label_repository=fake_label_store)
        
        pagination = RequiredPaginationParams(limit=10, offset=0)

        result = await service.get_git_labels_by_user(
            pagination=pagination,
            user_claims=self.user_claims,
            git_hosting=None,
        )

        assert result == {
            "items": [],
            "total": 0,
            "page": 1,
            "size": 10,
        }
        assert (fake_label_store.store.count_by_user_id.__name__, (), {'git_hosting': None, 'user_id': 'user123'}) in fake_label_store.received_calls

    async def test_returns_formatted_git_labels(self):
        
        fake_label_store = GenericFakeStore(in_memory_backend=self.IN_MEMO_GIT_LABEL())
        fake_label = make_fake_git_label(user_id="user123", label="bugfix")
        fake_label_store.backend.set_data_store([fake_label])
        
        service = GetGitLabelService(label_repository=fake_label_store)
        
        pagination = RequiredPaginationParams(limit=10, offset=0)

        result = await service.get_git_labels_by_user(
            pagination=pagination,
            user_claims=self.user_claims,
            git_hosting="github",
        )

        assert result["total"] == 1
        assert result["items"][0]["label"] == "bugfix"
        assert result["items"][0]["masked_token"] == "****1234"
        assert (
            fake_label_store.store.count_by_user_id.__name__,
            (),
            {'git_hosting': 'github', 'user_id': 'user123'}
        ) in fake_label_store.received_calls
        
        assert (
            fake_label_store.store.find_all_by_user_id.__name__,
            (),
            {'git_hosting': 'github', 'limit': 10, 'offset': 0, 'user_id': 'user123'}
        ) in fake_label_store.received_calls

    async def test_bubbles_up_store_exception(self):
        
        fake_label_store = GenericFakeStore(in_memory_backend=self.IN_MEMO_GIT_LABEL())
        fake_label_store.set_exception(fake_label_store.store.count_by_user_id, ValueError("Boom"))
        
        service = GetGitLabelService(label_repository=fake_label_store)
        
        
        pagination = RequiredPaginationParams(limit=10, offset=0)

        with pytest.raises(ValueError) as exc:
            await service.get_git_labels_by_user(
                pagination=pagination,
                user_claims=self.user_claims,
                git_hosting=None,
            )

        assert str(exc.value) == "Boom"


@pytest.mark.asyncio
class TestGetGitLabelServiceGetGitLabelsByLabel:
    
    IN_MEMO_GIT_LABEL = InMemoryGitLabelBackend
    
    def setup_method(self):
        self.user_claims = UserClaims(sub="user123")
        self.pagination = PaginationParams(limit=10, offset=0)

    async def test_get_git_labels_by_label_returns_formatted(self):
        
        fake_label_store = GenericFakeStore(in_memory_backend=self.IN_MEMO_GIT_LABEL())
        label = make_fake_git_label(user_id="user123", label="bug")
        fake_label_store.backend.set_data_store([label])
        
        service = GetGitLabelService(label_repository=fake_label_store)
        
        result = await service.get_git_labels_by_label(
            pagination=self.pagination,
            user_claims=self.user_claims,
            label="bug",
        )
        
        dict_res = result.get('items', {})
        assert dict_res[0]["label"] == "bug"
        assert dict_res[0]["masked_token"] == "****1234"

    async def test_get_git_labels_by_label_handles_store_exception(self):

        fake_label_store = GenericFakeStore(in_memory_backend=self.IN_MEMO_GIT_LABEL())
        fake_label_store.set_exception(
            fake_label_store.store.count_by_user_id_and_label, ValueError("Simulated error")
        )
        
        service = GetGitLabelService(label_repository=fake_label_store)
        
        with pytest.raises(ValueError, match="Simulated error"):
            await service.get_git_labels_by_label(
                pagination=self.pagination,
                user_claims=self.user_claims,
                label="bug",
            )

    async def test_get_git_labels_by_label_returns_empty_list(self):
        
        fake_label_store = GenericFakeStore(in_memory_backend=self.IN_MEMO_GIT_LABEL())
        fake_label_store.backend.set_data_store([])
        
        service = GetGitLabelService(label_repository=fake_label_store)

        result = await service.get_git_labels_by_label(
            pagination=self.pagination, user_claims=self.user_claims, label="anything"
        )

        assert result["items"] == []

    async def test_get_git_labels_by_label_applies_formatting(self):
        
        fake_label_store = GenericFakeStore(in_memory_backend=self.IN_MEMO_GIT_LABEL())
        
        label = make_fake_git_label(
            user_id="user123", label="bug", masked_token="****abcd"
        )
        fake_label_store.backend.set_data_store([label])
        
        service = GetGitLabelService(label_repository=fake_label_store)
        
        result = await service.get_git_labels_by_label(
            pagination=self.pagination, user_claims=self.user_claims, label="bug"
        )

        item = result.get("items", {})[0]
        assert item["label"] == "bug"
        assert item["masked_token"] == "****abcd"
        assert "id" in item and "created_at" in item

    async def test_get_git_labels_by_label_passes_correct_arguments(self):
        
        fake_label_store = GenericFakeStore(in_memory_backend=self.IN_MEMO_GIT_LABEL())
        label = make_fake_git_label(user_id="user123", label="feature")
        fake_label_store.backend.set_data_store([label])
        
        service = GetGitLabelService(label_repository=fake_label_store)
    
        await service.get_git_labels_by_label(
            pagination=self.pagination, user_claims=self.user_claims, label="feature"
        )

        assert (
            fake_label_store.store.find_all_by_user_id_and_label.__name__,
            (),
            {'label': 'feature', 'limit': 10, 'offset': 0, 'user_id': 'user123'}
        ) in fake_label_store.received_calls


class TestPostGitLabelServiceAddGitToken:
    
    IN_MEMO_GIT_LABEL = InMemoryGitLabelBackend
    IN_MEMO_USER = InMemoryUserBackend
    
    def setup_method(self):
        self.fake_crypto = FakeEncryptionHelper()
        self.fake_fetcher = FakeRepoFetcher()

        self.valid_user = make_fake_user(user_id="user123")

        self.valid_payload = GitLabelBase(
            label="label1", token_value="mytoken", git_hosting=GitHosting.GITHUB
        )

    @pytest.mark.asyncio
    async def test_add_token_success(self):
        
        fake_label_store = GenericFakeStore(in_memory_backend=self.IN_MEMO_GIT_LABEL())
        fake_user_store = GenericFakeStore(in_memory_backend=self.IN_MEMO_USER())
        
        fake_user_store.backend.set_data_store(fake_data=[self.valid_user])
        
        
        service = PostGitLabelService(
            user_repository=fake_user_store,
            label_repository=fake_label_store,
            crypto_store=self.fake_crypto,
            git_manager=self.fake_fetcher,
        )
        
        result = await service.add_git_token(
            user_claims=UserClaims(sub="user123"), json_payload=self.valid_payload
        )

        assert result.label == "label1"
        assert result.username == "mockuser"

    @pytest.mark.asyncio
    async def test_raises_if_token_is_blank(self):
        self.valid_payload.token_value = "   "
        
        fake_label_store = GenericFakeStore(in_memory_backend=self.IN_MEMO_GIT_LABEL())
        fake_user_store = GenericFakeStore(in_memory_backend=self.IN_MEMO_USER())
        fake_user_store.backend.set_data_store(fake_data=[self.valid_user])
        
        
        service = PostGitLabelService(
            user_repository=fake_user_store,
            label_repository=fake_label_store,
            crypto_store=self.fake_crypto,
            git_manager=self.fake_fetcher,
        )
        
        with pytest.raises(BadRequest) as exc:
            await service.add_git_token(
                UserClaims(sub="user123"), self.valid_payload
            )

        assert exc.value.user_message == TOKEN_MISSING

    @pytest.mark.asyncio
    async def test_raises_if_user_not_found(self):
        
        fake_label_store = GenericFakeStore(in_memory_backend=self.IN_MEMO_GIT_LABEL())
        fake_user_store = GenericFakeStore(in_memory_backend=self.IN_MEMO_USER())
        fake_user_store.backend.set_data_store(fake_data=[self.valid_user])
        
        
        service = PostGitLabelService(
            user_repository=fake_user_store,
            label_repository=fake_label_store,
            crypto_store=self.fake_crypto,
            git_manager=self.fake_fetcher,
        )
        
        with pytest.raises(ResourceNotFound) as exc:
            await service.add_git_token(
                UserClaims(sub="user_not_found"), self.valid_payload
            )

        assert exc.value.user_message == USER_RESOURCE_NOT_FOUND

    @pytest.mark.asyncio
    async def test_raises_if_git_user_is_none(self):
        self.fake_fetcher.github_fetcher.repo_user = None
        
        fake_label_store = GenericFakeStore(in_memory_backend=self.IN_MEMO_GIT_LABEL())
        fake_user_store = GenericFakeStore(in_memory_backend=self.IN_MEMO_USER())
        fake_user_store.backend.set_data_store(fake_data=[self.valid_user])
        
        
        service = PostGitLabelService(
            user_repository=fake_user_store,
            label_repository=fake_label_store,
            crypto_store=self.fake_crypto,
            git_manager=self.fake_fetcher,
        )
        
        with pytest.raises(ResourceNotFound) as exc:
            await service.add_git_token(
                UserClaims(sub="user123"), self.valid_payload
            )

        assert exc.value.user_message == TOKEN_MISSING

    @pytest.mark.asyncio
    async def test_raises_if_integrity_error(self):
        
        fake_label_store = GenericFakeStore(in_memory_backend=self.IN_MEMO_GIT_LABEL())
        fake_label_store.set_exception(
            fake_label_store.store.save,
            internal_error(**GitLabelErrors.GIT_LABEL_ALREADY_EXISTS.value)
        )
        
        fake_user_store = GenericFakeStore(in_memory_backend=self.IN_MEMO_USER())
        fake_user_store.backend.set_data_store(fake_data=[self.valid_user])
        
        service = PostGitLabelService(
            user_repository=fake_user_store,
            label_repository=fake_label_store,
            crypto_store=self.fake_crypto,
            git_manager=self.fake_fetcher,
        )
        
        with pytest.raises(BadRequest) as exc:
            await service.add_git_token(
                UserClaims(sub="user123"), self.valid_payload
            )

        assert exc.value.user_message == GENERIC_ALREADY_EXIST


def make_fake_user_claims(user_id="user123"):
    return UserClaims(sub=user_id)


@pytest.mark.asyncio
class TestDeleteGitLabelServiceDeleteByGitLabelId:
    
    IN_MEMO_GIT_LABEL = InMemoryGitLabelBackend
    
    def setup_method(self):
        self.user_claims = make_fake_user_claims()
        self.existing_label_id = uuid.uuid4()

    async def test_returns_label_when_found(self):
        # Arrange
        
        fake_label_store = GenericFakeStore(in_memory_backend=self.IN_MEMO_GIT_LABEL())
        fake_label_store.backend.set_data_store(fake_data=[
            GitLabelResponseDTO(
                id=self.existing_label_id,
                user_id="user123",
                label="GitLabel"
            )
        ])
        
        service = DeleteGitLabelService(label_repository=fake_label_store)
        
        # Act
        result = await service.delete_by_git_label_id(
            user_claims=self.user_claims, git_label_id=self.existing_label_id
        )

        # Assert
        assert result == 1
        assert (
            fake_label_store.store.delete_by_id_and_user_id.__name__,
            (),
            {'label_id': self.existing_label_id, 'user_id': 'user123'}
        ) in fake_label_store.received_calls

    async def test_raises_when_label_not_found(self):
        # Arrange: empty store
        
        fake_label_store = GenericFakeStore(in_memory_backend=self.IN_MEMO_GIT_LABEL())
        fake_label_store.backend.set_data_store([])
        
        
        service = DeleteGitLabelService(label_repository=fake_label_store)
        
        # Act & Assert
        with pytest.raises(ResourceNotFound) as exc:
            await service.delete_by_git_label_id(
                user_claims=self.user_claims, git_label_id=self.existing_label_id
            )

        assert exc.value.user_message == TOKEN_NOT_FOUND
        assert (
            fake_label_store.store.delete_by_id_and_user_id.__name__,
            (),
            {'label_id': self.existing_label_id, 'user_id': 'user123'}
        ) in fake_label_store.received_calls
