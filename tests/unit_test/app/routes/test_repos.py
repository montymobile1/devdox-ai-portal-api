import datetime
import uuid

import pytest
from fastapi import status
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock

from app.config import GitHosting
from app.main import app
from app.schemas.repo import RepoResponse
from app.utils.auth import UserClaims
from app.utils.constants import RESOURCE_RETRIEVED_SUCCESSFULLY
from app.routes.repos import (
    get_authenticated_user,
    repo_query_service_dependency_definition,
)


class TestGetReposEndpoint:

    @pytest.fixture(autouse=True)
    def setup(self):
        self.endpoint = "/api/v1/repos/"
        self.test_user = UserClaims(
            sub="test-user", email="test@example.com", name="Test User"
        )
        date_time = datetime.datetime.combine(
            datetime.datetime.now(datetime.timezone.utc).date(),
            datetime.time.min,
            tzinfo=datetime.timezone.utc,
        )

        self.test_repos = [
            RepoResponse(
                id=uuid.UUID("8e0cead3-953c-4aa3-8b38-933045fde176"),
                user_id="test-user",
                repo_id="123",
                repo_name="repo-one",
                description="A test repo",
                html_url="https://example.com/repo-one",
                default_branch="main",
                forks_count=3,
                stargazers_count=7,
                is_private=False,
                visibility="public",
                token_id="token-xyz",
                created_at=date_time,
                updated_at=date_time,
                repo_created_at=date_time,
                repo_updated_at=date_time,
                language="Python",
                size=100,
                git_hosting=GitHosting.GITHUB.value,
            )
        ]

    def override_deps(self, user=None, service=None):
        app.dependency_overrides[get_authenticated_user] = (
            lambda: user or self.test_user
        )
        app.dependency_overrides[repo_query_service_dependency_definition] = (
            lambda: service or self.mock_service
        )

    def clear_deps(self):
        app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_success(self):
        self.mock_service = AsyncMock()
        self.mock_service.get_all_user_repositories.return_value = (1, self.test_repos)
        self.override_deps()

        with TestClient(app) as client:
            response = client.get(self.endpoint)
            assert response.status_code == status.HTTP_200_OK
            body = response.json()
            assert body["message"] == RESOURCE_RETRIEVED_SUCCESSFULLY
            assert body["data"]["total_count"] == 1
            assert body["data"]["repos"][0]["repo_name"] == "repo-one"
        self.clear_deps()

    @pytest.mark.asyncio
    async def test_empty_repo_list(self):
        self.mock_service = AsyncMock()
        self.mock_service.get_all_user_repositories.return_value = (0, [])
        self.override_deps()

        with TestClient(app) as client:
            response = client.get(self.endpoint)
            assert response.status_code == status.HTTP_200_OK
            data = response.json()["data"]
            assert data["total_count"] == 0
            assert data["repos"] == []
        self.clear_deps()

    @pytest.mark.asyncio
    async def test_service_throws_exception(self):
        self.mock_service = AsyncMock()
        self.mock_service.get_all_user_repositories.side_effect = Exception("DB down")
        self.override_deps()

        with TestClient(app, raise_server_exceptions=False) as client:
            response = client.get(self.endpoint)
            assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
        self.clear_deps()

    @pytest.mark.asyncio
    async def test_with_pagination(self):
        self.mock_service = AsyncMock()
        self.mock_service.get_all_user_repositories.return_value = (1, self.test_repos)
        self.override_deps()

        with TestClient(app) as client:
            response = client.get(f"{self.endpoint}?offset=0&limit=1")
            assert response.status_code == status.HTTP_200_OK
            data = response.json()["data"]
            assert data["total_count"] == 1
            assert len(data["repos"]) == 1
        self.clear_deps()
