import pytest

from app.schemas.basic import PaginationParams, RequiredPaginationParams
from app.services.git_tokens_service import GetGitLabelService
from app.utils.auth import UserClaims
from tests.unit_test.test_doubles.app.repository.get_label_repository_doubles import FakeGitLabelStore, \
	make_fake_git_label


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
            pagination=self.pagination,
            user_claims=self.user_claims,
            label="anything"
        )
        
        assert result == []
    
    async def test_get_git_labels_by_label_applies_formatting(self):
        label = make_fake_git_label(user_id="user123", label="bug", masked_token="****abcd")
        self.store.set_fake_data([label])
        
        result = await self.service.get_git_labels_by_label(
            pagination=self.pagination,
            user_claims=self.user_claims,
            label="bug"
        )
        
        item = result[0]
        assert item["label"] == "bug"
        assert item["masked_token"] == "****abcd"
        assert "id" in item and "created_at" in item
    
    async def test_get_git_labels_by_label_passes_correct_arguments(self):
        label = make_fake_git_label(user_id="user123", label="feature")
        self.store.set_fake_data([label])
        
        await self.service.get_git_labels_by_label(
            pagination=self.pagination,
            user_claims=self.user_claims,
            label="feature"
        )
        
        assert ("get_by_user_id_and_label", 0, 10, "user123", "feature") in self.store.received_calls
