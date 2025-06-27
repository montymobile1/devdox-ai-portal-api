import datetime
from http import HTTPStatus
from uuid import uuid4

import pytest
from clerk_backend_api import Requestish
from fastapi.testclient import TestClient

from app.config import GitHosting
from app.main import app
from app.schemas.repo import RepoResponse
from app.services.repository_service import RepoManipulationService, RepoQueryService
from app.utils.auth import (
    get_authenticated_user,
    get_user_authenticator_dependency,
    IUserAuthenticator,
    UserClaims,
)


class TestRepoRouter:

    @pytest.fixture(autouse=True)
    def setup(self):
        self.user = UserClaims(
            sub="router-123", email="r@example.com", name="RouterUser"
        )
        self.repo = RepoResponse(
            id=uuid4(),
            user_id="router-123",
            repo_id="repo-1",
            repo_name="test-repo",
            description="Test repository",
            html_url="https://example.com/repo",
            default_branch="main",
            forks_count=10,
            stargazers_count=20,
            is_private=True,
            visibility="private",
            git_hosting=GitHosting.GITHUB.value,
            language="Python",
            size=512,
            repo_created_at=datetime.datetime.now(),
            repo_updated_at=datetime.datetime.now(),
            created_at=datetime.datetime.now(),
            updated_at=datetime.datetime.now(),
            token_id="token-1",
        )

    @pytest.fixture
    def override_dependencies(self):
        def _override(user=None, service=None):
            app.dependency_overrides[get_authenticated_user] = lambda: user or self.user
            app.dependency_overrides[RepoQueryService] = (
                lambda: service or self.mock_service
            )

        yield _override
        app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_successful_repo_fetch(self, override_dependencies):
        repo = self.repo  # capture repo from outer scope

        class MockService:
            async def get_all_user_repositories(self, *args, **kwargs):
                return 1, [repo]

        self.mock_service = MockService()
        override_dependencies()

        with TestClient(app) as client:
            response = client.get("/api/v1/repos/")
            assert response.status_code == HTTPStatus.OK
            data = response.json()["data"]
            assert data["total_count"] == 1
            assert data["repos"][0]["repo_name"] == repo.repo_name

    @pytest.mark.asyncio
    async def test_empty_repo_list(self, override_dependencies):
        class MockService:
            async def get_all_user_repositories(self, *args, **kwargs):
                return 0, []

        self.mock_service = MockService()
        override_dependencies()

        with TestClient(app) as client:
            response = client.get("/api/v1/repos/")
            assert response.status_code == HTTPStatus.OK
            data = response.json()["data"]
            assert data["total_count"] == 0
            assert data["repos"] == []

    @pytest.mark.asyncio
    async def test_service_exception_handling(self, override_dependencies):
        class MockService:
            async def get_all_user_repositories(self, *args, **kwargs):
                raise Exception("Unexpected failure")

        self.mock_service = MockService()
        override_dependencies()

        with TestClient(app, raise_server_exceptions=False) as client:
            response = client.get("/api/v1/repos/")
            assert response.status_code == HTTPStatus.SERVICE_UNAVAILABLE

    @pytest.mark.asyncio
    async def test_with_pagination_params(self, override_dependencies):
        repo = self.repo  # capture the repo in the outer scope

        class MockService:
            async def get_all_user_repositories(self, user, pagination):
                assert pagination.limit == 10
                assert pagination.offset == 20
                return 1, [repo]

        self.mock_service = MockService()
        override_dependencies()

        with TestClient(app) as client:
            response = client.get("/api/v1/repos/?limit=10&offset=20")
            assert response.status_code == HTTPStatus.OK
            data = response.json()["data"]
            assert data["total_count"] == 1
            assert len(data["repos"]) == 1


class TestAddRepoFromGit:

    class FakeRepoService:
        def __init__(self):
            self.called_with = None

        async def add_repo_from_provider(self, user, token_id, relative_path):
            self.called_with = (user, token_id, relative_path)

    class FakeAuthenticator(IUserAuthenticator):
        async def authenticate(self, request: Requestish) -> UserClaims:
            return UserClaims(sub="user123")

    @pytest.fixture
    def client(self):
        app.dependency_overrides[RepoManipulationService] = (
            lambda: self.FakeRepoService()
        )
        app.dependency_overrides[get_user_authenticator_dependency] = (
            lambda: self.FakeAuthenticator()
        )
        yield TestClient(app)
        app.dependency_overrides.clear()

    def test_add_repo_from_git(self, client):
        payload = {"relative_path": "owner/repo"}
        headers = {"Authorization": "Bearer faketoken"}
        response = client.post(
            "/api/v1/repos/git_repos/users/token_abc", json=payload, headers=headers
        )
        assert response.status_code == 200
        assert response.json()["success"] is True
        assert "Repository added successfully" in response.json()["message"]

    def test_add_repo_from_git_validation_error(self, client):
        headers = {"Authorization": "Bearer faketoken"}
        response = client.post(
            "/api/v1/repos/git_repos/users/token_abc", json={}, headers=headers
        )
        assert (
            response.status_code == 422
        )  # Unprocessable Entity for missing 'relative_path'
