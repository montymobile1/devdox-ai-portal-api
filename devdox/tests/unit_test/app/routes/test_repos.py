import datetime
from http import HTTPStatus
from uuid import uuid4

import pytest
from clerk_backend_api import Requestish
from fastapi.testclient import TestClient
from models_src.dto.repo import GitHosting

from app.exceptions.local_exceptions import ValidationFailed
from app.main import app
from app.schemas.repo import RepoResponse
from app.services.repository import RepoManipulationService, RepoQueryService
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
            language=["Python"],
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
        payload = {"relative_path": "owner/repo", "repo_alias_name": "some random alias"}
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
            response.status_code == ValidationFailed.http_status
        )  # Unprocessable Entity for missing 'relative_path'


class TestAnalyzeRepo:

    class FakeRepoService:
        def __init__(self):
            self.called_with = None
            self.call_count = 0

        async def analyze_repo(self, user, repo_id):
            self.called_with = (user, repo_id)
            self.call_count += 1

    class FakeAuthenticator(IUserAuthenticator):
        async def authenticate(self, request: Requestish) -> UserClaims:
            return UserClaims(sub="user123", email="test@example.com", name="TestUser")

    @pytest.fixture
    def fake_repo_service(self):
        """Create a fresh fake repo service for each test"""
        return self.FakeRepoService()

    @pytest.fixture
    def client(self, fake_repo_service):
        app.dependency_overrides[RepoManipulationService] = lambda: fake_repo_service
        app.dependency_overrides[get_user_authenticator_dependency] = (
            lambda: self.FakeAuthenticator()
        )
        yield TestClient(app), fake_repo_service
        app.dependency_overrides.clear()

    def test_analyze_repo_with_string_id(self, client):
        """Test analyze repo with string ID (existing test)"""
        test_client, fake_service = client
        payload = {"id": "123"}
        headers = {"Authorization": "Bearer faketoken"}

        response = test_client.post(
            "/api/v1/repos/analyze", json=payload, headers=headers
        )

        print("response: ", response.json())
        assert response.status_code == 200
        assert response.json()["success"] is True
        assert "Start analyzing successfully" in response.json()["message"]

        # Verify service was called correctly
        assert fake_service.called_with is not None
        user, repo_id = fake_service.called_with
        assert isinstance(user, UserClaims)
        assert user.sub == "user123"
        assert repo_id == "123"

    def test_analyze_repo_with_uuid_format(self, client):
        """Test successful repository analysis with UUID format"""
        test_client, fake_service = client
        test_uuid = str(uuid4())
        payload = {"id": test_uuid}
        headers = {"Authorization": "Bearer faketoken"}

        response = test_client.post(
            "/api/v1/repos/analyze", json=payload, headers=headers
        )

        # Assert response structure and content
        assert response.status_code == 200
        response_data = response.json()
        assert response_data["success"] is True
        assert "Start analyzing successfully" in response_data["message"]

        # Verify service method was called with correct parameters
        assert fake_service.called_with is not None
        user, repo_id = fake_service.called_with
        assert isinstance(user, UserClaims)
        assert user.sub == "user123"
        assert user.email == "test@example.com"
        assert repo_id == test_uuid
        assert fake_service.call_count == 1

    def test_analyze_repo_with_different_uuid_formats(self, client):
        """Test repository analysis with different UUID formats"""
        test_client, fake_service = client
        headers = {"Authorization": "Bearer faketoken"}

        # Test with standard UUID format
        test_uuid1 = str(uuid4())
        response1 = test_client.post(
            "/api/v1/repos/analyze", json={"id": test_uuid1}, headers=headers
        )
        assert response1.status_code == 200

        # Test with UUID without hyphens
        test_uuid2 = str(uuid4()).replace("-", "")
        response2 = test_client.post(
            "/api/v1/repos/analyze", json={"id": test_uuid2}, headers=headers
        )
        assert response2.status_code == 200

        # Verify both calls were made correctly
        assert fake_service.call_count == 2

    def test_proper_service_method_calls_and_response_validation(self, client):
        """Test proper service method calls and comprehensive response validation"""
        test_client, fake_service = client
        test_repo_id = str(uuid4())
        payload = {"id": test_repo_id}
        headers = {"Authorization": "Bearer faketoken"}

        response = test_client.post(
            "/api/v1/repos/analyze", json=payload, headers=headers
        )

        # Comprehensive response validation
        assert response.status_code == 200
        assert response.headers["content-type"] == "application/json"

        response_data = response.json()

        # Validate response structure
        assert "success" in response_data
        assert "message" in response_data
        assert isinstance(response_data["success"], bool)
        assert isinstance(response_data["message"], str)

        # Validate response content
        assert response_data["success"] is True
        assert response_data["message"] == "Start analyzing successfully"

        # Validate service method was called exactly once
        assert fake_service.call_count == 1
        assert fake_service.called_with is not None

        # Validate service method parameters
        user_param, repo_id_param = fake_service.called_with

        # Validate user parameter
        assert isinstance(user_param, UserClaims)
        assert hasattr(user_param, "sub")
        assert hasattr(user_param, "email")
        assert hasattr(user_param, "name")
        assert user_param.sub == "user123"
        assert user_param.email == "test@example.com"
        assert user_param.name == "TestUser"

        # Validate repo_id parameter
        assert repo_id_param == test_repo_id
        assert isinstance(repo_id_param, str)

    def test_analyze_repo_service_call_isolation(self, client):
        """Test that each request creates isolated service calls"""
        test_client, fake_service = client
        headers = {"Authorization": "Bearer faketoken"}

        # First request
        payload1 = {"id": "repo-1"}
        response1 = test_client.post(
            "/api/v1/repos/analyze", json=payload1, headers=headers
        )
        assert response1.status_code == 200
        first_call = fake_service.called_with

        # Second request
        payload2 = {"id": "repo-2"}
        response2 = test_client.post(
            "/api/v1/repos/analyze", json=payload2, headers=headers
        )
        assert response2.status_code == 200
        second_call = fake_service.called_with

        # Verify isolation - second call should overwrite the first
        assert fake_service.call_count == 2
        assert second_call != first_call
        assert second_call[1] == "repo-2"  # repo_id should be from second call

    def test_analyze_repo_authentication_validation(self, client):
        """Test that authentication is properly validated"""
        test_client, fake_service = client
        payload = {"id": str(uuid4())}
        headers = {"Authorization": "Bearer faketoken"}

        response = test_client.post(
            "/api/v1/repos/analyze", json=payload, headers=headers
        )

        assert response.status_code == 200

        # Verify authenticated user was passed to service
        user_param, _ = fake_service.called_with
        assert user_param.sub == "user123"  # From FakeAuthenticator

    def test_analyze_repo_response_format_consistency(self, client):
        """Test that response format is consistent across different scenarios"""
        test_client, fake_service = client
        headers = {"Authorization": "Bearer faketoken"}

        test_cases = [
            {"id": "string-id"},
            {"id": str(uuid4())},
            {"id": "123456"},
        ]

        for payload in test_cases:
            response = test_client.post(
                "/api/v1/repos/analyze", json=payload, headers=headers
            )

            assert response.status_code == 200
            response_data = response.json()
            # Ensure consistent response structure
            assert set(response_data.keys()) == {"success", "message", "status_code"}
            assert response_data["success"] is True
            assert response_data["message"] == "Start analyzing successfully"

    def test_add_analyze_repo_validation_error(self, client):
        """Test validation error for missing payload (existing test)"""
        test_client, _ = client
        headers = {"Authorization": "Bearer faketoken"}
        response = test_client.post("/api/v1/repos/analyze", json={}, headers=headers)
        assert (
            response.status_code == 400
        )  # Unprocessable Entity for missing 'payload id'


class TestReanalyzeRepo:

    class FakeRepoService:
        def __init__(self):
            self.called_with = None
            self.call_count = 0

        async def reanalyze_repo(self, user, repo_id):
            self.called_with = (user, repo_id)
            self.call_count += 1

    class FakeAuthenticator(IUserAuthenticator):
        async def authenticate(self, request: Requestish) -> UserClaims:
            # mirror the analyze tests’ claims
            return UserClaims(sub="user123", email="test@example.com", name="TestUser")

    @pytest.fixture
    def fake_repo_service(self):
        return self.FakeRepoService()

    @pytest.fixture
    def client(self, fake_repo_service):
        app.dependency_overrides[RepoManipulationService] = lambda: fake_repo_service
        app.dependency_overrides[get_user_authenticator_dependency] = (
            lambda: self.FakeAuthenticator()
        )
        yield TestClient(app), fake_repo_service
        app.dependency_overrides.clear()

    def test_reanalyze_repo_with_string_id(self, client):
        test_client, fake_service = client
        payload = {"id": "123"}
        headers = {"Authorization": "Bearer faketoken"}

        resp = test_client.post("/api/v1/repos/re-analyze", json=payload, headers=headers)
        assert resp.status_code in (200, 201)
        body = resp.json()
        assert body["success"] is True
        assert body["message"] == "Reanalysis scheduled successfully"
        assert fake_service.called_with is not None
        user, repo_id = fake_service.called_with
        assert isinstance(user, UserClaims)
        assert user.sub == "user123"
        assert repo_id == "123"

    def test_reanalyze_repo_with_uuid_format(self, client):
        test_client, fake_service = client
        test_uuid = str(uuid4())
        headers = {"Authorization": "Bearer faketoken"}

        resp = test_client.post("/api/v1/repos/re-analyze", json={"id": test_uuid}, headers=headers)
        assert resp.status_code in (200, 201)
        data = resp.json()
        assert data["success"] is True
        assert "Reanalysis scheduled successfully" in data["message"]
        user, repo_id = fake_service.called_with
        assert user.email == "test@example.com"
        assert repo_id == test_uuid
        assert fake_service.call_count == 1

    def test_reanalyze_repo_with_different_uuid_formats(self, client):
        test_client, fake_service = client
        headers = {"Authorization": "Bearer faketoken"}

        # standard UUID
        u1 = str(uuid4())
        r1 = test_client.post("/api/v1/repos/re-analyze", json={"id": u1}, headers=headers)
        assert r1.status_code in (200, 201)

        # UUID without hyphens
        u2 = str(uuid4()).replace("-", "")
        r2 = test_client.post("/api/v1/repos/re-analyze", json={"id": u2}, headers=headers)
        assert r2.status_code in (200, 201)

        assert fake_service.call_count == 2

    def test_proper_service_method_calls_and_response_validation(self, client):
        test_client, fake_service = client
        repo_id = str(uuid4())
        headers = {"Authorization": "Bearer faketoken"}

        resp = test_client.post("/api/v1/repos/re-analyze", json={"id": repo_id}, headers=headers)
        assert resp.status_code in (200, 201)
        assert resp.headers["content-type"] == "application/json"

        body = resp.json()
        assert set(body.keys()) >= {"success", "message"}
        assert body["success"] is True
        assert body["message"] == "Reanalysis scheduled successfully"
        assert fake_service.call_count == 1
        u, rid = fake_service.called_with
        assert isinstance(u, UserClaims) and u.sub == "user123"
        assert rid == repo_id

    def test_reanalyze_repo_service_call_isolation(self, client):
        test_client, fake_service = client
        headers = {"Authorization": "Bearer faketoken"}

        r1 = test_client.post("/api/v1/repos/re-analyze", json={"id": "repo-1"}, headers=headers)
        assert r1.status_code in (200, 201)
        first = fake_service.called_with

        r2 = test_client.post("/api/v1/repos/re-analyze", json={"id": "repo-2"}, headers=headers)
        assert r2.status_code in (200, 201)
        second = fake_service.called_with

        assert fake_service.call_count == 2
        assert second != first
        assert second[1] == "repo-2"

    def test_reanalyze_repo_authentication_validation(self, client):
        test_client, fake_service = client
        headers = {"Authorization": "Bearer faketoken"}

        resp = test_client.post("/api/v1/repos/re-analyze", json={"id": str(uuid4())}, headers=headers)
        assert resp.status_code in (200, 201)
        user_param, _ = fake_service.called_with
        assert user_param.sub == "user123"

    def test_reanalyze_repo_response_format_consistency(self, client):
        test_client, _ = client
        headers = {"Authorization": "Bearer faketoken"}
        cases = [{"id": "string-id"}, {"id": str(uuid4())}, {"id": "123456"}]

        for payload in cases:
            resp = test_client.post("/api/v1/repos/re-analyze", json=payload, headers=headers)
            assert resp.status_code in (200, 201)
            data = resp.json()
            assert data["success"] is True
            assert data["message"] == "Reanalysis scheduled successfully"

    def test_reanalyze_repo_validation_error(self, client):
        test_client, _ = client
        headers = {"Authorization": "Bearer faketoken"}
        resp = test_client.post("/api/v1/repos/re-analyze", json={}, headers=headers)
        # mirror your analyze test’s expectation
        assert resp.status_code == 400