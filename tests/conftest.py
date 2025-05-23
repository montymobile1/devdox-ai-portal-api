"""
Pytest fixtures for token API endpoint tests.
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch, MagicMock


from app.main import app  # Assuming your FastAPI app is in app.main

# Sample encrypted token values for testing
#TOKEN_ENCRYPTED_1 = "gAAAAABoLCptgspZg0h7yQRjfAJhWWKHLsKl5IL8qKnP4mH4TDq-6TlZI_94TMWCftEUU65eYAlz0e0_gQI4pKwOIEoqHEqtxOuzHEIvwTJRtaVi1nQZm4Y="
TOKEN_ENCRYPTED_1 = "gAAAAABoLY1xN44144aj4hoqxlP1A385SKuWONI-ydywxS2M8UHpxMu71CHXhu3rDruewrLeAV-jMiQAp0F8i5a5f9yv06QScbeV0yqI_rFN6B3HYsIZnMs="
TOKEN_ENCRYPTED_2 = "gAAAAABoLY1VLHmjiBQ1QMt1nG9PcKxdGHjDK1QzsZHwo7-7WZv8uFfTbZikYZcizmkHWl9SwEcuSYXVogoCABLXfrIvmD3u3hnUxVqw9fo6eZeB8TrJDNE="



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
            "created_at": "2024-01-01T10:00:00Z",
            "updated_at": "2024-01-02T10:00:00Z"
        },
        {
            "id": "2",
            "label": "GitLab Staging",
            "git_hosting": "gitlab",
            "token_value": TOKEN_ENCRYPTED_2,
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


@pytest.fixture
def mock_supabase_client_with_data():
    """
    Mock SupabaseClient fixture pre-configured with sample data.
    Useful for tests that need existing data scenarios.
    """
    with patch('your_app.SupabaseClient') as mock_client_class:
        mock_client = Mock()
        mock_client_class.return_value = mock_client

        # Sample data
        sample_token = {
            "id": "test-token-123",
            "label": "test-label",
            "value": "masked-value",
            "created_at": "2024-01-01T00:00:00Z",
            "updated_at": "2024-01-01T00:00:00Z"
        }

        # Configure default behaviors
        mock_client.get_by_id.return_value = sample_token
        mock_client.delete.return_value = True
        mock_client.create.return_value = sample_token
        mock_client.update.return_value = sample_token
        mock_client.get_all.return_value = [sample_token]

        yield mock_client


@pytest.fixture
def mock_supabase_client_factory():
    """
    Factory fixture that allows you to create customized mock clients.
    Use this when you need different configurations for different tests.
    """

    def _create_mock_client(
            get_by_id_return=None,
            delete_return=True,
            create_return=None,
            update_return=None,
            get_all_return=None,
            should_raise_exception=False,
            exception_message="Database error"
    ):
        with patch('your_app.SupabaseClient') as mock_client_class:
            mock_client = Mock()
            mock_client_class.return_value = mock_client

            if should_raise_exception:
                mock_client.get_by_id.side_effect = Exception(exception_message)
                mock_client.delete.side_effect = Exception(exception_message)
                mock_client.create.side_effect = Exception(exception_message)
                mock_client.update.side_effect = Exception(exception_message)
                mock_client.get_all.side_effect = Exception(exception_message)
            else:
                mock_client.get_by_id.return_value = get_by_id_return
                mock_client.delete.return_value = delete_return
                mock_client.create.return_value = create_return
                mock_client.update.return_value = update_return
                mock_client.get_all.return_value = get_all_return or []

            return mock_client

    return _create_mock_client


@pytest.fixture
def mock_supabase_client_error():
    """
    Mock SupabaseClient fixture that raises exceptions.
    Use this for testing error handling scenarios.
    """
    with patch('your_app.SupabaseClient') as mock_client_class:
        mock_client = Mock()
        mock_client_class.return_value = mock_client

        # Configure all methods to raise exceptions
        error_message = "Database connection failed"
        mock_client.get_by_id.side_effect = Exception(error_message)
        mock_client.delete.side_effect = Exception(error_message)
        mock_client.create.side_effect = Exception(error_message)
        mock_client.update.side_effect = Exception(error_message)
        mock_client.get_all.side_effect = Exception(error_message)

        yield mock_client


@pytest.fixture
def mock_supabase_client_initialization_error():
    """
    Mock SupabaseClient fixture that fails during initialization.
    Use this for testing client initialization error scenarios.
    """
    with patch('your_app.SupabaseClient') as mock_client_class:
        mock_client_class.side_effect = Exception("Failed to initialize SupabaseClient")
        yield mock_client_class


@pytest.fixture
def mock_supabase_client_advanced():
    """
    Advanced mock SupabaseClient fixture with configurable behaviors.
    Allows you to set up complex scenarios with method call tracking.
    """
    with patch('your_app.SupabaseClient') as mock_client_class:
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client

        # Track method calls
        mock_client.method_calls = []

        # Default configurations
        mock_client.get_by_id.return_value = None
        mock_client.delete.return_value = True
        mock_client.create.return_value = {"success": True}
        mock_client.update.return_value = {"success": True}
        mock_client.get_all.return_value = []

        # Add method to configure specific behaviors
        def configure_method(method_name: str, return_value=None, side_effect=None):
            method = getattr(mock_client, method_name)
            if side_effect:
                method.side_effect = side_effect
            else:
                method.return_value = return_value

        mock_client.configure_method = configure_method

        yield mock_client


# Example usage fixtures for specific scenarios
@pytest.fixture
def mock_supabase_token_exists():
    """Mock client where token exists"""
    with patch('your_app.SupabaseClient') as mock_client_class:
        mock_client = Mock()
        mock_client_class.return_value = mock_client

        existing_token = {
            "id": "existing-token-123",
            "label": "existing-label",
            "value": "existing-masked-value"
        }

        mock_client.get_by_id.return_value = existing_token
        mock_client.delete.return_value = True

        yield mock_client


@pytest.fixture
def mock_supabase_token_not_found():
    """Mock client where token doesn't exist"""
    with patch('your_app.SupabaseClient') as mock_client_class:
        mock_client = Mock()
        mock_client_class.return_value = mock_client

        mock_client.get_by_id.return_value = None
        mock_client.delete.return_value = False

        yield mock_client


@pytest.fixture
def mock_supabase_delete_fails():
    """Mock client where delete operation fails"""
    with patch('your_app.SupabaseClient') as mock_client_class:
        mock_client = Mock()
        mock_client_class.return_value = mock_client

        token_data = {"id": "test-id", "label": "test-label"}
        mock_client.get_by_id.return_value = token_data
        mock_client.delete.side_effect = Exception("Delete operation failed")

        yield mock_client


# Parametrized fixture for multiple scenarios
@pytest.fixture(params=[
    {"get_return": {"id": "1", "label": "test"}, "delete_return": True, "expected_status": 200},
    {"get_return": None, "delete_return": False, "expected_status": 404},
    {"get_return": {}, "delete_return": False, "expected_status": 404},
])
def mock_supabase_scenarios(request):
    """
    Parametrized fixture that provides different scenarios for testing.
    Use this with pytest.mark.parametrize or for comprehensive testing.
    """
    with patch('your_app.SupabaseClient') as mock_client_class:
        mock_client = Mock()
        mock_client_class.return_value = mock_client

        params = request.param
        mock_client.get_by_id.return_value = params["get_return"]
        mock_client.delete.return_value = params["delete_return"]

        # Add scenario info to the mock for test assertions
        mock_client.scenario = params

        yield mock_client


# Context manager fixture for more control
@pytest.fixture
def supabase_client_context():
    """
    Context manager fixture that gives you full control over the mock lifecycle.
    """

    class SupabaseClientContext:
        def __init__(self):
            self.mock_client = None
            self.mock_class = None

        def __enter__(self):
            self.patcher = patch('your_app.SupabaseClient')
            self.mock_class = self.patcher.__enter__()
            self.mock_client = Mock()
            self.mock_class.return_value = self.mock_client
            return self.mock_client

        def __exit__(self, exc_type, exc_val, exc_tb):
            self.patcher.__exit__(exc_type, exc_val, exc_tb)

    return SupabaseClientContext
