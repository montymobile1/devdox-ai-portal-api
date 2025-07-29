import uuid
from unittest.mock import patch

import pytest

from app.exceptions.custom_exceptions import DevDoxAPIException
from app.repositories.api_key import TortoiseApiKeyStore
from app.schemas.api_key import APIKeyCreate

import app.repositories.api_key as actual_module_path

PATH_TO_REPOSITORY_APIKEY = (
    f"{actual_module_path.__name__}.{actual_module_path.APIKEY.__name__}"
)
PATH_TO_REPOSITORY_FILTER = (
    f"{PATH_TO_REPOSITORY_APIKEY}.{actual_module_path.APIKEY.filter.__name__}"
)
PATH_TO_REPOSITORY_CREATE = (
    f"{PATH_TO_REPOSITORY_APIKEY}.{actual_module_path.APIKEY.create.__name__}"
)


@pytest.mark.asyncio
class TestTortoiseApiKeyStore:

    async def test_query_for_existing_hashes_returns_false_on_invalid_input(self):
        store = TortoiseApiKeyStore()

        assert await store.query_for_existing_hashes(None) is False
        assert await store.query_for_existing_hashes("") is False
        assert await store.query_for_existing_hashes("   ") is False

    async def test_save_api_key_calls_model_create(self):
        store = TortoiseApiKeyStore()
        with patch(PATH_TO_REPOSITORY_CREATE) as mock_create:
            model = APIKeyCreate(user_id="u", api_key="a", masked_api_key="m")
            await store.save_api_key(model)
            mock_create.assert_called_once_with(**model.model_dump())

    async def test_set_inactive_returns_negative_on_invalid_input(self):
        store = TortoiseApiKeyStore()

        invalid_cases = [
            (None, uuid.uuid4()),
            (" ", uuid.uuid4()),
            ("user", None),
        ]

        for user_id, key_id in invalid_cases:
            result = await store.set_inactive_by_user_id_and_api_key_id(user_id, key_id)
            assert result == -1

    @pytest.mark.parametrize(
        "input_user_id",
        [
            None,
            "",
            " "
        ],
        ids=[
            "None user_id",
            "Empty user_id",
            "Whitespace user_id",
        ],
    )
    async def test_get_all_api_keys_returns_empty_on_blank_user_id(self, input_user_id):
        store = TortoiseApiKeyStore()

        with pytest.raises(DevDoxAPIException) as exp:
            await store.get_all_api_keys(0, 20, input_user_id)
        
        assert exp.value.error_type == store.InternalExceptions.MISSING_USER_ID.value.get("error_type")
        