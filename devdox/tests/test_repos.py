"""
Updated test cases for repository API endpoints using Tortoise ORM.
Tests cover all CRUD operations and new functionality.
"""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest
from fastapi import status
from tortoise.exceptions import DoesNotExist

from app.config import GitHosting
from app.exceptions.exception_constants import SERVICE_UNAVAILABLE
from app.utils import constants

@pytest.fixture
def sample_github_repos():
    """Sample GitHub API response"""
    return {
        "repositories": [
            {
                "id": 123,
                "name": "test-repo",
                "description": "A test repository",
                "default_branch": "main",
                "forks_count": 5,
                "stargazers_count": 10,
                "private": False,
                "html_url": "https://github.com/user/test-repo",
            }
        ],
        "pagination_info": {"total_count": 1},
    }



@pytest.fixture
def mock_git_label():
    """Mock GitLabel model"""
    return Mock(
        id="token-123",
        user_id="user-1",
        token_value="encrypted_token",
        git_hosting=GitHosting.GITHUB,
    )


mock_git_label_class = MagicMock(
    name="GitLabel",
    spec=None,
)


@pytest.mark.skip("DEPRECATED and OLD")
class TestGetReposFromGitEndpoint:
    """Test cases for GET /repos/git_repos/{user_id}/{token_id} endpoint."""

    @patch("app.routes.repos.get_git_repo_fetcher")
    async def test_get_repos_from_git_success(
        mock_fetcher,
        client,
        sample_github_repos,
    ):
        """Test successful retrieval of repos from Git provider."""
        user_id = "user-1"
        token_id = "token-123"

        with patch("app.routes.repos.GitLabel") as mock_git_label:
            mock_label = MagicMock()
            mock_label.id = token_id
            mock_label.user_id = user_id
            mock_label.token_value = "encrypted_token"
            mock_label.git_hosting = GitHosting.GITHUB

            mock_git_label.filter.return_value.first = AsyncMock(
                return_value=mock_label
            )
            with patch("app.utils.encryption.EncryptionHelper") as mock_helper:
                mock_instance = MagicMock()
                mock_instance.decrypt.return_value = "ghp_1234567890abcdef"
                mock_helper.return_value = mock_instance
                mock_helper.encrypt = mock_instance.encrypt
                mock_helper.decrypt = mock_instance.decrypt
                yield mock_helper

            # Mock fetcher - it should return a function that returns the repos
            mock_fetcher_func = Mock(
                return_value=(sample_github_repos["repositories"], 1)
            )

            mock_fetcher.return_value = mock_fetcher_func

            response = client.get(f"/api/v1/repos/git_repos/{user_id}/{token_id}")
            data = response.json()

            assert response.status_code == status.HTTP_200_OK
            assert data["success"] is True
            assert data["data"]["total_count"] == 1
            assert len(data["data"]["repos"]) == 1

    @patch("app.routes.repos.GitLabel")
    async def test_get_repos_from_git_token_not_found(self, mock_git_label, client):
        """Test response when token is not found."""
        user_id = "user-1"
        token_id = "nonexistent-token"

        mock_git_label.filter.return_value.first = AsyncMock(return_value=None)

        response = client.get(f"/api/v1/repos/git_repos/{user_id}/{token_id}")

        assert response.status_code == status.HTTP_404_NOT_FOUND
        data = response.json()
        assert data["message"] == constants.TOKEN_NOT_FOUND

    @patch("app.routes.repos.get_git_repo_fetcher")
    @patch("app.routes.repos.EncryptionHelper")
    @patch("app.routes.repos.GitLabel")
    async def test_get_repos_from_git_unsupported_provider(
        self, mock_git_label, mock_encryption, mock_fetcher, client
    ):
        """Test unsupported Git hosting provider."""
        user_id = "user-1"
        token_id = "token-123"

        # Create a mock token instance
        mock_token = Mock()
        mock_token.id = token_id
        mock_token.user_id = user_id
        mock_token.token_value = "encrypted_token"
        mock_token.git_hosting = "BITBUCKET"  # Unsupported provider

        # Mock the filter().first() chain
        mock_filter = Mock()
        mock_filter.first = AsyncMock(return_value=mock_token)
        mock_git_label.filter.return_value = mock_filter

        # Mock the encryption helper
        mock_encryption_instance = Mock()
        mock_encryption_instance.decrypt.return_value = "decrypted_token"
        mock_encryption.return_value = mock_encryption_instance

        # Mock the fetcher to return None for unsupported provider
        mock_fetcher.return_value = None

        response = client.get(f"/api/v1/repos/git_repos/{user_id}/{token_id}")

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        data = response.json()
        assert "Unsupported Git hosting provider" in data["message"]
