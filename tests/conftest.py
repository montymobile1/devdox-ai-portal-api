"""
Pytest fixtures for token API endpoint tests.
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch, MagicMock


from app.main import app  # Assuming your FastAPI app is in app.main

# Sample encrypted token values for testing
#TOKEN_ENCRYPTED_1 = "gAAAAABoLCptgspZg0h7yQRjfAJhWWKHLsKl5IL8qKnP4mH4TDq-6TlZI_94TMWCftEUU65eYAlz0e0_gQI4pKwOIEoqHEqtxOuzHEIvwTJRtaVi1nQZm4Y="
TOKEN_ENCRYPTED_1 = "gAAAAABoMFiNIvAc7WIFnoKXBjkpAVrdiTFrhlmZtG8BBwvmy1dtvfEFmupm0fcvDUo3unosoAQz5eclP2QFMnPMLG4Hj21MBt-xTdWL661JnWP-wQarnLI="
TOKEN_ENCRYPTED_2 = "gAAAAABoMFiNIvAc7WIFnoKXBjkpAVrdiTFrhlmZtG8BBwvmy1dtvfEFmupm0fcvDUo3unosoAQz5eclP2QFMnPMLG4Hj21MBt-xTdWL661JnWP-wQarnLI="
decrypted1_masked=decrypted2_masked="ghp_************cdef"



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
def mock_supabase():
    """
    Create a mocked Supabase client.
    """
    with patch('app.routes.git_tokens.SupabaseClient') as mock:
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
        "created_at": "2024-01-01T10:00:00Z",
        "updated_at": "2024-01-02T10:00:00Z"
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
            "updated_at": "2024-01-02T10:00:00Z"
        },
        {
            "id": "2",
            "label": "GitLab Staging",
            "git_hosting": "gitlab",
            "token_value": TOKEN_ENCRYPTED_2,
            "masked_token":decrypted2_masked,
            "created_at": "2024-01-03T10:00:00Z",
            "updated_at": "2024-01-04T10:00:00Z"
        }
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

            "created_at": "2024-01-01T10:00:00Z"

        },

        {

            # Missing id field

            "label": "Missing ID",

            "git_hosting": "gitlab",

            "token_value": TOKEN_ENCRYPTED_2,

            "created_at": "2024-01-03T10:00:00Z"

        },

        {

            "id": "5",

            "label": "Empty Token Value",

            "git_hosting": "github",

            "token_value": "",  # Empty token

            "created_at": "2024-01-05T10:00:00Z"

        }

    ]



@pytest.fixture
def mock_supabase_select(mock_supabase, token_data_list):
    """
    Setup the mock Supabase client to return token data list.
    """
    mock_instance = mock_supabase.return_value
    mock_instance.select.return_value = token_data_list
    return mock_instance


@pytest.fixture
def mock_supabase_filter(mock_supabase, token_data_list):
    """

    Setup the mock Supabase client to return filtered token data using filter method.

    """

    mock_instance = mock_supabase.return_value

    # Configure filter method to return specific results based on filters

    def side_effect_filter(table, filters=None, columns=None, limit=None):

        if not filters:
            return token_data_list

        # Filter by label

        if 'label' in filters:
            label = filters['label']

            return [token for token in token_data_list if token.get('label') == label]

        return []

    mock_instance.filter.side_effect = side_effect_filter

    return mock_instance


@pytest.fixture
def mock_supabase_empty(mock_supabase):
    """

    Setup the mock Supabase client to return empty results.

    """

    mock_instance = mock_supabase.return_value

    mock_instance.select.return_value = []

    mock_instance.filter.return_value = []

    return mock_instance


@pytest.fixture
def mock_supabase_invalid_data(mock_supabase, invalid_token_data_list):
    """

    Setup the mock Supabase client to return invalid token data.

    """

    mock_instance = mock_supabase.return_value

    mock_instance.filter.return_value = invalid_token_data_list

    def side_effect_filter(table, filters=None, columns=None, limit=None):
        if filters and 'label' in filters:
            # Return the first invalid token data

            return [invalid_token_data_list[0]]

        return invalid_token_data_list

    mock_instance.filter.side_effect = side_effect_filter

    return mock_instance


@pytest.fixture()
def mock_supabase_invalid_label(mock_supabase):
    mock_supabase.filter.return_value = []
    return mock_supabase

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
    with patch("app.routes.git_tokens.SupabaseClient") as mock:
        mock_instance = MagicMock()
        mock_instance.insert.return_value = {"id": "999"}
        mock.return_value = mock_instance
        yield mock_instance

@pytest.fixture
def mock_supabase_insert_success():
    """Mock for successful SupabaseClient insert operation."""
    with patch("app.routes.git_tokens.SupabaseClient") as mock_class:
        mock_instance = MagicMock()
        mock_instance.insert.return_value = {"id": "999"}
        mock_class.return_value = mock_instance
        yield mock_instance

@pytest.fixture
def sample_token_id():
    """Simple sample token ID for testing"""
    return "test-token-id-123"

@pytest.fixture
def sample_token_data():
    """Basic sample token data"""
    return {
        "id": "test-token-id-123",
        "label": "test-token-label",
        "value": "masked-token-value",
        "created_at": "2024-01-01T00:00:00Z",
        "updated_at": "2024-01-01T00:00:00Z"
    }


@pytest.fixture
def token_payload_github():
    """Sample GitHub token payload."""
    return {
        "label": "Test GitHub Token",
        "user_id": "user123",
        "git_hosting": "github",
        "token_value": "ghp_1234567890abcdef"
    }

@pytest.fixture
def token_payload_gitlab():
    """Sample GitLab token payload."""
    return {
        "label": "Test GitLab Token",
        "user_id": "user123",
        "git_hosting": "gitlab",
        "token_value": "glpat-1234567890abcdef"
    }


@pytest.fixture
def mock_api_response():
    """Mock for APIResponse utility class."""
    with patch("app.routes.git_tokens.APIResponse") as mock:
        # Set up success method
        mock.success = MagicMock(return_value={
            "success": True,
            "message": "Operation successful",
            "data": {}
        })

        # Set up error method
        mock.error = MagicMock(return_value={
            "success": False,
            "message": "Operation failed",
            "data": None
        })

        yield mock


@pytest.fixture
def mock_supabase_client():
    """
    Basic mock SupabaseClient fixture that returns a mocked client instance.
    Use this for simple test cases where you just need to mock return values.
    """
    with patch('app.routes.git_tokens.SupabaseClient') as mock_client_class:  # Adjust import path
        mock_client = Mock()
        mock_client_class.return_value = mock_client

        # Set default return values
        mock_client.get_by_id.return_value = None
        mock_client.delete.return_value = True
        mock_client.create.return_value = {"id": "new-id", "created": True}
        mock_client.update.return_value = {"id": "updated-id", "updated": True}
        mock_client.get_all.return_value = []

        yield mock_client

