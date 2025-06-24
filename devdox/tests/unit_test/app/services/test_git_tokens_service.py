import pytest

from app.schemas.basic import RequiredPaginationParams
from app.services.git_tokens_service import GetGitLabelService
from app.utils.auth import UserClaims
from tests.unit_test.test_doubles.app.repository.get_label_repository_doubles import FakeGitLabelStore, \
	make_fake_git_label


@pytest.mark.asyncio
class TestGetGitLabelService:
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
        assert ("count_by_user_id", "user123", "github") in self.fake_store.received_calls
        assert ("get_by_user_id", 0, 10, "user123", "github") in self.fake_store.received_calls
    
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
