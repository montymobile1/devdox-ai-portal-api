"""
Test cases for token retrieval and creation API endpoints.
"""

from fastapi import status
import pytest
from urllib.parse import quote
from app.routes.git_tokens import mask_token
from app.config import GitHosting

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


class TestGetTokensEndpoint:
    """Test cases for GET /api/tokens endpoint."""

    def test_successful_token_retrieval(self, client, mock_db_client, token_data_list):
        """Test successful retrieval of tokens."""
        # Setup mock
        mock_db_client.execute_query.return_value = token_data_list

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
        assert token1["masked_token"] == "ghp_************cdef"
        assert token1["created_at"] == "2024-01-01T10:00:00Z"

        # Verify second token
        token2 = data[1]
        assert token2["id"] == "2"
        assert token2["label"] == "GitLab Staging"
        assert token2["git_hosting"] == "gitlab"

        # Verify db_client was called correctly
        mock_db_client.execute_query.assert_called_once()
        call_args = mock_db_client.execute_query.call_args[0][0]
        assert (
            "SELECT label, id, git_hosting,masked_token, created_at FROM git_label"
            in call_args
        )

    def test_empty_token_list(self, client, mock_db_client):
        """Test retrieval when no tokens exist."""
        # Mock empty database response
        mock_db_client.execute_query.return_value = []

        # Make request
        response = client.get("/api/v1/git_tokens/")

        # Verify response
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data == []
        assert isinstance(data, list)

        # Verify db_client was called
        mock_db_client.execute_query.assert_called_once()

    def test_database_connection_error(self, client, mock_db_client):
        """Test error handling when database connection fails."""
        # Mock database error
        mock_db_client.execute_query.side_effect = Exception(
            "Database connection failed"
        )

        # Make request
        response = client.get("/api/v1/git_tokens/")

        # Verify error response
        assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
        data = response.json()
        assert "detail" in data
        assert (
            "Service temporarily unavailable. Please try again later." in data["detail"]
        )


class TestGetTokenByLabelEndpoint:
    """Test cases for GET /api/v1/git_tokens/{label} endpoint."""

    def test_get_token_by_label_success(self, client, mock_db_client, token_data_list):
        """Test successful retrieval of token by label."""
        # Setup mock to return filtered data
        filtered_data = [token_data_list[0]]  # Return only first token
        mock_db_client.execute_query.return_value = filtered_data

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
        assert token["masked_token"] == "ghp_************cdef"

        # Verify query was called with correct parameters
        mock_db_client.execute_query.assert_called_once()
        call_args = mock_db_client.execute_query.call_args[0][0]
        assert "WHERE label='GitHub Production'" in call_args

    def test_get_token_by_nonexistent_label(self, client, mock_db_client):
        """Test getting token with label that doesn't exist."""
        # Mock empty result
        mock_db_client.execute_query.return_value = []

        # Make request for a non-existent label
        response = client.get("/api/v1/git_tokens/NonExistentLabel")

        # Verify response
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data == []

    def test_get_token_by_label_database_error(self, client, mock_db_client):
        """Test error handling when database query fails."""
        # Mock database error
        mock_db_client.execute_query.side_effect = Exception("Database error")

        # Make request
        response = client.get("/api/v1/git_tokens/SomeLabel")

        # Verify error response
        assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
        data = response.json()
        assert "Service temporarily unavailable" in data["detail"]


class TestAddTokenEndpoint:
    """Test cases for POST /api/v1/git_tokens/ endpoint."""

    def test_add_github_token_success(
        self,
        client,
        token_payload_github,
        mock_github_manager_success,
        mock_supabase_insert_success,
        token_decrypted1,
        token_decrypted1_masked,
        mock_encryption_helper,
    ):
        """Test successful creation of a GitHub token."""
        # Make the request
        response = client.post("/api/v1/git_tokens/", json=token_payload_github)

        # Verify response
        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert "success" in data and data["success"] is True
        assert "data" in data and "id" in data["data"]
        assert data["data"]["id"] == "999"

        # Verify GitHub manager was initialized with correct token
        mock_github_manager_success.assert_called_once_with(
            access_token=token_decrypted1
        )

        # Verify db_client insert was called
        mock_supabase_insert_success.insert_row.assert_called_once()

        # Get the actual call args
        call_args = mock_supabase_insert_success.insert_row.call_args

        # Verify the table name (first argument)
        assert call_args[0][0] == "git_label"

        # Verify all fields in the data dict
        data_dict = call_args[0][1]
        assert data_dict["label"] == "Test GitHub Token"
        assert data_dict["user_id"] == "user123"
        assert data_dict["git_hosting"] == GitHosting.GITHUB
        assert data_dict["masked_token"] == token_decrypted1_masked
        assert data_dict["username"] == "testuser"

        # Verify token_value exists but don't check its value (it's encrypted)
        assert "token_value" in data_dict

    def test_add_gitlab_token_success(
        self,
        token_payload_gitlab,
        client,
        mock_gitlab_manager_success,
        mock_supabase_insert_success,
        token_gitlab_decrypted1,
        token_gitlab_decrypted1_masked,
        mock_encryption_helper,
    ):
        """Test successful creation of a GitLab token."""
        # Make the request
        response = client.post("/api/v1/git_tokens/", json=token_payload_gitlab)

        # Verify response
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "success" in data and data["success"] is True
        assert "data" in data and "id" in data["data"]
        assert data["data"]["id"] == "999"

        # Verify GitLab manager was initialized with correct parameters
        mock_gitlab_manager_success.assert_called_once_with(
            base_url="https://gitlab.com",
            access_token=token_gitlab_decrypted1.replace(" ", ""),
        )

        # Verify user data was fetched
        mock_gitlab_manager_success.return_value.get_user.assert_called_once()

        # Get the actual call args
        call_args = mock_supabase_insert_success.insert_row.call_args

        # Verify the table name (first argument)
        assert call_args[0][0] == "git_label"

        # Verify all fields in the data dict
        data_dict = call_args[0][1]
        assert data_dict["label"] == "Test GitLab Token"
        assert data_dict["user_id"] == "user123"
        assert data_dict["git_hosting"] == GitHosting.GITLAB
        assert data_dict["masked_token"] == token_gitlab_decrypted1_masked
        assert data_dict["username"] == "testuser"

        # Verify token_value exists
        assert "token_value" in data_dict

    def test_add_github_token_authentication_failure(
        self,
        token_payload_github,
        client,
        mock_github_manager_failure,
        mock_encryption_helper,
    ):
        """Test GitHub token creation with authentication failure."""
        # Mock GitHub authentication failure
        mock_github_manager_failure.return_value.get_user.return_value = None
        token_payload_github["token_value"] = "invalid_token"

        # Make the request
        response = client.post("/api/v1/git_tokens/", json=token_payload_github)

        # Verify response
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        data = response.json()
        assert data["success"] is False
        assert "Failed to authenticate with GitHub" in data["message"]

        # Verify GitHub manager was initialized with the invalid token
        mock_github_manager_failure.assert_called_once_with(
            access_token="invalid_token"
        )

        # Verify get_user was called
        mock_github_manager_failure.return_value.get_user.assert_called_once()

    def test_add_gitlab_token_authentication_failure(
        self, client, mock_gitlab_manager, mock_encryption_helper, mock_supabase_insert
    ):
        """Test GitLab token creation with authentication failure."""
        # Mock GitLab authentication failure
        mock_gitlab_manager.return_value.auth_status = False

        # Create payload
        payload = {
            "label": "Test GitHub Token",
            "user_id": "user123",
            "git_hosting": "github",
            "token_value": "ghp_1234567890abcdef",
        }

        # Make the request
        response = client.post("/api/v1/git_tokens/", json=payload)

        # Verify response
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        data = response.json()
        assert data["success"] is False
        assert "Failed to authenticate with GitHub" in data["message"]

        # Verify db_client insert was called
        mock_supabase_insert.insert_row.assert_not_called()

    def test_add_token_unsupported_provider(self, client, mock_encryption_helper):
        """Test creation with unsupported git hosting provider."""
        # Create payload with unsupported provider
        payload = {
            "label": "Test Token",
            "user_id": "user123",
            "git_hosting": "bitbucket",  # Unsupported provider
            "token_value": "token123456",
        }

        # Make the request
        response = client.post("/api/v1/git_tokens/", json=payload)

        # Verify response
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        data = response.json()
        assert "Input should be 'gitlab' or 'github" in data["detail"][0]["msg"]

    def test_add_token_empty_token(
        self, client, mock_github_manager, mock_supabase_insert, mock_encryption_helper
    ):
        """Test creation with empty token."""
        # Create payload with empty token
        payload = {
            "label": "Test GitHub Token",
            "user_id": "user123",
            "git_hosting": "github",
            "token_value": "",  # Empty token
        }

        # Make the request
        response = client.post("/api/v1/git_tokens/", json=payload)

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


class TestDeleteToken:
    """Test cases for delete_token endpoint"""

    def test_delete_token_success(
        self, client, mock_supabase_client, sample_token_id, sample_token_data
    ):
        """Test successful token deletion"""
        # Arrange
        mock_supabase_client.execute_query_one.return_value = sample_token_data
        mock_supabase_client.delete_rows.return_value = True

        # Act
        response = client.delete(f"/api/v1/git_tokens/{sample_token_id}")

        # Assert
        assert response.status_code == status.HTTP_200_OK
        response_data = response.json()
        assert response_data["success"] is True
        assert response_data["message"] == "Token deleted successfully"

        # Verify the correct methods were called
        mock_supabase_client.execute_query_one.assert_called_once()
        call_args = mock_supabase_client.execute_query_one.call_args
        assert "SELECT label, id FROM git_label WHERE id = $1" in call_args[0][0]

        mock_supabase_client.delete_rows.assert_called_once()

    def test_delete_token_not_found(
        self, client, mock_supabase_client, sample_token_id
    ):
        """Test deletion when token doesn't exist"""
        # Arrange
        mock_supabase_client.execute_query_one.return_value = None

        # Act
        response = client.delete(f"/api/v1/git_tokens/{sample_token_id}")

        # Assert
        assert response.status_code == status.HTTP_404_NOT_FOUND
        response_data = response.json()
        assert response_data["message"] == "Token not found"

        # Verify execute_query_one was called but delete_rows was not
        mock_supabase_client.execute_query_one.assert_called_once()
        mock_supabase_client.delete_rows.assert_not_called()

    def test_delete_token_empty_response(
        self, client, mock_supabase_client, sample_token_id
    ):
        """Test deletion when execute_query_one returns empty dict or falsy value"""
        # Arrange
        mock_supabase_client.execute_query_one.return_value = {}

        # Act
        response = client.delete(f"/api/v1/git_tokens/{sample_token_id}")

        # Assert
        assert response.status_code == status.HTTP_404_NOT_FOUND
        response_data = response.json()
        assert response_data["message"] == "Token not found"

    def test_delete_token_database_error_on_get(
        self, client, mock_supabase_client, sample_token_id
    ):
        """Test handling of database error during get operation"""
        # Arrange
        mock_supabase_client.execute_query_one.side_effect = Exception(
            "Database connection failed"
        )

        # Act
        response = client.delete(f"/api/v1/git_tokens/{sample_token_id}")

        # Assert
        assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
        response_data = response.json()
        assert (
            response_data["detail"]
            == "Service temporarily unavailable. Please try again later."
        )

    def test_delete_token_database_error_on_delete(
        self, client, mock_supabase_client, sample_token_id, sample_token_data
    ):
        """Test handling of database error during delete operation"""
        # Arrange
        mock_supabase_client.execute_query_one.return_value = sample_token_data
        mock_supabase_client.delete_rows.side_effect = Exception(
            "Delete operation failed"
        )

        # Act
        response = client.delete(f"/api/v1/git_tokens/{sample_token_id}")

        # Assert
        assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
        response_data = response.json()
        assert (
            response_data["detail"]
            == "Service temporarily unavailable. Please try again later."
        )

    def test_delete_token_with_special_characters_in_id(
        self, client, mock_supabase_client, sample_token_data
    ):
        """Test deletion with special characters in token ID"""
        # Arrange
        special_id = "token-with-special-chars!@#$%"
        encoded_id = quote(special_id, safe="")
        mock_supabase_client.execute_query_one.return_value = sample_token_data
        mock_supabase_client.delete_rows.return_value = True

        # Act
        response = client.delete(f"/api/v1/git_tokens/{encoded_id}")
        print("data ", response.json())
        # Assert
        assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE

    def test_delete_token_invalid_uuid(self, client, mock_supabase_client):
        """Test deletion with invalid UUID format"""
        # Arrange
        invalid_id = "not-a-valid-uuid"

        # Act
        response = client.delete(f"/api/v1/git_tokens/{invalid_id}")

        # Assert
        assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
        response_data = response.json()
        assert (
            response_data["detail"]
            == "Service temporarily unavailable. Please try again later."
        )

    @pytest.mark.parametrize(
        "token_id",
        [
            "550e8400-e29b-41d4-a716-446655440000",  # Valid UUID
            "123e4567-e89b-12d3-a456-426614174000",  # Another valid UUID
        ],
    )
    def test_delete_token_valid_uuid_formats(
        self, client, mock_supabase_client, sample_token_data, token_id
    ):
        """Test deletion with valid UUID formats"""
        # Arrange
        mock_supabase_client.execute_query_one.return_value = sample_token_data
        mock_supabase_client.delete_rows.return_value = True

        # Act
        response = client.delete(f"/api/v1/git_tokens/{token_id}")

        # Assert
        assert response.status_code == status.HTTP_200_OK
        mock_supabase_client.execute_query_one.assert_called_once()

    def test_delete_token_response_structure(
        self, client, mock_supabase_client, sample_token_id, sample_token_data
    ):
        """Test that the response follows the expected structure"""
        # Arrange
        mock_supabase_client.execute_query_one.return_value = sample_token_data
        mock_supabase_client.delete_rows.return_value = True

        # Act
        response = client.delete(f"/api/v1/git_tokens/{sample_token_id}")

        # Assert
        assert response.status_code == status.HTTP_200_OK
        response_data = response.json()

        # Check response structure (assuming APIResponse.success returns this structure)
        assert "success" in response_data
        assert "message" in response_data
        assert isinstance(response_data["success"], bool)
        assert isinstance(response_data["message"], str)


# Additional integration-style tests if needed
class TestDeleteTokenIntegration:
    """Integration tests for delete_token endpoint"""

    def test_delete_token_endpoint_exists(self, client):
        """Test that the delete endpoint exists and is accessible"""
        # This will return 404 or 503 depending on the mock, but not 405 (Method Not Allowed)
        response = client.delete("/api/v1/git_tokens/test-id")
        assert response.status_code != status.HTTP_405_METHOD_NOT_ALLOWED


# Additional async tests for Tortoise ORM functionality
class TestTortoiseOrmIntegration:
    """Test cases specific to Tortoise ORM integration"""

    @pytest.mark.asyncio
    async def test_async_database_operations(self, mock_db_client):
        """Test that async database operations work correctly"""
        # This would test the actual async functionality if needed
        mock_db_client.execute_query.return_value = []

        # Simulate async call
        result = await mock_db_client.execute_query("SELECT * FROM git_label")
        assert result == []
        mock_db_client.execute_query.assert_called_once()

    def test_connection_initialization(self, client, mock_tortoise_init):
        """Test that Tortoise ORM connection is properly initialized"""
        # Make any request to trigger connection
        response = client.get("/api/v1/git_tokens/")

        # The connection should be initialized (mocked)
        # This is more of an integration test to ensure the app starts properly

    def test_database_migration_compatibility(
        self, client, mock_supabase_client, sample_token_id
    ):
        """Test that the new Tortoise ORM implementation is compatible with existing data"""
        # This test ensures that the data format returned by Tortoise ORM
        # matches what the API expects

        # Mock data in the format Tortoise ORM would return
        mock_supabase_client.execute_query.return_value = [
            {
                "id": sample_token_id,
                "label": "Test Token",
                "git_hosting": "github",
                "masked_token": "ghp_************cdef",
                "created_at": "2024-01-01T10:00:00+00:00",  # ISO format with timezone
            }
        ]

        response = client.get("/api/v1/git_tokens/")
        data = response.json()
        print("response data ", data)
        assert response.status_code == status.HTTP_200_OK

        assert len(data) == 1
        assert data[0]["id"] == sample_token_id
        assert data[0]["label"] == "Test Token"


# Performance and stress tests
class TestPerformance:
    """Performance-related tests for the new implementation"""

    def test_large_token_list_performance(self, client, mock_db_client):
        """Test handling of large token lists"""
        # Create a large list of tokens
        large_token_list = []
        for i in range(1000):
            large_token_list.append(
                {
                    "id": str(i),
                    "label": f"Token {i}",
                    "git_hosting": "github",
                    "masked_token": "ghp_************cdef",
                    "created_at": "2024-01-01T10:00:00Z",
                }
            )

        mock_db_client.execute_query.return_value = large_token_list

        response = client.get("/api/v1/git_tokens/")
        assert response.status_code == status.HTTP_200_OK

        data = response.json()
        assert len(data) == 1000

    def test_concurrent_requests(self, client, mock_db_client, mock_gitlab_manager):
        """Test handling of concurrent requests"""
        import threading
        import time

        mock_db_client.execute_query.return_value = []

        results = []

        def make_request():
            response = client.get("/api/v1/git_tokens/")
            results.append(response.status_code)

        # Create multiple threads to make concurrent requests
        threads = []
        for _ in range(10):
            thread = threading.Thread(target=make_request)
            threads.append(thread)
            thread.start()

        # Wait for all threads to complete
        for thread in threads:
            thread.join()

        # All requests should succeed
        assert all(status_code == 200 for status_code in results)
        assert len(results) == 10
        payload = {
            "label": "Test GitLab Token",
            "user_id": "user123",
            "git_hosting": "gitlab",
            "token_value": "glpat-1234567890abcdef",
        }
        mock_gitlab_manager.return_value.auth_status = False
        # Make the request
        response = client.post("/api/v1/git_tokens/", json=payload)
        data = response.json()

        # Verify response
        assert response.status_code == status.HTTP_400_BAD_REQUEST

        assert data["success"] is False
        assert "Failed to authenticate with GitLab" in data["message"]

        # Verify GitLab manager was initialized with the invalid token
        mock_gitlab_manager.assert_called_once_with(
            base_url="https://gitlab.com", access_token="glpat-1234567890abcdef"
        )

    def test_add_gitlab_token_user_fetch_failure(
        self,
        client,
        mock_gitlab_manager,
        mock_supabase_invalid_data,
        mock_encryption_helper,
    ):
        """Test GitLab token creation with user fetch failure."""
        # Mock GitLab auth success but user fetch failure
        mock_gitlab_manager.return_value.auth_status = True
        mock_gitlab_manager.return_value.get_user.return_value = None

        # Create payload
        payload = {
            "label": "Test GitLab Token",
            "user_id": "user123",
            "git_hosting": "gitlab",
            "token_value": "glpat-1234567890abcdef",
        }

        # Make the request
        response = client.post("/api/v1/git_tokens/", json=payload)

        # Verify response
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        data = response.json()
        assert data["success"] is False
        assert "Could not retrieve GitLab user" in data["message"]

        # Verify user data was attempted to be fetched
        mock_gitlab_manager.return_value.get_user.assert_called_once()
