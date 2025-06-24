import pytest

from app.exceptions.custom_exceptions import DevDoxAPIException
from app.repositories.git_label_repository import TortoiseGitLabelStore


@pytest.mark.asyncio
class TestTortoiseGitLabelStore:

    def setup_method(self):
        self.store = TortoiseGitLabelStore()

    async def test_raises_when_user_id_is_none(self):
        with pytest.raises(DevDoxAPIException) as exc:
            await self.store.get_by_user_id(offset=0, limit=10, user_id=None)

        expected_error = self.store.InternalExceptions.MISSING_USER_ID.value
        assert exc.value.error_type == expected_error.get("error_type")

    async def test_raises_when_user_id_missing_on_count(self):
        with pytest.raises(DevDoxAPIException) as exc:
            await self.store.count_by_user_id(user_id=None)

        expected_error = self.store.InternalExceptions.MISSING_USER_ID.value
        assert exc.value.error_type == expected_error.get("error_type")

    async def test_get_git_hosting_map_returns_empty_list_if_token_ids_empty(self):
        result = await self.store.get_git_hosting_map_by_token_id(token_ids=[])
        assert result == []

    async def test_get_by_token_id_and_user_returns_none_if_token_id_blank(self):
        result = await self.store.get_by_token_id_and_user(
            token_id="", user_id="some-user"
        )
        assert result is None

    async def test_get_by_token_id_and_user_returns_none_if_user_id_blank(self):
        result = await self.store.get_by_token_id_and_user(
            token_id="some-token", user_id=" "
        )
        assert result is None

    async def test_get_by_token_id_and_user_returns_none_if_both_blank(self):
        result = await self.store.get_by_token_id_and_user(token_id="", user_id=" ")
        assert result is None

    async def test_get_by_token_id_and_user_returns_none_if_both_none(self):
        result = await self.store.get_by_token_id_and_user(token_id=None, user_id=None)
        assert result is None

    async def test_get_by_user_id_and_label_raises_when_user_id_is_none(self):
        with pytest.raises(DevDoxAPIException) as exc:
            await self.store.get_by_user_id_and_label(
                offset=0, limit=10, user_id=None, label="any"
            )

        expected_error = self.store.InternalExceptions.MISSING_USER_ID.value
        assert exc.value.error_type == expected_error.get("error_type")

    async def test_get_by_user_id_and_label_raises_when_label_is_none(self):
        with pytest.raises(DevDoxAPIException) as exc:
            await self.store.get_by_user_id_and_label(
                offset=0, limit=10, user_id="user123", label=None
            )

        expected_error = self.store.InternalExceptions.MISSING_LABEL.value
        assert exc.value.error_type == expected_error.get("error_type")
