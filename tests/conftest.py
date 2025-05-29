"""
Pytest fixtures for token API endpoint tests.
Updated for Tortoise ORM-based SupabaseClient.
"""

import pytest
import asyncio
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch, MagicMock, AsyncMock
from app.routes.git_tokens import get_current_user_id
from app.main import app  # Assuming your FastAPI app is in app.main

# Sample encrypted token values for testing
TOKEN_ENCRYPTED_1 = "gAAAAABoMFiNIvAc7WIFnoKXBjkpAVrdiTFrhlmZtG8BBwvmy1dtvfEFmupm0fcvDUo3unosoAQz5eclP2QFMnPMLG4Hj21MBt-xTdWL661JnWP-wQarnLI="
TOKEN_ENCRYPTED_2 = "gAAAAABoMFiNIvAc7WIFnoKXBjkpAVrdiTFrhlmZtG8BBwvmy1dtvfEFmupm0fcvDUo3unosoAQz5eclP2QFMnPMLG4Hj21MBt-xTdWL661JnWP-wQarnLI="
decrypted1_masked = decrypted2_masked = "ghp_************cdef"


@pytest.fixture
def token_decrypted1_masked():
    return "ghp_************cdef"


@pytest.fixture
def token_decrypted1():
    return "ghp_1234567890abcdef"


@pytest.fixture
def token_encrypted1():
    return TOKEN_ENCRYPTED_1


@pytest.fixture
def token_gitlab_decrypted1():
    return "glpat-1234567890abcdef"


@pytest.fixture
def token_gitlab_decrypted1_masked():
    return "glpa**************cdef"


@pytest.fixture
def client():
    """
    Create and return a test client for the FastAPI app.
    """
    return TestClient(app)


@pytest.fixture
def mock_db_client():
    """
    Create a mocked db_client for Tortoise ORM operations.
    """
    with patch("app.routes.git_tokens.db_client") as mock:
        # Setup async mock methods
        mock.execute_query = AsyncMock()
        mock.execute_query_one = AsyncMock()
        mock.insert_row = AsyncMock()
        mock.delete_rows = AsyncMock()
        yield mock


@pytest.fixture
def mock_get_current_user_id():
    """Create a mocked get_current_user_id function."""
    with patch(
        "app.routes.git_tokens.get_current_user_id", new_callable=AsyncMock
    ) as mock:
        mock.return_value = "user-123"
        yield mock


@pytest.fixture(autouse=True)
def override_get_current_user_id():
    async def mock_user():
        return "user-123"

    app.dependency_overrides[get_current_user_id] = mock_user
    yield
    app.dependency_overrides.clear()


@pytest.fixture
def mock_supabase():
    """
    Create a mocked Supabase client (kept for backward compatibility).
    This now mocks the Tortoise ORM-based client.
    """
    with patch("app.services.db_client") as mock:  # Note: using 'Test' alias
        mock_instance = AsyncMock()
        mock.return_value = mock_instance
        yield mock


@pytest.fixture
def token_data_single():
    """
    Return a single token data record for testing.
    """
    return {
        "id": "123",
        "label": "Production GitHub",
        "git_hosting": "github",
        "token_value": TOKEN_ENCRYPTED_1,
        "masked_token": "ghp_************cdef",
        "created_at": "2024-01-01T10:00:00Z",
        "updated_at": "2024-01-02T10:00:00Z",
    }


@pytest.fixture
def token_data_list():
    """
    Return a list of token data records for testing.
    """
    return [
        {
            "id": "1",
            "label": "GitHub Production",
            "git_hosting": "github",
            "token_value": TOKEN_ENCRYPTED_1,
            "masked_token": decrypted1_masked,
            "created_at": "2024-01-01T10:00:00Z",
            "updated_at": "2024-01-02T10:00:00Z",
        },
        {
            "id": "2",
            "label": "GitLab Staging",
            "git_hosting": "gitlab",
            "token_value": TOKEN_ENCRYPTED_2,
            "masked_token": decrypted2_masked,
            "created_at": "2024-01-03T10:00:00Z",
            "updated_at": "2024-01-04T10:00:00Z",
        },
    ]


@pytest.fixture
def invalid_token_data_list():
    """
    Return a list of token data with missing or invalid fields for testing.
    """
    return [
        {
            "id": "3",
            # Missing token_value field
            "label": "Missing Token Value",
            "git_hosting": "github",
            "created_at": "2024-01-01T10:00:00Z",
        },
        {
            # Missing id field
            "label": "Missing ID",
            "git_hosting": "gitlab",
            "token_value": TOKEN_ENCRYPTED_2,
            "created_at": "2024-01-03T10:00:00Z",
        },
        {
            "id": "5",
            "label": "Empty Token Value",
            "git_hosting": "github",
            "token_value": "",  # Empty token
            "created_at": "2024-01-05T10:00:00Z",
        },
    ]


@pytest.fixture
def mock_supabase_select(mock_db_client, token_data_list):
    """
    Setup the mock db_client to return token data list for execute_query.
    """
    mock_db_client.execute_query.return_value = token_data_list
    return mock_db_client


@pytest.fixture
def mock_supabase_filter(mock_supabase, token_data_list):
    """
    Setup the mock Supabase client to return filtered token data using filter method.
    """
    mock_instance = mock_supabase.return_value

    # Configure filter method to return specific results based on filters
    async def side_effect_filter(
        table, filters=None, columns=None, limit=None, single=False
    ):
        if not filters:
            return (
                token_data_list
                if not single
                else (token_data_list[0] if token_data_list else None)
            )

        # Filter by label
        if "label" in filters:
            label = filters["label"]
            filtered = [
                token for token in token_data_list if token.get("label") == label
            ]
            return filtered if not single else (filtered[0] if filtered else None)

        return [] if not single else None

    mock_instance.filter = AsyncMock(side_effect=side_effect_filter)
    return mock_instance


@pytest.fixture
def mock_supabase_empty(mock_supabase):
    """
    Setup the mock Supabase client to return empty results.
    """
    mock_instance = mock_supabase.return_value
    mock_instance.select = AsyncMock(return_value=[])
    mock_instance.filter = AsyncMock(return_value=[])
    return mock_instance


@pytest.fixture
def mock_supabase_invalid_data(mock_supabase, invalid_token_data_list):
    """
    Setup the mock Supabase client to return invalid token data.
    """
    mock_instance = mock_supabase.return_value
    mock_instance.filter = AsyncMock(return_value=invalid_token_data_list)

    async def side_effect_filter(
        table, filters=None, columns=None, limit=None, single=False
    ):
        if filters and "label" in filters:
            # Return the first invalid token data
            return (
                [invalid_token_data_list[0]]
                if not single
                else invalid_token_data_list[0]
            )
        return (
            invalid_token_data_list
            if not single
            else (invalid_token_data_list[0] if invalid_token_data_list else None)
        )

    mock_instance.filter.side_effect = side_effect_filter
    return mock_instance


@pytest.fixture()
def mock_supabase_invalid_label(mock_supabase):
    mock_instance = mock_supabase.return_value
    mock_instance.filter = AsyncMock(return_value=[])
    return mock_instance


@pytest.fixture
def mock_github_manager():
    """Mock for GitHubManager."""
    with patch("app.routes.git_tokens.GitHubManager") as mock:
        yield mock


@pytest.fixture
def mock_gitlab_manager():
    """Mock for GitLabManager."""
    with patch("app.routes.git_tokens.GitLabManager") as mock:
        yield mock


@pytest.fixture
def mock_github_manager_success():
    """Mock for successful GitHubManager authentication."""
    with patch("app.routes.git_tokens.GitHubManager") as mock_class:
        mock_instance = MagicMock()
        mock_instance.auth_status = True
        mock_instance.get_user.return_value = {"login": "testuser"}
        mock_class.return_value = mock_instance
        yield mock_class


@pytest.fixture
def mock_github_manager_failure():
    """Mock for failed GitHubManager authentication."""
    with patch("app.routes.git_tokens.GitHubManager") as mock_class:
        mock_instance = MagicMock()
        mock_instance.auth_status = False
        mock_instance.get_user.return_value = None
        mock_class.return_value = mock_instance
        yield mock_class


@pytest.fixture
def mock_gitlab_manager_success():
    with patch("app.routes.git_tokens.GitLabManager") as mock_class:
        mock_instance = MagicMock()
        mock_instance.auth_status = True
        mock_instance.get_user.return_value = {"username": "testuser"}
        mock_class.return_value = mock_instance
        yield mock_class


@pytest.fixture
def mock_gitlab_manager_auth_failure():
    """Mock for GitLabManager with authentication failure."""
    with patch("app.routes.git_tokens.GitLabManager") as mock_class:
        mock_instance = MagicMock()
        mock_instance.auth_status = False
        mock_class.return_value = mock_instance
        yield mock_class


@pytest.fixture
def mock_gitlab_manager_user_failure():
    """Mock for GitLabManager with user fetch failure."""
    with patch("app.routes.git_tokens.GitLabManager") as mock_class:
        mock_instance = MagicMock()
        mock_instance.auth_status = True
        mock_instance.get_user.return_value = None
        mock_class.return_value = mock_instance
        yield mock_class


@pytest.fixture
def mock_supabase_insert():
    """Mock for SupabaseClient insert operation."""
    with patch("app.routes.git_tokens.db_client") as mock:
        mock.insert_row = AsyncMock(return_value="999")
        yield mock


@pytest.fixture
def mock_supabase_insert_success():
    """Mock for successful SupabaseClient insert operation."""
    with patch("app.routes.git_tokens.db_client") as mock:
        mock.insert_row = AsyncMock(return_value="999")
        yield mock


@pytest.fixture
def sample_token_id():
    """Simple sample token ID for testing"""
    return "67dff10e-d80e-4a90-a737-20afab09a321"


@pytest.fixture
def sample_token_data():
    """Basic sample token data"""
    return {
        "id": "67dff10e-d80e-4a90-a737-20afab09a321",
        "label": "test-token-label",
        "value": "masked-token-value",
        "created_at": "2024-01-01T00:00:00Z",
        "updated_at": "2024-01-01T00:00:00Z",
    }


@pytest.fixture
def token_payload_github():
    """Sample GitHub token payload."""
    return {
        "label": "Test GitHub Token",
        "user_id": "user123",
        "git_hosting": "github",
        "token_value": "ghp_1234567890abcdef",
    }


@pytest.fixture
def token_payload_gitlab():
    """Sample GitLab token payload."""
    return {
        "label": "Test GitLab Token",
        "user_id": "user123",
        "git_hosting": "gitlab",
        "token_value": "glpat-1234567890abcdef",
    }


@pytest.fixture
def mock_api_response():
    """Mock for APIResponse utility class."""
    with patch("app.routes.git_tokens.APIResponse") as mock:
        # Set up success method
        mock.success = MagicMock(
            return_value={
                "success": True,
                "message": "Operation successful",
                "data": {},
            }
        )

        # Set up error method
        mock.error = MagicMock(
            return_value={"success": False, "message": "Operation failed", "data": None}
        )

        yield mock


@pytest.fixture
def mock_supabase_client():
    """
    Basic mock SupabaseClient fixture that returns a mocked client instance.
    Updated for Tortoise ORM async methods.
    """
    with patch("app.routes.git_tokens.db_client") as mock_client:
        # Set default async return values
        mock_client.execute_query_one = AsyncMock(return_value=None)
        mock_client.delete_rows = AsyncMock(return_value=True)
        mock_client.insert_row = AsyncMock(return_value="new-id")
        mock_client.execute_query = AsyncMock(return_value=[])

        yield mock_client


# Additional fixtures for Tortoise ORM specific testing
@pytest.fixture
def mock_tortoise_connection():
    """Mock Tortoise ORM connection."""
    with patch("app.services.supabase_client.connections") as mock_connections:
        mock_conn = AsyncMock()
        mock_connections.get.return_value = mock_conn
        yield mock_conn


@pytest.fixture
def mock_tortoise_init():
    """Mock Tortoise.init for database initialization."""
    with patch("app.services.supabase_client.Tortoise.init") as mock_init:
        mock_init.return_value = AsyncMock()
        yield mock_init


@pytest.fixture
def mock_encryption_helper():
    """Mock EncryptionHelper for token encryption/decryption."""
    with patch("app.routes.git_tokens.EncryptionHelper") as mock_helper:
        mock_instance = MagicMock()
        mock_instance.encrypt.return_value = TOKEN_ENCRYPTED_1
        mock_instance.decrypt.return_value = "ghp_1234567890abcdef"
        mock_helper.return_value = mock_instance
        mock_helper.encrypt = mock_instance.encrypt
        mock_helper.decrypt = mock_instance.decrypt
        yield mock_helper


def mock_general_encryption_helper():
    """Mock EncryptionHelper for token encryption/decryption."""
    with patch("app.utils.encryption.EncryptionHelper") as mock_helper:
        mock_instance = MagicMock()
        mock_instance.encrypt.return_value = TOKEN_ENCRYPTED_1
        mock_instance.decrypt.return_value = "ghp_1234567890abcdef"
        mock_helper.return_value = mock_instance
        mock_helper.encrypt = mock_instance.encrypt
        mock_helper.decrypt = mock_instance.decrypt
        yield mock_helper


# Event loop fixture for async tests
@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


# Fixture for async test client
@pytest.fixture
async def async_client():
    """
    Create an async test client for testing async endpoints.
    """
    from httpx import AsyncClient

    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac
