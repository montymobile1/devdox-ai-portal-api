import uuid

import pytest
from tortoise.exceptions import IntegrityError

from app.exceptions.custom_exceptions import BadRequest, ResourceNotFound
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
from tests.unit_test.test_doubles.app.repository.get_label_repository_doubles import (
    FakeGitLabelStore,
    make_fake_git_label,
)
from tests.unit_test.test_doubles.app.repository.user_repository_doubles import (
    FakeUserStore,
    make_fake_user,
)
from tests.unit_test.test_doubles.app.utils.encryption_doubles import (
    FakeEncryptionHelper,
)
from tests.unit_test.test_doubles.app.utils.repo_fetcher_doubles import FakeRepoFetcher


@pytest.mark.asyncio
class TestGetGitLabelService__GetGitLabelsByUser:
    def setup_method(self):
        self.fake_store = FakeGitLabelStore()
        self.service = GetGitLabelService(label_store=self.fake_store)
        self.user_claims = UserClaims(sub="user123")

    async def test_returns_empty_if_store_count_is_zero(self):
        self.fake_store.set_fake_data([], total_count=0)
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
        assert ("count_by_user_id", "user123", None) in self.fake_store.received_calls

    async def test_returns_formatted_git_labels(self):
        fake_label = make_fake_git_label(user_id="user123", label="bugfix")
        self.fake_store.set_fake_data([fake_label], total_count=1)
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
            "count_by_user_id",
            "user123",
            "github",
        ) in self.fake_store.received_calls
        assert (
            "get_by_user_id",
            0,
            10,
            "user123",
            "github",
        ) in self.fake_store.received_calls

    async def test_bubbles_up_store_exception(self):
        self.fake_store.set_exception("count_by_user_id", ValueError("Boom"))
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
        self.service = GetGitLabelService(label_store=self.store)
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

        assert result[0]["label"] == "bug"
        assert result[0]["masked_token"] == "****1234"

    async def test_get_git_labels_by_label_handles_store_exception(self):
        self.store.set_exception(
            "get_by_user_id_and_label", ValueError("Simulated error")
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

        assert result == []

    async def test_get_git_labels_by_label_applies_formatting(self):
        label = make_fake_git_label(
            user_id="user123", label="bug", masked_token="****abcd"
        )
        self.store.set_fake_data([label])

        result = await self.service.get_git_labels_by_label(
            pagination=self.pagination, user_claims=self.user_claims, label="bug"
        )

        item = result[0]
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
            "get_by_user_id_and_label",
            0,
            10,
            "user123",
            "feature",
        ) in self.store.received_calls


class TestPostGitLabelService__AddGitToken:

    def setup_method(self):
        self.fake_label_store = FakeGitLabelStore()
        self.fake_user_store = FakeUserStore()
        self.fake_crypto = FakeEncryptionHelper()
        self.fake_fetcher = FakeRepoFetcher()

        self.service = PostGitLabelService(
            user_store=self.fake_user_store,
            label_store=self.fake_label_store,
            crypto_store=self.fake_crypto,
            git_manager=self.fake_fetcher,
        )

        self.valid_user = make_fake_user(user_id="user123")
        self.fake_user_store.set_fake_user(self.valid_user)

        self.valid_payload = GitLabelBase(
            label="label1", token_value="mytoken", git_hosting="github"
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
        self.fake_user_store.set_fake_user(None)

        with pytest.raises(ResourceNotFound) as exc:
            await self.service.add_git_token(
                UserClaims(sub="user123"), self.valid_payload
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
        self.fake_label_store.set_exception("create_new", IntegrityError("fail"))

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
        self.service = DeleteGitLabelService(label_store=self.fake_store)
        self.user_claims = make_fake_user_claims()
        self.existing_label_id = uuid.uuid4()

    async def test_returns_label_when_found(self):
        # Arrange
        self.fake_store.git_labels = [
            type("GitLabel", (), {"id": self.existing_label_id, "user_id": "user123"})()
        ]

        # Act
        result = await self.service.delete_by_git_label_id(
            user_claims=self.user_claims, git_label_id=self.existing_label_id
        )

        # Assert
        assert result == 1
        assert (
            "delete_by_id_and_user_id",
            self.existing_label_id,
            "user123",
        ) in self.fake_store.received_calls

    async def test_raises_when_label_not_found(self):
        # Arrange: empty store
        self.fake_store.git_labels = []

        # Act & Assert
        with pytest.raises(ResourceNotFound) as exc:
            await self.service.delete_by_git_label_id(
                user_claims=self.user_claims, git_label_id=self.existing_label_id
            )

        assert exc.value.user_message == TOKEN_NOT_FOUND
        assert (
            "delete_by_id_and_user_id",
            self.existing_label_id,
            "user123",
        ) in self.fake_store.received_calls
