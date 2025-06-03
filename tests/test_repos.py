"""
Updated test cases for repository API endpoints using Tortoise ORM.
Tests cover all CRUD operations and new functionality.
"""

import pytest
from fastapi import status
from unittest.mock import patch, AsyncMock, Mock, MagicMock
from tortoise.exceptions import DoesNotExist
from datetime import datetime

from app.exceptions.exception_constants import SERVICE_UNAVAILABLE
from app.utils import constants
from app.config import GitHosting
from app.schemas.repo import GitHostingProvider


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


class TestGetReposEndpoint:
    """Test cases for GET /repos/{user_id} endpoint."""

    @patch("app.routes.repos.Repo")
    async def test_get_repos_success(self, mock_repo, client, sample_repo_dict_list):
        """Test successful retrieval of repos with pagination."""
        user_id = "user-1"

        # Mock the query chain
        mock_query = MagicMock()
        mock_query.count = AsyncMock(return_value=2)

        mock_query.order_by.return_value = mock_query
        mock_query.offset.return_value = mock_query
        mock_query.limit.return_value = mock_query

        mock_query.all = AsyncMock(return_value=sample_repo_dict_list)

        # Set up the initial filter to return our mock query
        mock_repo.filter.return_value = mock_query

        response = client.get(f"/api/v1/repos/{user_id}?offset=0&limit=10")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["total_count"] == 2
        assert len(data["repos"]) == 2
        assert data["repos"][0]["repo_name"] == "repo-1"

    @patch("app.routes.repos.Repo")
    async def test_get_repos_empty(self, mock_repo, client):
        """Test retrieval when user has no repos."""
        user_id = "user-2"

        mock_filter = MagicMock()
        mock_filter.count = AsyncMock(return_value=0)

        mock_filter.order_by.return_value = mock_filter
        mock_filter.offset.return_value = mock_filter
        mock_filter.limit.return_value = mock_filter

        # Mock all() to return the sample repo list
        mock_filter.all = AsyncMock(return_value=[])

        # Set up the initial filter to return our mock query
        mock_repo.filter.return_value = mock_filter

        response = client.get(f"/api/v1/repos/{user_id}")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["total_count"] == 0
        assert data["repos"] == []

    @patch("app.routes.repos.Repo")
    async def test_get_repos_error(self, mock_repo, client):
        """Test error handling when database query fails."""
        user_id = "user-3"

        mock_repo.filter.side_effect = Exception("Database error")

        response = client.get(f"/api/v1/repos/{user_id}")

        assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
        assert SERVICE_UNAVAILABLE in response.json()["detail"]


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


class TestRepoUtilityFunctions:
    """Test utility functions used in repository endpoints."""

    def test_build_repo_dict_github(self):
        """Test build_repo_dict function for GitHub repositories."""
        from app.routes.repos import build_repo_dict

        github_repo = {
            "id": 123,
            "name": "test-repo",
            "description": "A test repository",
            "default_branch": "main",
            "forks_count": 5,
            "stargazers_count": 10,
            "private": False,
            "html_url": "https://github.com/user/test-repo",
        }

        result = build_repo_dict(github_repo, GitHosting.GITHUB)
        assert result["id"] == "123"  # Should be string
        assert result["repo_name"] == "test-repo"
        assert result["private"] is False
        assert result["html_url"] == "https://github.com/user/test-repo"
        assert result["visibility"] is None

    def test_build_repo_dict_gitlab(self):
        """Test build_repo_dict function for GitLab repositories."""
        from app.routes.repos import build_repo_dict

        gitlab_repo = {
            "id": 456,
            "name": "gitlab-repo",
            "description": "A GitLab repository",
            "default_branch": "main",
            "forks_count": 3,
            "stargazers_count": 7,
            "visibility": "public",
            "http_url_to_repo": "https://gitlab.com/user/gitlab-repo",
        }

        result = build_repo_dict(gitlab_repo, GitHosting.GITLAB)

        assert result["id"] == "456"
        assert result["repo_name"] == "gitlab-repo"
        assert result["visibility"] == "public"
        assert result["html_url"] == "https://gitlab.com/user/gitlab-repo"
        assert result["private"] is None

    def test_get_git_repo_fetcher_github(self):
        """Test get_git_repo_fetcher function for GitHub."""
        from app.routes.repos import get_git_repo_fetcher, fetch_github_repos

        fetcher = get_git_repo_fetcher(GitHosting.GITHUB)
        assert fetcher == fetch_github_repos

    def test_get_git_repo_fetcher_gitlab(self):
        """Test get_git_repo_fetcher function for GitLab."""
        from app.routes.repos import get_git_repo_fetcher, fetch_gitlab_repos

        fetcher = get_git_repo_fetcher(GitHosting.GITLAB)
        assert fetcher == fetch_gitlab_repos

    def test_get_git_repo_fetcher_unsupported(self):
        """Test get_git_repo_fetcher function for unsupported provider."""
        from app.routes.repos import get_git_repo_fetcher

        fetcher = get_git_repo_fetcher("BITBUCKET")
        assert fetcher is None


class TestRepoFetcherFunctions:
    """Test the individual fetcher functions."""

    @patch("app.routes.repos.GitHubManager")
    def test_fetch_github_repos(self, mock_github_manager, sample_github_repos):
        """Test fetch_github_repos function."""
        from app.routes.repos import fetch_github_repos
        from app.schemas.basic import PaginationParams

        # Mock GitHub manager
        mock_github_instance = mock_github_manager.return_value
        mock_github_instance.get_user_repositories.return_value = sample_github_repos

        # Create pagination params
        pagination = PaginationParams(limit=10, offset=0)

        # Call the function
        repos, total_count = fetch_github_repos("test_token", pagination)
        # Verify results
        assert len(repos) == 1
        assert repos[0]["repo_name"] == "test-repo"
        assert repos[0]["id"] == "123"  # Should be string
        assert total_count == 1

        # Verify GitHub manager was called correctly
        mock_github_manager.assert_called_once_with(access_token="test_token")
        mock_github_instance.get_user_repositories.assert_called_once_with(
            page=1, per_page=10
        )

    @patch("app.routes.repos.GitLabManager")
    def test_fetch_gitlab_repos(self, mock_gitlab_manager, sample_gitlab_repos):
        """Test fetch_gitlab_repos function."""
        from app.routes.repos import fetch_gitlab_repos
        from app.schemas.basic import PaginationParams

        # Mock GitLab manager
        mock_gitlab_instance = mock_gitlab_manager.return_value
        mock_gitlab_instance.get_repos.return_value = sample_gitlab_repos

        # Create pagination params
        pagination = PaginationParams(limit=10, offset=0)

        # Call the function
        repos, total_pages = fetch_gitlab_repos("test_token", pagination)

        # Verify results
        assert len(repos) == 1
        assert repos[0]["repo_name"] == "gitlab-repo"
        assert repos[0]["id"] == "456"
        assert total_pages == 1

        # Verify GitLab manager was called correctly
        mock_gitlab_manager.assert_called_once_with(
            base_url="https://gitlab.com", access_token="test_token"
        )
        mock_gitlab_instance.get_repos.assert_called_once_with(page=1, per_page=10)
