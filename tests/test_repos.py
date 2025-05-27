"""
Updated test cases for repository API endpoints.
Fixed mocking to match actual database client usage.
"""

import pytest
from fastapi import status
from unittest.mock import patch, AsyncMock, Mock
from app.utils import constants
from app.config import GitHosting


@pytest.fixture
def sample_repos():
    return [
        {
            "repo_id": "uuid-123",
            "user_id": "user-1",
            "repo_name": "awesome-repo",
            "description": "Test repository",
            "last_commit": "abc123",
            "star_count": 10,
            "commit_count": 50,
            "fork_count": 5,
            "branch_default": "main",
            "created_at": "2024-01-01T00:00:00Z",
            "updated_at": "2024-01-01T00:00:00Z",
        }
    ]


@pytest.fixture
def sample_github_repos():
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
def mock_token_github():
    return {"token_value": "encrypted_github_token", "git_hosting": GitHosting.GITHUB}


@pytest.fixture
def mock_token_gitlab():
    return {"token_value": "encrypted_gitlab_token", "git_hosting": GitHosting.GITLAB}


class TestGetReposEndpoint:
    """Test cases for GET /repos/{user_id} endpoint."""

    @patch("app.routes.repos.db_client")
    async def test_get_repos_by_user_success(
        self, mock_db_client, client, sample_repos
    ):
        """Test successful retrieval of repos by user ID."""
        user_id = "user-1"

        # Mock the database query
        mock_db_client.execute_query = AsyncMock(return_value=sample_repos)

        # Make the request
        response = client.get(f"/api/v1/repos/{user_id}")

        # Verify response
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 1
        assert data[0]["user_id"] == user_id

        # Verify the database was called with correct query
        expected_query = f"SELECT * FROM repo WHERE user_id =  '{user_id}' ORDER BY created_at DESC LIMIT 20 OFFSET 0"
        mock_db_client.execute_query.assert_called_once_with(expected_query)

    @patch("app.routes.repos.db_client")
    async def test_get_repos_by_user_empty(self, mock_db_client, client):
        """Test retrieval when user has no repos."""
        user_id = "user-2"

        # Mock empty database response
        mock_db_client.execute_query = AsyncMock(return_value=[])

        # Make the request
        response = client.get(f"/api/v1/repos/{user_id}")

        # Verify response
        assert response.status_code == status.HTTP_200_OK
        assert response.json() == []

    @patch("app.routes.repos.db_client")
    async def test_get_repos_by_user_failure(self, mock_db_client, client):
        """Test error handling when database query fails."""
        user_id = "user-3"

        # Mock database error
        mock_db_client.execute_query = AsyncMock(
            side_effect=Exception("Database error")
        )

        # Make the request
        response = client.get(f"/api/v1/repos/{user_id}")

        # Verify error response
        assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
        assert response.json()["detail"] == constants.SERVICE_UNAVAILABLE

    @patch("app.routes.repos.db_client")
    async def test_get_repos_with_pagination(
        self, mock_db_client, client, sample_repos
    ):
        """Test repos retrieval with custom pagination."""
        user_id = "user-1"
        limit = 10
        offset = 5

        # Mock the database query
        mock_db_client.execute_query = AsyncMock(return_value=sample_repos)

        # Make the request with pagination parameters
        response = client.get(f"/api/v1/repos/{user_id}?limit={limit}&offset={offset}")

        # Verify response
        assert response.status_code == status.HTTP_200_OK

        # Verify the database was called with correct pagination
        expected_query = f"SELECT * FROM repo WHERE user_id =  '{user_id}' ORDER BY created_at DESC LIMIT {limit} OFFSET {offset}"
        mock_db_client.execute_query.assert_called_once_with(expected_query)

    @patch("app.routes.repos.db_client")
    async def test_token_not_found(self, mock_db_client, client):
        """Test response when token is not found."""
        user_id = "user-1"
        token_id = "token-1"

        mock_db_client.execute_query_one = AsyncMock(return_value=None)
        response = client.get(f"/api/v1/repos/git_repos/{user_id}/{token_id}")
        assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE

        #assert response.json()["detail"] == "Token not found"

    @patch("app.routes.repos.get_git_repo_fetcher")
    @patch("app.routes.repos.EncryptionHelper")
    @patch("app.routes.repos.db_client")
    async def test_successful_repo_fetch(
            self, mock_db_client, mock_encryption_helper, mock_get_repo_fetcher, client
    ):
        """Test successful retrieval of repos from Git provider."""
        user_id = "user-1"
        token_id = "token-1"

        # Mock DB return
        mock_token_data = {
            "token_value": "encrypted_value",
            "git_hosting": "github"
        }
        mock_db_client.execute_query_one = AsyncMock(return_value=mock_token_data)

        # Mock token decryption
        mock_encryption_helper.return_value.decrypt.return_value = "decrypted_token"

        # Mock repo fetcher
        mock_fetcher = Mock(return_value=([{"id": 1, "name": "repo1"}], 1))
        mock_get_repo_fetcher.return_value = mock_fetcher

        # Perform request
        response = client.get(f"/api/v1/repos/git_repos/{user_id}/{token_id}")
        data = response.json()
        print("line 203 ", data)
        # Validate response
        assert response.status_code == status.HTTP_200_OK

        assert isinstance(data, dict)
        assert "data" in data
        assert len(data["data"]) == 1
        assert data["data"][0]["total_count"] == 1
        assert data["data"][0]["repos"] == [{"id": 1, "name": "repo1"}]

class TestGetReposFromGitErrors:
    """Test error cases for the GET /repos/git_repos/{user_id}/{token_id} endpoint"""

    @patch("app.routes.repos.db_client")
    @patch("app.routes.repos.EncryptionHelper")
    async def test_unsupported_provider(self, mock_encryption, mock_db_client, client):
        """Test unsupported Git hosting provider"""
        user_id = "user-1"
        token_id = "token-123"

        mock_token = {
            "token_value": "encrypted_token",
            "git_hosting": "BITBUCKET",  # Unsupported provider
        }

        mock_db_client.execute_query_one = AsyncMock(return_value=mock_token)

        mock_encryption_instance = mock_encryption.return_value
        mock_encryption_instance.decrypt.return_value = "decrypted_token"

        response = client.get(f"/api/v1/repos/git_repos/{user_id}/{token_id}")

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "Unsupported Git hosting provider" in response.json()["message"]

    @patch("app.routes.repos.db_client")
    async def test_supabase_exception(self, mock_db_client, client):
        """Test database client exception handling"""
        user_id = "user-1"
        token_id = "token-123"

        mock_db_client.execute_query_one = AsyncMock(
            side_effect=Exception("Database connection failed")
        )

        response = client.get(f"/api/v1/repos/git_repos/{user_id}/{token_id}")

        assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
        assert response.json()["message"] == constants.SERVICE_UNAVAILABLE

    @patch("app.routes.repos.db_client")
    @patch("app.routes.repos.EncryptionHelper")
    async def test_encryption_exception(
        self, mock_encryption, mock_db_client, client, mock_token_github
    ):
        """Test encryption/decryption exception handling"""
        user_id = "user-1"
        token_id = "token-123"

        mock_db_client.execute_query_one = AsyncMock(return_value=mock_token_github)

        mock_encryption_instance = mock_encryption.return_value
        mock_encryption_instance.decrypt.side_effect = Exception("Decryption failed")

        response = client.get(f"/api/v1/repos/git_repos/{user_id}/{token_id}")

        assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
        assert response.json()["message"] == constants.SERVICE_UNAVAILABLE

    @patch("app.routes.repos.db_client")
    @patch("app.routes.repos.EncryptionHelper")
    @patch("app.routes.repos.GitHubManager")
    async def test_github_manager_exception(
        self,
        mock_github_manager,
        mock_encryption,
        mock_db_client,
        client,
        mock_token_github,
    ):
        """Test GitHub manager exception handling"""
        user_id = "user-1"
        token_id = "token-123"

        mock_db_client.execute_query_one = AsyncMock(return_value=mock_token_github)

        mock_encryption_instance = mock_encryption.return_value
        mock_encryption_instance.decrypt.return_value = "decrypted_github_token"

        mock_github_instance = mock_github_manager.return_value
        mock_github_instance.get_user_repositories.side_effect = Exception(
            "GitHub API error"
        )

        response = client.get(f"/api/v1/repos/git_repos/{user_id}/{token_id}")

        assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
        assert response.json()["message"] == constants.SERVICE_UNAVAILABLE

    @patch("app.routes.repos.db_client")
    @patch("app.routes.repos.EncryptionHelper")
    @patch("app.routes.repos.GitLabManager")
    async def test_gitlab_manager_exception(
        self,
        mock_gitlab_manager,
        mock_encryption,
        mock_db_client,
        client,
        mock_token_gitlab,
    ):
        """Test GitLab manager exception handling"""
        user_id = "user-1"
        token_id = "token-456"

        mock_db_client.execute_query_one = AsyncMock(return_value=mock_token_gitlab)

        mock_encryption_instance = mock_encryption.return_value
        mock_encryption_instance.decrypt.return_value = "decrypted_gitlab_token"

        mock_gitlab_instance = mock_gitlab_manager.return_value
        mock_gitlab_instance.get_repos.side_effect = Exception("GitLab API error")

        response = client.get(f"/api/v1/repos/git_repos/{user_id}/{token_id}")

        assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
        assert response.json()["message"] == constants.SERVICE_UNAVAILABLE


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

        assert result["id"] == 123
        assert result["name"] == "test-repo"
        assert result["private"] is False
        assert result["html_url"] == "https://github.com/user/test-repo"
        assert "visibility" not in result

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

        assert result["id"] == 456
        assert result["name"] == "gitlab-repo"
        assert result["visibility"] == "public"
        assert result["html_url"] == "https://gitlab.com/user/gitlab-repo"
        assert "private" not in result

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
        assert repos[0]["name"] == "test-repo"
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
        assert repos[0]["name"] == "gitlab-repo"
        assert total_pages == 1

        # Verify GitLab manager was called correctly
        mock_gitlab_manager.assert_called_once_with(
            base_url="https://gitlab.com", access_token="test_token"
        )
        mock_gitlab_instance.get_repos.assert_called_once_with(page=1, per_page=10)
