"""
Test cases for token retrieval and creation API endpoints.
"""

from fastapi import status
from app.routes.git_tokens import mask_token, format_token_response

class TestTokenMasking:
    """Test cases for token masking functionality."""

    def test_mask_token_normal_length(self):
        """Test masking for normal length token."""
        token = "ghp_1234567890abcdef"
        result = mask_token(token)
        assert result == "ghp_************cdef"
        assert len(result) == len(token)

    def test_mask_token_short_token(self):
        """Test masking for short token (8 chars or less)."""
        token = "short123"
        result = mask_token(token)
        assert result == "********"
        assert len(result) == len(token)

    def test_mask_token_empty_string(self):
        """Test masking for empty token."""
        token = ""
        result = mask_token(token)
        assert result == ""

    def test_mask_token_none(self):
        """Test masking for None token."""
        token = None
        result = mask_token(token)
        assert result == ""

    def test_mask_token_exact_eight_chars(self):
        """Test masking for a token of exactly 8 characters."""

        token = "12345678"

        result = mask_token(token)

        assert result == "********"

        assert len(result) == 8

    def test_mask_token_nine_chars(self):
        """Test masking for a token of exactly 9 characters."""

        token = "123456789"

        result = mask_token(token)

        assert result == "1234*6789"

        assert len(result) == 9


class TestTokenFormatting:
    """Test cases for token response formatting."""

    def test_format_token_response_complete(self, token_data_single, mock_encryption_helper):
        """Test formatting with all fields present."""
        result = format_token_response(token_data_single)

        assert result["id"] == "123"
        assert result["label"] == "Production GitHub"
        assert result["git_hosting"] == "github"
        assert result["token_value"] == "ghp_************cdef"
        assert result["created_at"] == "2024-01-01T10:00:00Z"
        assert result["updated_at"] == "2024-01-02T10:00:00Z"

    def test_format_token_response_missing_fields(self):
        """Test formatting with missing fields."""
        token_data = {
            "id": "123",
            "label": "Test Token"
            # Missing token_value field
        }

        result = format_token_response(token_data)
        assert result is None

    def test_format_token_response_empty_token(self, mock_encryption_helper):
            """Test formatting with empty token value."""

            token_data = {

                "id": "123",

                "label": "Test Token",

                "git_hosting": "github",

                "token_value": "",  # Empty token

                "created_at": "2024-01-01T10:00:00Z"

            }

            result = format_token_response(token_data)

            assert result is  None



    def test_format_token_response_none_input(self):
            """Test formatting with None input."""

            result = format_token_response(None)

            assert result is None


class TestGetTokensEndpoint:
    """Test cases for GET /api/tokens endpoint."""

    def test_successful_token_retrieval(self, client, mock_supabase_select, mock_encryption_helper):
        """Test successful retrieval of tokens."""
        # Make the request
        response = client.get("/api/v1/git_tokens/")

        # Verify response
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data) == 2

        # Verify first token
        token1 = data[0]
        assert token1["id"] == "1"
        assert token1["label"] == "GitHub Production"
        assert token1["git_hosting"] == "github"
        assert token1["token_value"] == "ghp_************cdef"
        assert token1["created_at"] == "2024-01-01T10:00:00Z"

        # Verify second token
        token2 = data[1]
        assert token2["id"] == "2"
        assert token2["label"] == "GitLab Staging"
        assert token2["git_hosting"] == "gitlab"
        assert token2["token_value"] == "ghp_************cdef"

        # Verify supabase was called correctly
        mock_supabase_select.select.assert_called_once_with(
            table="git_label",
            columns="label, id, git_hosting,token_value, created_at"
        )

    def test_invalid_token_data(self, client, mock_supabase_invalid_data, mock_encryption_helper):
        """Test handling of invalid token data."""

        # Make request

        response = client.get("/api/v1/git_tokens/")

        # Verify response

        assert response.status_code == status.HTTP_200_OK

        data = response.json()

        # Since format_token_response returns None for invalid data, we should get an empty list

        assert isinstance(data, list)

        assert len(data) == 0

    def test_empty_token_list(self, client, mock_supabase):
        """Test retrieval when no tokens exist."""
        # Mock empty database response
        mock_instance = mock_supabase.return_value
        mock_instance.select.return_value = []

        # Make request
        response = client.get("/api/v1/git_tokens/")

        # Verify response
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data == []
        assert isinstance(data, list)

        # Verify supabase was called
        mock_instance.select.assert_called_once()

    def test_database_connection_error(self, client, mock_supabase):
        """Test error handling when database connection fails."""
        # Mock database error
        mock_instance = mock_supabase.return_value
        mock_instance.select.side_effect = Exception("Database connection failed")

        # Make request
        response = client.get("/api/v1/git_tokens/")

        # Verify error response
        assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
        data = response.json()
        assert "detail" in data
        assert "Service temporarily unavailable. Please try again later." in data["detail"]

    def test_database_timeout_error(self, client, mock_supabase):
        """Test error handling for database timeout."""
        # Mock timeout error
        mock_instance = mock_supabase.return_value
        mock_instance.select.side_effect = TimeoutError("Database timeout")

        # Make request
        response = client.get("/api/v1/git_tokens/")

        # Verify error response
        assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
        data = response.json()
        assert "Service temporarily unavailable. Please try again later" in data["detail"]


class TestGetTokenByLabelEndpoint:
    """Test cases for GET /api/v1/git_tokens/{label} endpoint."""

    def test_get_token_by_label_success(self, client, mock_supabase_filter, mock_encryption_helper):
        """Test successful retrieval of token by label."""

        # Make the request for a known label

        response = client.get("/api/v1/git_tokens/GitHub%20Production")

        # Verify response

        assert response.status_code == status.HTTP_200_OK

        data = response.json()

        assert len(data) == 1

        token = data[0]

        assert token["id"] == "1"

        assert token["label"] == "GitHub Production"

        assert token["git_hosting"] == "github"

        assert token["token_value"] == "ghp_************cdef"

        # Verify filter was called with correct parameters

        mock_supabase_filter.filter.assert_called_once_with(

            table="git_label",

            filters={"label": "GitHub Production"},

            limit=1

        )

    def test_get_token_by_nonexistent_label(self, client, mock_supabase_empty):
        """Test getting token with label that doesn't exist."""

        # Make request for a non-existent label

        response = client.get("/api/v1/git_tokens/NonExistentLabel")

        # Verify response

        assert response.status_code == status.HTTP_200_OK

        data = response.json()

        assert data == []

    def test_get_token_by_label_database_error(self, client, mock_supabase):
        """Test error handling when database query fails."""

        # Mock database error

        mock_instance = mock_supabase.return_value

        mock_instance.filter.side_effect = Exception("Database error")

        # Make request

        response = client.get("/api/v1/git_tokens/SomeLabel")

        # Verify error response

        assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE

        data = response.json()

        assert "Service temporarily unavailable" in data["detail"]

    def test_get_token_by_label_invalid_data(self, client, mock_supabase_invalid_data, mock_encryption_helper):
        """Test handling of invalid token data when filtering by label."""

        # Make request for a label that returns invalid data

        response = client.get("/api/v1/git_tokens/Missing%20Token%20Value")

        # Verify response

        assert response.status_code == status.HTTP_200_OK

        data = response.json()

        # Since format_token_response returns None for invalid data, we should get an empty list

        assert isinstance(data, list)

        assert len(data) == 0