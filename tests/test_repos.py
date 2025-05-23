import pytest
from fastapi import status
from unittest.mock import  patch
from app.utils import constants


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
def sample_repos():
    return [
        {
            "repo_id": "uuid-123",
            "user_id": "user-1",
            "repo_name": "test-repo",
            "description": "Repo description",
            "last_commit": "abc123",
            "star_count": 10,
            "commit_count": 20,
            "fork_count": 3,
            "branch_default": "main",
            "created_at": "2024-01-01T00:00:00Z",
            "updated_at": "2024-01-01T00:00:00Z",
        }
    ]


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
        table="repo", filters={"user_id": user_id}
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
