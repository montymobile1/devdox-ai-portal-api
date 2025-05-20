"""
Pytest fixtures for token API endpoint tests.
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import MagicMock, patch

from app.main import app  # Assuming your FastAPI app is in app.main

# Sample encrypted token values for testing
TOKEN_ENCRYPTED_1 = "gAAAAABoLCptgspZg0h7yQRjfAJhWWKHLsKl5IL8qKnP4mH4TDq-6TlZI_94TMWCftEUU65eYAlz0e0_gQI4pKwOIEoqHEqtxOuzHEIvwTJRtaVi1nQZm4Y="
TOKEN_ENCRYPTED_2 = "gAAAAABoLCptgspZg0h7yQRjfAJhWWKHLsKl5IL8qKnP4mH4TDq-6TlZI_94TMWCftEUU65eYAlz0e0_gQI4pKwOIEoqHEqtxOuzHEIvwTJRtaVi1nQZm4Y="

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
def mock_encryption_helper():
    """
    Create a mocked EncryptionHelper.
    """
    with patch('app.routes.git_tokens.EncryptionHelper') as mock:
        # Configure decrypt method to return predictable values for tests
        mock.decrypt.side_effect = lambda token: "ghp_1234567890abcdef" if token else ""
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
