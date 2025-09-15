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
from models_src.dto.git_label import GitLabelResponseDTO
from models_src.dto.repo import GitHosting
from models_src.exceptions.utils import GitLabelErrors, internal_error
from models_src.test_doubles.repositories.git_label import (
    FakeGitLabelStore,
    make_fake_git_label,
)
from models_src.test_doubles.repositories.user import FakeUserStore, make_fake_user


@pytest.mark.asyncio
class TestGetGitLabelService__GetGitLabelsByUser:
    def setup_method(self):
        self.fake_store = FakeGitLabelStore()
        self.service = GetGitLabelService(label_repository=self.fake_store)
        self.user_claims = UserClaims(sub="user123")

    async def test_returns_empty_if_store_count_is_zero(self):
        self.fake_store.set_fake_data([])
        pagination = RequiredPaginationParams(limit=10, offset=0)

        result = await self.service.get_git_labels_by_user(
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
        assert (self.fake_store.count_by_user_id.__name__, (), {'git_hosting': None, 'user_id': 'user123'}) in self.fake_store.received_calls

    async def test_returns_formatted_git_labels(self):
        fake_label = make_fake_git_label(user_id="user123", label="bugfix")
        self.fake_store.set_fake_data([fake_label])
        pagination = RequiredPaginationParams(limit=10, offset=0)

        result = await self.service.get_git_labels_by_user(
            pagination=pagination,
            user_claims=self.user_claims,
            git_hosting="github",
        )

        assert result["total"] == 1
        assert result["items"][0]["label"] == "bugfix"
        assert result["items"][0]["masked_token"] == "****1234"
        assert (
            self.fake_store.count_by_user_id.__name__,
            (),
            {'git_hosting': 'github', 'user_id': 'user123'}
        ) in self.fake_store.received_calls
        
        assert (
            self.fake_store.find_all_by_user_id.__name__,
            (),
            {'git_hosting': 'github', 'limit': 10, 'offset': 0, 'user_id': 'user123'}
        ) in self.fake_store.received_calls

    async def test_bubbles_up_store_exception(self):
        self.fake_store.set_exception(self.fake_store.count_by_user_id, ValueError("Boom"))
        pagination = RequiredPaginationParams(limit=10, offset=0)

        with pytest.raises(ValueError) as exc:
            await self.service.get_git_labels_by_user(
                pagination=pagination,
                user_claims=self.user_claims,
                git_hosting=None,
            )

        assert str(exc.value) == "Boom"


@pytest.mark.asyncio
class TestGetGitLabelService__GetGitLabelsByLabel:

    def setup_method(self):
        self.store = FakeGitLabelStore()
        self.service = GetGitLabelService(label_repository=self.store)
        self.user_claims = UserClaims(sub="user123")
        self.pagination = PaginationParams(limit=10, offset=0)

    async def test_get_git_labels_by_label_returns_formatted(self):
        label = make_fake_git_label(user_id="user123", label="bug")
        self.store.set_fake_data([label])

        result = await self.service.get_git_labels_by_label(
            pagination=self.pagination,
            user_claims=self.user_claims,
            label="bug",
        )
        
        dict_res = result.get('items', {})
        assert dict_res[0]["label"] == "bug"
        assert dict_res[0]["masked_token"] == "****1234"

    async def test_get_git_labels_by_label_handles_store_exception(self):
        self.store.set_exception(
            self.store.count_by_user_id_and_label, ValueError("Simulated error")
        )

        with pytest.raises(ValueError, match="Simulated error"):
            await self.service.get_git_labels_by_label(
                pagination=self.pagination,
                user_claims=self.user_claims,
                label="bug",
            )

    async def test_get_git_labels_by_label_returns_empty_list(self):
        self.store.set_fake_data([])

        result = await self.service.get_git_labels_by_label(
            pagination=self.pagination, user_claims=self.user_claims, label="anything"
        )

        assert result["items"] == []

    async def test_get_git_labels_by_label_applies_formatting(self):
        label = make_fake_git_label(
            user_id="user123", label="bug", masked_token="****abcd"
        )
        self.store.set_fake_data([label])

        result = await self.service.get_git_labels_by_label(
            pagination=self.pagination, user_claims=self.user_claims, label="bug"
        )

        item = result.get("items", {})[0]
        assert item["label"] == "bug"
        assert item["masked_token"] == "****abcd"
        assert "id" in item and "created_at" in item

    async def test_get_git_labels_by_label_passes_correct_arguments(self):
        label = make_fake_git_label(user_id="user123", label="feature")
        self.store.set_fake_data([label])

        await self.service.get_git_labels_by_label(
            pagination=self.pagination, user_claims=self.user_claims, label="feature"
        )

        assert (
            self.store.find_all_by_user_id_and_label.__name__,
            (),
            {'label': 'feature', 'limit': 10, 'offset': 0, 'user_id': 'user123'}
        ) in self.store.received_calls


class TestPostGitLabelService__AddGitToken:

    def setup_method(self):
        self.fake_label_store = FakeGitLabelStore()
        self.fake_user_store = FakeUserStore()
        self.fake_crypto = FakeEncryptionHelper()
        self.fake_fetcher = FakeRepoFetcher()

        self.service = PostGitLabelService(
            user_repository=self.fake_user_store,
            label_repository=self.fake_label_store,
            crypto_store=self.fake_crypto,
            git_manager=self.fake_fetcher,
        )

        self.valid_user = make_fake_user(user_id="user123")
        self.fake_user_store.set_fake_data(fake_data=[self.valid_user])

        self.valid_payload = GitLabelBase(
            label="label1", token_value="mytoken", git_hosting=GitHosting.GITHUB
        )

    @pytest.mark.asyncio
    async def test_add_token_success(self):
        result = await self.service.add_git_token(
            user_claims=UserClaims(sub="user123"), json_payload=self.valid_payload
        )

        assert result.label == "label1"
        assert result.username == "mockuser"

    @pytest.mark.asyncio
    async def test_raises_if_token_is_blank(self):
        self.valid_payload.token_value = "   "

        with pytest.raises(BadRequest) as exc:
            await self.service.add_git_token(
                UserClaims(sub="user123"), self.valid_payload
            )

        assert exc.value.user_message == TOKEN_MISSING

    @pytest.mark.asyncio
    async def test_raises_if_user_not_found(self):
        with pytest.raises(ResourceNotFound) as exc:
            await self.service.add_git_token(
                UserClaims(sub="user_not_found"), self.valid_payload
            )

        assert exc.value.user_message == USER_RESOURCE_NOT_FOUND

    @pytest.mark.asyncio
    async def test_raises_if_git_user_is_none(self):
        self.fake_fetcher.github_fetcher.repo_user = None

        with pytest.raises(ResourceNotFound) as exc:
            await self.service.add_git_token(
                UserClaims(sub="user123"), self.valid_payload
            )

        assert exc.value.user_message == TOKEN_MISSING

    @pytest.mark.asyncio
    async def test_raises_if_integrity_error(self):
        self.fake_label_store.set_exception(
            self.fake_label_store.save,
            internal_error(**GitLabelErrors.GIT_LABEL_ALREADY_EXISTS.value)
        )

        with pytest.raises(BadRequest) as exc:
            await self.service.add_git_token(
                UserClaims(sub="user123"), self.valid_payload
            )

        assert exc.value.user_message == GENERIC_ALREADY_EXIST


def make_fake_user_claims(user_id="user123"):
    return UserClaims(sub=user_id)


@pytest.mark.asyncio
class TestDeleteGitLabelService__DeleteByGitLabelId:

    def setup_method(self):
        self.fake_store = FakeGitLabelStore()
        self.service = DeleteGitLabelService(label_repository=self.fake_store)
        self.user_claims = make_fake_user_claims()
        self.existing_label_id = uuid.uuid4()

    async def test_returns_label_when_found(self):
        # Arrange
        self.fake_store.set_fake_data(fake_data=[
            GitLabelResponseDTO(
                id=self.existing_label_id,
                user_id="user123",
                label="GitLabel"
            )
        ])
        
        # Act
        result = await self.service.delete_by_git_label_id(
            user_claims=self.user_claims, git_label_id=self.existing_label_id
        )

        # Assert
        assert result == 1
        assert (
            'delete_by_id_and_user_id',
            (),
            {'label_id': self.existing_label_id, 'user_id': 'user123'}
        ) in self.fake_store.received_calls

    async def test_raises_when_label_not_found(self):
        # Arrange: empty store
        self.fake_store.set_fake_data([])

        # Act & Assert
        with pytest.raises(ResourceNotFound) as exc:
            await self.service.delete_by_git_label_id(
                user_claims=self.user_claims, git_label_id=self.existing_label_id
            )

        assert exc.value.user_message == TOKEN_NOT_FOUND
        assert (
            self.fake_store.delete_by_id_and_user_id.__name__,
            (),
            {'label_id': self.existing_label_id, 'user_id': 'user123'}
        ) in self.fake_store.received_calls
