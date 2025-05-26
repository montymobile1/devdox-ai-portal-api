import pytest
from fastapi import status
from unittest.mock import patch
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
    return [
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
    ]


@pytest.fixture
def sample_gitlab_repos():
    return [
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
    ]


@pytest.fixture
def mock_token_github():
    return {"token_value": "encrypted_github_token", "git_hosting": GitHosting.GITHUB}


@pytest.fixture
def mock_token_gitlab():
    return {"token_value": "encrypted_gitlab_token", "git_hosting": GitHosting.GITLAB}


@patch("app.routes.repos.SupabaseClient")
def test_get_repos_by_user_success(mock_supabase_client, client, sample_repos):
    user_id = "user-1"
    mock_instance = mock_supabase_client.return_value
    mock_instance.filter.return_value = sample_repos

    response = client.get(f"/api/v1/repos/{user_id}")

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 1
    assert data[0]["user_id"] == user_id
    mock_instance.filter.assert_called_once_with(
        table="repo", filters={"user_id": user_id}, limit=20, order_by="created_at.desc"
    )


@patch("app.routes.repos.SupabaseClient")
def test_get_repos_by_user_empty(mock_supabase_client, client):
    user_id = "user-2"
    mock_instance = mock_supabase_client.return_value
    mock_instance.filter.return_value = []

    response = client.get(f"/api/v1/repos/{user_id}")

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == []


@patch("app.routes.repos.SupabaseClient")
def test_get_repos_by_user_failure(mock_supabase_client, client):
    user_id = "user-3"
    mock_instance = mock_supabase_client.return_value
    mock_instance.filter.side_effect = Exception("Something went wrong")

    response = client.get(f"/api/v1/repos/{user_id}")

    assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
    assert response.json()["detail"] == constants.SERVICE_UNAVAILABLE


class TestGetReposFromGitErrors:
    """Test error cases for the GET /repos/git_repos/{user_id}/{token_id} endpoint"""

    @patch("app.routes.repos.SupabaseClient")
    @patch("app.routes.repos.EncryptionHelper")
    def test_unsupported_provider(self, mock_encryption, mock_supabase_client, client):
        """Test unsupported Git hosting provider"""
        user_id = "user-1"
        token_id = "token-123"

        mock_token = {
            "token_value": "encrypted_token",
            "git_hosting": "BITBUCKET",  # Unsupported provider
        }

        mock_instance = mock_supabase_client.return_value
        mock_instance.get_by_id.return_value = mock_token

        mock_encryption_instance = mock_encryption.return_value
        mock_encryption_instance.decrypt.return_value = "decrypted_token"

        response = client.get(f"/api/v1/repos/git_repos/{user_id}/{token_id}")

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "Unsupported Git hosting provider" in response.json()["message"]

    @patch("app.routes.repos.SupabaseClient")
    @patch("app.routes.repos.EncryptionHelper")
    def test_missing_git_hosting_field(
        self, mock_encryption, mock_supabase_client, client
    ):
        """Test when git_hosting field is missing from token"""
        user_id = "user-1"
        token_id = "token-123"

        mock_token = {
            "token_value": "encrypted_token"
            # Missing git_hosting field
        }

        mock_instance = mock_supabase_client.return_value
        mock_instance.get_by_id.return_value = mock_token

        mock_encryption_instance = mock_encryption.return_value
        mock_encryption_instance.decrypt.return_value = "decrypted_token"

        response = client.get(f"/api/v1/repos/git_repos/{user_id}/{token_id}")

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "Unsupported Git hosting provider" in response.json()["message"]

    @patch("app.routes.repos.SupabaseClient")
    def test_supabase_exception(self, mock_supabase_client, client):
        """Test Supabase client exception handling"""
        user_id = "user-1"
        token_id = "token-123"

        mock_instance = mock_supabase_client.return_value
        mock_instance.get_by_id.side_effect = Exception("Database connection failed")

        response = client.get(f"/api/v1/repos/git_repos/{user_id}/{token_id}")

        assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
        assert response.json()["message"] == constants.SERVICE_UNAVAILABLE

    @patch("app.routes.repos.SupabaseClient")
    @patch("app.routes.repos.EncryptionHelper")
    def test_encryption_exception(
        self, mock_encryption, mock_supabase_client, client, mock_token_github
    ):
        """Test encryption/decryption exception handling"""
        user_id = "user-1"
        token_id = "token-123"

        mock_instance = mock_supabase_client.return_value
        mock_instance.get_by_id.return_value = mock_token_github

        mock_encryption_instance = mock_encryption.return_value
        mock_encryption_instance.decrypt.side_effect = Exception("Decryption failed")

        response = client.get(f"/api/v1/repos/git_repos/{user_id}/{token_id}")

        assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
        assert response.json()["message"] == constants.SERVICE_UNAVAILABLE

    @patch("app.routes.repos.SupabaseClient")
    @patch("app.routes.repos.EncryptionHelper")
    @patch("app.routes.repos.GitHubManager")
    def test_github_manager_exception(
        self,
        mock_github_manager,
        mock_encryption,
        mock_supabase_client,
        client,
        mock_token_github,
    ):
        """Test GitHub manager exception handling"""
        user_id = "user-1"
        token_id = "token-123"

        mock_instance = mock_supabase_client.return_value
        mock_instance.get_by_id.return_value = mock_token_github

        mock_encryption_instance = mock_encryption.return_value
        mock_encryption_instance.decrypt.return_value = "decrypted_github_token"

        mock_github_instance = mock_github_manager.return_value
        mock_github_instance.get_user_repositories.side_effect = Exception(
            "GitHub API error"
        )

        response = client.get(f"/api/v1/repos/git_repos/{user_id}/{token_id}")

        assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
        assert response.json()["message"] == constants.SERVICE_UNAVAILABLE

    @patch("app.routes.repos.SupabaseClient")
    @patch("app.routes.repos.EncryptionHelper")
    @patch("app.routes.repos.GitLabManager")
    def test_gitlab_manager_exception(
        self,
        mock_gitlab_manager,
        mock_encryption,
        mock_supabase_client,
        client,
        mock_token_gitlab,
    ):
        """Test GitLab manager exception handling"""
        user_id = "user-1"
        token_id = "token-456"

        mock_instance = mock_supabase_client.return_value
        mock_instance.get_by_id.return_value = mock_token_gitlab

        mock_encryption_instance = mock_encryption.return_value
        mock_encryption_instance.decrypt.return_value = "decrypted_gitlab_token"

        mock_gitlab_instance = mock_gitlab_manager.return_value
        mock_gitlab_instance.get_repos.side_effect = Exception("GitLab API error")

        response = client.get(f"/api/v1/repos/git_repos/{user_id}/{token_id}")

        assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
        assert response.json()["message"] == constants.SERVICE_UNAVAILABLE


class TestRepoUtilityFunctions:
    """Test utility functions used in repository endpoints"""

    def test_build_repo_dict_github(self):
        """Test build_repo_dict function for GitHub repositories"""
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
        assert "visibility" not in result  # GitHub specific field should not be present

    def test_build_repo_dict_gitlab(self):
        """Test build_repo_dict function for GitLab repositories"""
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
        assert "private" not in result  # GitHub specific field should not be present

    def test_get_git_repo_fetcher_github(self):
        """Test get_git_repo_fetcher function for GitHub"""
        from app.routes.repos import get_git_repo_fetcher, fetch_github_repos

        fetcher = get_git_repo_fetcher(GitHosting.GITHUB)
        assert fetcher == fetch_github_repos

    def test_get_git_repo_fetcher_gitlab(self):
        """Test get_git_repo_fetcher function for GitLab"""
        from app.routes.repos import get_git_repo_fetcher, fetch_gitlab_repos

        fetcher = get_git_repo_fetcher(GitHosting.GITLAB)
        assert fetcher == fetch_gitlab_repos
