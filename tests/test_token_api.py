"""
Test cases for token retrieval and creation API endpoints.
"""

import pytest
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
        assert not result


class TestGetTokensEndpoint:
    """Test cases for GET /api/tokens endpoint."""

    def test_successful_token_retrieval(self, client, mock_supabase_select, mock_encryption_helper):
        """Test successful retrieval of tokens."""
        # Make the request
        response = client.get("/api/v1/git_tokens/")

        # Verify response
        print("mock_supabase_select.filter.return_value ", mock_supabase_select.select.return_value)
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        print("data ", data)
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
        print("response.status_code  ", response.status_code )
        print("data ", response.json())

        # Verify error response
        assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
        data = response.json()
        assert "Service temporarily unavailable. Please try again later" in data["detail"]

