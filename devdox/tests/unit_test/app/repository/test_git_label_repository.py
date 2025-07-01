import uuid
from unittest.mock import AsyncMock, patch

import pytest

from app.exceptions.custom_exceptions import DevDoxAPIException
import app.repositories.git_label as actual_module_path

PATH_TO_ACTUAL_MODULE = actual_module_path.__name__

PATH_TO_GITLABEL = (
    f"{actual_module_path.__name__}.{actual_module_path.GitLabel.__name__}"
)
PATH_TO_GITLABEL_FILTER = (
    f"{PATH_TO_GITLABEL}.{actual_module_path.GitLabel.filter.__name__}"
)



@pytest.mark.asyncio
class TestTortoiseGitLabelStore:

    def setup_method(self):
        self.store = actual_module_path.TortoiseGitLabelStore()

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

    async def test_delete_by_id_and_user_id_returns_minus_one_for_invalid_input(self):
        result = await self.store.delete_by_id_and_user_id(label_id=None, user_id=" ")
        assert result == -1

    @pytest.mark.parametrize(
        "input_label_id,input_user_id",
        [
            (None, "valid_user_id"),
            (uuid.uuid4(), None),
            (uuid.uuid4(), ""),
            (uuid.uuid4(), " "),
        ],
        ids=[
            "None label_id",
            "None user_id",
            "Empty user_id",
            "Whitespace user_id",
        ],
    )
    async def test_delete_by_id_and_user_id_returns_none_when_input_invalid(
        self, input_label_id, input_user_id
    ):
        result = await self.store.delete_by_id_and_user_id(
            label_id=input_label_id, user_id=input_user_id
        )
        assert result == -1

    @patch(PATH_TO_GITLABEL_FILTER)
    async def test_delete_by_id_and_user_id_returns_zero_if_no_rows_deleted(
        self, mock_filter
    ):
        mock_query = AsyncMock()
        mock_query.delete.return_value = 0
        mock_filter.return_value = mock_query

        result = await self.store.delete_by_id_and_user_id(
            label_id=uuid.uuid4(), user_id="user123"
        )
        assert result == 0

    @patch(PATH_TO_GITLABEL_FILTER)
    async def test_delete_by_id_and_user_id_returns_row_count_on_success(
        self, mock_filter
    ):
        mock_query = AsyncMock()
        mock_query.delete.return_value = 1
        mock_filter.return_value = mock_query

        result = await self.store.delete_by_id_and_user_id(
            label_id=uuid.uuid4(), user_id="user123"
        )
        assert result == 1
