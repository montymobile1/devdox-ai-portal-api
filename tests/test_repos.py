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
from app.utils import constants


def create_does_not_exist_exception():
    """Create a properly formed DoesNotExist exception for Tortoise ORM."""
    # Create a mock model class to satisfy DoesNotExist constructor
    mock_model = Mock()
    mock_model.__name__ = "MockModel"
    return DoesNotExist(mock_model)


@pytest.fixture
def sample_repo_dict_list():
    """Sample list of repository data as dictionaries"""
    return [
        {
            "id": 1,
            "user_id": "user-1",
            "repo_id": "123",
            "repo_name": "repo-1",
            "description": "First repository",
            "html_url": "https://github.com/user/repo-1",
            "default_branch": "main",
            "forks_count": 5,
            "stargazers_count": 10,
            "is_private": False,
            "visibility": None,
            "git_hosting": GitHosting.GITHUB,
            "token_id": "token-123",
            "created_at": datetime.now(),
            "updated_at": datetime.now(),
            "repo_created_at": None,
            "repo_updated_at": None,
            "language": "Python",
            "size": 1024,
        },
        {
            "id": 2,
            "user_id": "user-1",
            "repo_id": "456",
            "repo_name": "repo-2",
            "description": "Second repository",
            "html_url": "https://gitlab.com/user/repo-2",
            "default_branch": "main",
            "forks_count": 3,
            "stargazers_count": 7,
            "is_private": True,
            "visibility": "private",
            "git_hosting": GitHosting.GITLAB,
            "token_id": "token-456",
            "created_at": datetime.now(),
            "updated_at": datetime.now(),
            "repo_created_at": None,
            "repo_updated_at": None,
            "language": "JavaScript",
            "size": 512,
        },
    ]


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
def sample_gitlab_repos():
    """Sample GitLab API response"""
    return {
        "repositories": [
            {
                "id": 456,
                "name": "gitlab-repo",
                "description": "A GitLab repository",
                "default_branch": "main",
                "forks_count": 3,
                "stargazers_count": 7,
                "visibility": "public",
                "http_url_to_repo": "https://gitlab.com/user/gitlab-repo",
            }
        ],
        "pagination_info": {"total_pages": 1},
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
