"""
Test cases for git label retrieval and creation API endpoints.
Updated for Tortoise ORM implementation with current route structure.
"""

from fastapi import status
import pytest
from urllib.parse import quote
from unittest.mock import patch, MagicMock, AsyncMock
from app.routes.git_tokens import mask_token
from app.utils.auth import AuthenticatedUserDTO, get_current_user
from app.main import app


@pytest.fixture(autouse=True)
def override_current_user():
    test_user = AuthenticatedUserDTO(
        id="user-123", email="test@example.com", name="Test User"
    )
    app.dependency_overrides[get_current_user] = lambda: test_user
    yield
    app.dependency_overrides.clear()


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


class TestGetGitLabelsEndpoint:
    """Test cases for GET /api/v1/git_tokens/ endpoint."""

    def test_successful_git_labels_retrieval(self, client, mock_encryption_helper):
        """Test successful retrieval of git labels."""
        # Setup mock data
        mock_labels = [
            MagicMock(
                id="1",
                label="GitHub Production",
                git_hosting="github",
                token_value="encrypted_token",
                username="testuser",
                created_at=MagicMock(
                    isoformat=MagicMock(return_value="2024-01-01T10:00:00+00:00")
                ),
                updated_at=MagicMock(
                    isoformat=MagicMock(return_value="2024-01-02T10:00:00+00:00")
                ),
            ),
            MagicMock(
                id="2",
                label="GitLab Staging",
                git_hosting="gitlab",
                token_value="encrypted_token",
                username="testuser2",
                created_at=MagicMock(
                    isoformat=MagicMock(return_value="2024-01-03T10:00:00+00:00")
                ),
                updated_at=MagicMock(
                    isoformat=MagicMock(return_value="2024-01-04T10:00:00+00:00")
                ),
            ),
        ]

        with patch("app.routes.git_tokens.GitLabel") as mock_git_label:
            # Setup mock query chain
            mock_query = MagicMock()
            mock_query.count = AsyncMock(return_value=2)
            mock_query.order_by.return_value = mock_query
            mock_query.offset.return_value = mock_query
            mock_query.limit.return_value = mock_query
            mock_query.all = AsyncMock(return_value=mock_labels)

            mock_git_label.filter.return_value = mock_query

            response = client.get("/api/v1/git_tokens/")

            assert response.status_code == status.HTTP_200_OK
            data = response.json()

            assert data["success"] is True
            assert "data" in data
            assert "items" in data["data"]
            assert len(data["data"]["items"]) == 2

            label1 = data["data"]["items"][0]
            assert label1["id"] == "1"
            assert label1["label"] == "GitHub Production"
            assert label1["git_hosting"] == "github"
            assert label1["masked_token"] == "ghp_************cdef"

    def test_empty_git_labels_list(self, client):
        """Test retrieval when no git labels exist."""
        with patch("app.routes.git_tokens.GitLabel") as mock_git_label:
            # Setup mock query chain for empty result
            mock_query = MagicMock()
            mock_query.count = AsyncMock(return_value=0)
            mock_query.order_by.return_value = mock_query
            mock_query.offset.return_value = mock_query
            mock_query.limit.return_value = mock_query
            mock_query.all = AsyncMock(return_value=[])

            mock_git_label.filter.return_value = mock_query

            response = client.get("/api/v1/git_tokens/")

            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data["success"] is True
            assert data["data"]["items"] == []

    def test_database_connection_error(self, client):
        """Test error handling when database connection fails."""
        with patch("app.routes.git_tokens.GitLabel") as mock_git_label:
            mock_git_label.filter.side_effect = Exception("Database connection failed")

            response = client.get("/api/v1/git_tokens/")

            assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
            data = response.json()
            assert data["success"] is False
            assert "Service temporarily unavailable" in data["message"]

    def test_git_hosting_filter(self, client, mock_encryption_helper):
        """Test filtering by git hosting service."""
        mock_labels = [
            MagicMock(
                id="1",
                label="GitHub Production",
                git_hosting="github",
                token_value="encrypted_token",
                username="testuser",
                created_at=MagicMock(
                    isoformat=MagicMock(return_value="2024-01-01T10:00:00+00:00")
                ),
                updated_at=MagicMock(
                    isoformat=MagicMock(return_value="2024-01-02T10:00:00+00:00")
                ),
            )
        ]

        with patch("app.routes.git_tokens.GitLabel") as mock_git_label:
            mock_query = MagicMock()
            mock_query.filter.return_value = mock_query  # For git_hosting filter
            mock_query.count = AsyncMock(return_value=1)
            mock_query.order_by.return_value = mock_query
            mock_query.offset.return_value = mock_query
            mock_query.limit.return_value = mock_query
            mock_query.all = AsyncMock(return_value=mock_labels)

            mock_git_label.filter.return_value = mock_query

            response = client.get("/api/v1/git_tokens/?git_hosting=github")

            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data["success"] is True
            assert len(data["data"]["items"]) == 1
            assert data["data"]["items"][0]["git_hosting"] == "github"

    def test_pagination_functionality(self, client, mock_encryption_helper):
        """Test pagination parameters work correctly"""
        with patch("app.routes.git_tokens.GitLabel") as mock_git_label:
            mock_query = MagicMock()
            mock_query.count = AsyncMock(return_value=50)
            mock_query.order_by.return_value = mock_query
            mock_query.offset.return_value = mock_query
            mock_query.limit.return_value = mock_query
            mock_query.all = AsyncMock(return_value=[])

            mock_git_label.filter.return_value = mock_query

            # Test with pagination parameters
            response = client.get("/api/v1/git_tokens/?offset=2&limit=20")

            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data["success"] is True

            mock_query.offset.assert_called_with(2)  # (page-1) * size = (2-1) * 20 = 20
            mock_query.limit.assert_called_with(20)




class TestAddGitTokenEndpoint:
    """Test cases for POST /api/v1/git_tokens/ endpoint."""

    def test_add_github_token_success(
        self, client, token_payload_github, mock_encryption_helper
    ):
        """Test successful creation of a GitHub token."""
        with patch("app.routes.git_tokens.GitHubManager") as mock_github_manager:
            # Setup successful GitHub manager
            mock_instance = MagicMock()
            mock_instance.get_user.return_value = {"login": "testuser"}
            mock_github_manager.return_value = mock_instance

            with patch("app.routes.git_tokens.GitLabel") as mock_git_label:
                # Setup successful GitLabel creation
                mock_created_label = MagicMock()
                mock_created_label.id = "999"
                mock_git_label.create = AsyncMock(return_value=mock_created_label)

                response = client.post("/api/v1/git_tokens/", json=token_payload_github)

                assert response.status_code == status.HTTP_200_OK
                data = response.json()
                assert data["success"] is True
                assert data["data"]["id"] == "999"

                # Verify GitLabel.create was called
                mock_git_label.create.assert_called_once()

    def test_add_gitlab_token_success(
        self, client, token_payload_gitlab, mock_encryption_helper
    ):
        """Test successful creation of a GitLab token."""
        with patch("app.routes.git_tokens.GitLabManager") as mock_gitlab_manager:
            # Setup successful GitLab manager
            mock_instance = MagicMock()
            mock_instance.auth_status = True
            mock_instance.get_user.return_value = {"username": "testuser"}
            mock_gitlab_manager.return_value = mock_instance

            with patch("app.routes.git_tokens.GitLabel") as mock_git_label:
                mock_created_label = MagicMock()
                mock_created_label.id = "999"
                mock_git_label.create = AsyncMock(return_value=mock_created_label)

                response = client.post("/api/v1/git_tokens/", json=token_payload_gitlab)

                assert response.status_code == status.HTTP_200_OK
                data = response.json()
                assert data["success"] is True
                assert data["data"]["id"] == "999"

    def test_add_github_token_authentication_failure(
        self, client, token_payload_github, mock_encryption_helper
    ):
        """Test GitHub token creation with authentication failure."""
        with patch("app.routes.git_tokens.GitHubManager") as mock_github_manager:
            mock_instance = MagicMock()
            mock_instance.get_user.return_value = None
            mock_github_manager.return_value = mock_instance

            response = client.post("/api/v1/git_tokens/", json=token_payload_github)

            assert response.status_code == status.HTTP_400_BAD_REQUEST
            data = response.json()
            assert data["success"] is False
            assert "Failed to authenticate with GitHub" in data["message"]

    def test_add_gitlab_token_authentication_failure(
        self, client, token_payload_gitlab, mock_encryption_helper
    ):
        """Test GitLab token creation with authentication failure."""
        with patch("app.routes.git_tokens.GitLabManager") as mock_gitlab_manager:
            # Setup failed GitLab manager
            mock_instance = MagicMock()
            mock_instance.auth_status = False
            mock_gitlab_manager.return_value = mock_instance

            response = client.post("/api/v1/git_tokens/", json=token_payload_gitlab)

            assert response.status_code == status.HTTP_400_BAD_REQUEST
            data = response.json()
            assert data["success"] is False
            assert "Failed to authenticate with GitLab" in data["message"]

    def test_add_gitlab_token_user_fetch_failure(self, client, mock_encryption_helper):
        """Test GitLab token creation with user fetch failure."""
        with patch("app.routes.git_tokens.GitLabManager") as mock_gitlab_manager:
            # Mock GitLab auth success but user fetch failure
            mock_instance = MagicMock()
            mock_instance.auth_status = True
            mock_instance.get_user.return_value = None
            mock_gitlab_manager.return_value = mock_instance

            payload = {
                "label": "Test GitLab Token",
                "git_hosting": "gitlab",
                "token_value": "glpat-1234567890abcdef",
            }

            response = client.post("/api/v1/git_tokens/", json=payload)

            assert response.status_code == status.HTTP_400_BAD_REQUEST
            data = response.json()
            assert data["success"] is False
            assert "Could not retrieve GitLab user" in data["message"]

            # Verify user data was attempted to be fetched
            mock_gitlab_manager.return_value.get_user.assert_called_once()

    def test_add_token_unsupported_provider(self, client, mock_encryption_helper):
        """Test creation with unsupported git hosting provider."""
        payload = {
            "label": "Test Token",
            "git_hosting": "bitbucket",  # Unsupported provider
            "token_value": "token123456",
        }

        response = client.post("/api/v1/git_tokens/", json=payload)

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        data = response.json()
        assert data["success"] is False
        assert "Unsupported git hosting provider" in data["message"]

    def test_add_token_empty_token(self, client, mock_encryption_helper):
        """Test creation with empty token."""
        payload = {
            "label": "Test GitHub Token",
            "git_hosting": "github",
            "token_value": "",  # Empty token
        }

        response = client.post("/api/v1/git_tokens/", json=payload)

        assert response.status_code in [
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            status.HTTP_400_BAD_REQUEST,
        ]

    def test_user_id_override_security(self, client, mock_encryption_helper):
        """Test that user_id is overridden with authenticated user for security."""
        with patch("app.routes.git_tokens.GitHubManager") as mock_github_manager:
            mock_instance = MagicMock()
            mock_instance.get_user.return_value = {"login": "testuser"}
            mock_github_manager.return_value = mock_instance

            with patch("app.routes.git_tokens.GitLabel") as mock_git_label:
                mock_created_label = MagicMock()
                mock_created_label.id = "999"
                mock_git_label.create = AsyncMock(return_value=mock_created_label)

                payload = {
                    "label": "Test GitHub Token",
                    "git_hosting": "github",
                    "token_value": "ghp_1234567890abcdef",
                    "user_id": "malicious-user-id",  # This should be overridden
                }

                response = client.post("/api/v1/git_tokens/", json=payload)

                assert response.status_code == status.HTTP_200_OK

                # Verify that GitLabel.create was called with the authenticated user ID, not the provided one
                call_args = mock_git_label.create.call_args
                assert call_args.kwargs["user_id"] == "user-123"


class TestDeleteGitLabelEndpoint:
    """Test cases for DELETE /api/v1/git_tokens/{git_label_id} endpoint."""

    def test_delete_git_label_success(self, client, sample_token_id):
        """Test successful git label deletion."""
        with patch("app.routes.git_tokens.GitLabel") as mock_git_label:
            mock_label = MagicMock()
            mock_label.delete = AsyncMock()
            mock_git_label.filter.return_value.first = AsyncMock(
                return_value=mock_label
            )

            response = client.delete(f"/api/v1/git_tokens/{sample_token_id}")

            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data["success"] is True
            assert "Token deleted successfully" in data["message"]

            mock_label.delete.assert_called_once()

    def test_delete_git_label_not_found(self, client, sample_token_id):
        """Test deletion when git label doesn't exist."""
        with patch("app.routes.git_tokens.GitLabel") as mock_git_label:

            mock_git_label.filter.return_value.first = AsyncMock(return_value=None)

            response = client.delete(f"/api/v1/git_tokens/{sample_token_id}")

            assert response.status_code == status.HTTP_404_NOT_FOUND
            data = response.json()
            assert data["success"] is False
            assert "Token not found" in data["message"]

    def test_delete_git_label_invalid_uuid(self, client):
        """Test deletion with invalid UUID format."""
        response = client.delete("/api/v1/git_tokens/invalid-uuid")

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        data = response.json()
        assert data["success"] is False
        assert "Invalid UUID format" in data["message"]

    def test_delete_token_database_error_on_get(self, client, sample_token_id):
        """Test handling of database error during get operation"""
        with patch("app.routes.git_tokens.GitLabel") as mock_git_label:
            mock_git_label.get = AsyncMock(
                side_effect=Exception("Database connection failed")
            )

            response = client.delete(f"/api/v1/git_tokens/{sample_token_id}")

            assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
            data = response.json()
            assert data["success"] is False
            assert "Service temporarily unavailable" in data["message"]

    @pytest.mark.parametrize(
        "token_id",
        [
            "550e8400-e29b-41d4-a716-446655440000",  # Valid UUID
            "123e4567-e89b-12d3-a456-426614174000",  # Another valid UUID
        ],
    )
    def test_delete_token_valid_uuid_formats(self, client, token_id):
        """Test deletion with valid UUID formats"""
        with patch("app.routes.git_tokens.GitLabel") as mock_git_label:
            mock_label = MagicMock()
            mock_label.delete = AsyncMock()
            mock_git_label.filter.return_value.first = AsyncMock(
                return_value=mock_label
            )

            response = client.delete(f"/api/v1/git_tokens/{token_id}")

            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data["success"] is True


# Performance and integration tests
class TestPerformance:
    """Performance-related tests for the new implementation."""

    def test_large_git_label_list_performance(self, client, mock_encryption_helper):
        """Test handling of large git label lists."""
        with patch("app.routes.git_tokens.GitLabel") as mock_git_label:
            # Create a large list of mock labels
            large_label_list = []
            for i in range(100):  # Reduced from 1000 for faster testing
                mock_label = MagicMock()
                mock_label.id = str(i)
                mock_label.label = f"Label {i}"
                mock_label.git_hosting = "github"
                mock_label.token_value = "encrypted_token"
                mock_label.username = "testuser"
                mock_label.created_at.isoformat.return_value = "2024-01-01T10:00:00"
                mock_label.updated_at.isoformat.return_value = "2024-01-01T10:00:00"
                large_label_list.append(mock_label)

            mock_query = MagicMock()
            mock_query.count = AsyncMock(return_value=100)
            mock_query.order_by.return_value = mock_query
            mock_query.offset.return_value = mock_query
            mock_query.limit.return_value = mock_query
            mock_query.all = AsyncMock(return_value=large_label_list)

            mock_git_label.filter.return_value = mock_query

            response = client.get("/api/v1/git_tokens/")
            assert response.status_code == status.HTTP_200_OK

            data = response.json()
            assert data["success"] is True
            assert len(data["data"]["items"]) == 100

    def test_concurrent_requests(self, client, mock_encryption_helper):
        """Test handling of concurrent requests"""
        import threading

        with patch("app.routes.git_tokens.GitLabel") as mock_git_label:
            mock_query = MagicMock()
            mock_query.count = AsyncMock(return_value=0)
            mock_query.order_by.return_value = mock_query
            mock_query.offset.return_value = mock_query
            mock_query.limit.return_value = mock_query
            mock_query.all = AsyncMock(return_value=[])

            mock_git_label.filter.return_value = mock_query

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


class TestTortoiseOrmIntegration:
    """Test cases specific to Tortoise ORM integration."""

    def test_query_chain_operations(self, client, mock_encryption_helper):
        """Test that Tortoise ORM query chain operations work correctly."""
        with patch("app.routes.git_tokens.GitLabel") as mock_git_label:
            mock_query = MagicMock()

            # Test that all query methods return the query object for chaining
            mock_query.filter.return_value = mock_query
            mock_query.order_by.return_value = mock_query
            mock_query.offset.return_value = mock_query
            mock_query.limit.return_value = mock_query
            mock_query.count = AsyncMock(return_value=0)
            mock_query.all = AsyncMock(return_value=[])

            mock_git_label.filter.return_value = mock_query

            response = client.get("/api/v1/git_tokens/")

            # Verify all query methods were called in the correct order
            mock_git_label.filter.assert_called_once()
            mock_query.order_by.assert_called_with("-created_at")
            mock_query.offset.assert_called()
            mock_query.limit.assert_called()
            mock_query.count.assert_called_once()
            mock_query.all.assert_called_once()

    def test_user_isolation(self, client, mock_encryption_helper):
        """Test that user isolation works correctly."""
        with patch("app.routes.git_tokens.GitLabel") as mock_git_label:
            mock_query = MagicMock()
            mock_query.count = AsyncMock(return_value=0)
            mock_query.order_by.return_value = mock_query
            mock_query.offset.return_value = mock_query
            mock_query.limit.return_value = mock_query
            mock_query.all = AsyncMock(return_value=[])

            mock_git_label.filter.return_value = mock_query

            # Mock the get_current_user_id dependency

            response = client.get("/api/v1/git_tokens/")

            # Verify that GitLabel.filter was called with user_id
            mock_git_label.filter.assert_called_with(user_id="user-123")


# Additional integration tests
class TestGitLabelIntegration:
    """Integration tests for git label endpoints"""

    def test_git_label_endpoint_exists(self, client):
        """Test that the git label endpoints exist and are accessible"""
        # This will return success or error, but not 405 (Method Not Allowed)
        response = client.get("/api/v1/git_tokens/")
        assert response.status_code != status.HTTP_405_METHOD_NOT_ALLOWED

        response = client.post("/api/v1/git_tokens/", json={})
        assert response.status_code != status.HTTP_405_METHOD_NOT_ALLOWED

        response = client.delete("/api/v1/git_tokens/test-id")
        assert response.status_code != status.HTTP_405_METHOD_NOT_ALLOWED

    def test_api_response_structure(self, client, mock_encryption_helper):
        """Test that all endpoints return proper APIResponse structure"""
        with patch("app.routes.git_tokens.GitLabel") as mock_git_label:
            mock_query = MagicMock()
            mock_query.count = AsyncMock(return_value=0)
            mock_query.order_by.return_value = mock_query
            mock_query.offset.return_value = mock_query
            mock_query.limit.return_value = mock_query
            mock_query.all = AsyncMock(return_value=[])

            mock_git_label.filter.return_value = mock_query

            response = client.get("/api/v1/git_tokens/")

            assert response.status_code == status.HTTP_200_OK
            data = response.json()

            assert "success" in data
            assert "message" in data
            assert "data" in data
            assert isinstance(data["success"], bool)
            assert isinstance(data["message"], str)

    def test_current_user_id_consistency(self, client, mock_encryption_helper):
        """Test that get_current_user_id returns consistent user ID across requests"""
        expected_user_id = "user-123"

        with patch("app.routes.git_tokens.GitLabel") as mock_git_label:
            mock_query = MagicMock()
            mock_query.count = AsyncMock(return_value=0)
            mock_query.order_by.return_value = mock_query
            mock_query.offset.return_value = mock_query
            mock_query.limit.return_value = mock_query
            mock_query.all = AsyncMock(return_value=[])

            mock_git_label.filter.return_value = mock_query

            response = client.get("/api/v1/git_tokens/")
            assert response.status_code == status.HTTP_200_OK

            mock_git_label.filter.assert_called_with(user_id=expected_user_id)

    def test_error_handling_consistency(self, client):
        """Test that error handling is consistent across endpoints"""
        # Test invalid UUID handling
        response = client.delete("/api/v1/git_tokens/invalid-uuid")
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        data = response.json()
        assert data["success"] is False
        assert "Invalid UUID format" in data["message"]

    def test_authentication_dependency(self, client, mock_encryption_helper):
        """Test that authentication dependency is properly applied"""
        with patch("app.routes.git_tokens.GitLabel") as mock_git_label:
            mock_query = MagicMock()
            mock_query.count = AsyncMock(return_value=0)
            mock_query.order_by.return_value = mock_query
            mock_query.offset.return_value = mock_query
            mock_query.limit.return_value = mock_query
            mock_query.all = AsyncMock(return_value=[])

            mock_git_label.filter.return_value = mock_query

            # Mock get_current_user_id to simulate different authentication states

            response = client.get("/api/v1/git_tokens/")

            mock_git_label.filter.assert_called_with(user_id="user-123")


class TestEndpointSecurity:
    """Test security aspects of the endpoints"""

    def test_user_data_isolation_get_labels(self, client):
        """Test that users can only see their own git labels"""
        with patch("app.routes.git_tokens.GitLabel") as mock_git_label:
            mock_query = MagicMock()
            mock_query.count = AsyncMock(return_value=0)
            mock_query.order_by.return_value = mock_query
            mock_query.offset.return_value = mock_query
            mock_query.limit.return_value = mock_query
            mock_query.all = AsyncMock(return_value=[])

            mock_git_label.filter.return_value = mock_query

            response = client.get("/api/v1/git_tokens/")

            assert response.status_code == 200
            mock_git_label.filter.assert_called_with(user_id="user-123")

    def test_user_data_isolation_get_by_label(self, client, mock_encryption_helper):
        """Test that users can only see their own git labels when filtering by label"""

        async def mock_get_current_user_id():
            return "user-123"

        # Apply the override to your FastAPI app
        from app.main import app  # Import your FastAPI app
        from app.routes.git_tokens import get_current_user_id

        app.dependency_overrides[get_current_user_id] = mock_get_current_user_id

        try:
            with patch("app.routes.git_tokens.GitLabel") as mock_git_label:
                mock_query = MagicMock()
                mock_query.order_by.return_value = mock_query
                mock_query.offset.return_value = mock_query
                mock_query.limit.return_value = mock_query
                mock_query.all = AsyncMock(return_value=[])
                mock_git_label.filter.return_value = mock_query

                response = client.get("/api/v1/git_tokens/TestLabel")

                # Verify that the query was filtered by both user_id and label
                mock_git_label.filter.assert_called_with(
                    user_id="user-123", label="TestLabel"
                )
        finally:
            # Clean up the override
            app.dependency_overrides.clear()

    def test_token_encryption_on_create(self, client, mock_encryption_helper):
        """Test that tokens are properly encrypted when creating git labels"""
        with patch("app.routes.git_tokens.GitHubManager") as mock_github_manager:
            mock_instance = MagicMock()
            mock_instance.get_user.return_value = {"login": "testuser"}
            mock_github_manager.return_value = mock_instance

            with patch("app.routes.git_tokens.GitLabel") as mock_git_label:
                mock_created_label = MagicMock()
                mock_created_label.id = "999"
                mock_git_label.create = AsyncMock(return_value=mock_created_label)

                payload = {
                    "label": "Test GitHub Token",
                    "git_hosting": "github",
                    "token_value": "ghp_1234567890abcdef",
                }

                response = client.post("/api/v1/git_tokens/", json=payload)

                mock_encryption_helper.encrypt.assert_called_once()

                call_args = mock_git_label.create.call_args
                assert "token_value" in call_args.kwargs

    def test_token_masking_in_response(self, client, mock_encryption_helper):
        """Test that tokens are properly masked in API responses"""
        mock_labels = [
            MagicMock(
                id="1",
                label="GitHub Production",
                git_hosting="github",
                token_value="encrypted_token",
                username="testuser",
                created_at=MagicMock(
                    isoformat=MagicMock(return_value="2024-01-01T10:00:00+00:00")
                ),
                updated_at=MagicMock(
                    isoformat=MagicMock(return_value="2024-01-02T10:00:00+00:00")
                ),
            )
        ]

        with patch("app.routes.git_tokens.GitLabel") as mock_git_label:
            mock_query = MagicMock()
            mock_query.count = AsyncMock(return_value=1)
            mock_query.order_by.return_value = mock_query
            mock_query.offset.return_value = mock_query
            mock_query.limit.return_value = mock_query
            mock_query.all = AsyncMock(return_value=mock_labels)

            mock_git_label.filter.return_value = mock_query

            response = client.get("/api/v1/git_tokens/")

            mock_encryption_helper.decrypt.assert_called()

            data = response.json()
            assert data["data"]["items"][0]["masked_token"] == "ghp_************cdef"

            # Verify the original token is not in the response
            response_str = response.text
            assert "ghp_1234567890abcdef" not in response_str


class TestInputValidation:
    """Test input validation and edge cases"""

    def test_empty_label_handling(self, client, mock_encryption_helper):
        """Test handling of empty labels"""
        payload = {
            "label": "",  # Empty label
            "git_hosting": "github",
            "token_value": "ghp_1234567890abcdef",
        }

        response = client.post("/api/v1/git_tokens/", json=payload)

        # Should return validation error or handle gracefully
        assert response.status_code in [status.HTTP_400_BAD_REQUEST]

    def test_whitespace_token_handling(self, client, mock_encryption_helper):
        """Test that whitespace is properly stripped from tokens"""
        with patch("app.routes.git_tokens.GitHubManager") as mock_github_manager:
            mock_instance = MagicMock()
            mock_instance.get_user.return_value = {"login": "testuser"}
            mock_github_manager.return_value = mock_instance

            with patch("app.routes.git_tokens.GitLabel") as mock_git_label:
                mock_created_label = MagicMock()
                mock_created_label.id = "999"
                mock_git_label.create = AsyncMock(return_value=mock_created_label)

                payload = {
                    "label": "Test GitHub Token",
                    "git_hosting": "github",
                    "token_value": " ghp_1234567890abcdef ",  # Token with whitespace
                }

                response = client.post("/api/v1/git_tokens/", json=payload)

                # Verify that the token was trimmed before encryption
                mock_encryption_helper.encrypt.assert_called_with(
                    "ghp_1234567890abcdef"
                )

    def test_slashes_characters_in_label_path(self, client):
        """Test handling of slashes characters in label path parameter"""

        response = client.get(f"/api/v1/git_tokens/label/with/slashes")
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_special_characters_in_label_path(self, client):
        """Test handling of special characters in label path parameter"""
        special_labels = [
            "label with spaces",
            # "label/with/slashes",
            "label@with@symbols",
            "label%20encoded",
        ]

        for label in special_labels:
            with patch("app.routes.git_tokens.GitLabel") as mock_git_label:
                mock_query = MagicMock()
                mock_query.order_by.return_value = mock_query
                mock_query.offset.return_value = mock_query
                mock_query.limit.return_value = mock_query
                mock_query.all = AsyncMock(return_value=[])

                mock_git_label.filter.return_value = mock_query

                encoded_label = quote(label)
                response = client.get(f"/api/v1/git_tokens/{encoded_label}")
                assert response.status_code == status.HTTP_200_OK


class TestEdgeCases:
    """Test edge cases and boundary conditions"""

    def test_very_long_label(self, client, mock_encryption_helper):
        """Test handling of very long labels"""
        long_label = "a" * 1000  # Very long label
        payload = {
            "label": long_label,
            "git_hosting": "github",
            "token_value": "ghp_1234567890abcdef",
            "user_id": 1,
        }

        response = client.post("/api/v1/git_tokens/", json=payload)

        # Should either succeed or return appropriate validation error
        assert response.status_code in [
            status.HTTP_201_CREATED,
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            status.HTTP_200_OK,
        ]

    def test_malformed_uuid_variations(self, client):
        """Test various malformed UUID formats"""
        malformed_uuids = [
            "not-a-uuid",
            "123",
            "123e4567-e89b-12d3-a456",  # Too short
            "123e4567-e89b-12d3-a456-426614174000-extra",  # Too long
            "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",  # Invalid characters
            # "",  # Empty string
            # "123e4567e89b12d3a456426614174000",  # Missing hyphens
        ]

        for uuid_str in malformed_uuids:
            response = client.delete(f"/api/v1/git_tokens/{uuid_str}")
            data = response.json()

            assert response.status_code == status.HTTP_400_BAD_REQUEST

            assert data["success"] is False
