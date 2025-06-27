import pytest
from fastapi import status
from fastapi.testclient import TestClient

from app.exceptions.exception_constants import GENERIC_ALREADY_EXIST
from app.main import app
from app.utils.auth import UserClaims
from app.services.git_tokens_service import GetGitLabelService, PostGitLabelService
from app.utils.auth import get_authenticated_user
from app.exceptions.custom_exceptions import BadRequest, UnauthorizedAccess
from app.utils.constants import TOKEN_SAVED_SUCCESSFULLY
from tests.unit_test.test_doubles.app.repository.get_label_repository_doubles import (
    FakeGitLabelStore,
    make_fake_git_label,
)
from tests.unit_test.test_doubles.app.repository.user_repository_doubles import (
    FakeUserStore,
    make_fake_user,
)
from tests.unit_test.test_doubles.app.utils.encryption_doubles import (
    FakeEncryptionHelper,
)
from tests.unit_test.test_doubles.app.utils.repo_fetcher_doubles import (
    FakeGitHubRepoFetcher,
    FakeRepoFetcher,
)


@pytest.fixture(scope="module")
def t_client():
    client = TestClient(app)
    yield client


@pytest.fixture(scope="module")
def per_t_client():
    client = TestClient(app, raise_server_exceptions=False)
    yield client


@pytest.fixture
def override_auth_user():
    async def _override():
        return UserClaims(sub="user123")

    app.dependency_overrides[get_authenticated_user] = _override
    try:
        yield
    finally:
        app.dependency_overrides.clear()


@pytest.fixture
def override_auth_user_unauthorized():
    async def _override():
        raise UnauthorizedAccess("Invalid token")

    app.dependency_overrides[get_authenticated_user] = _override
    try:
        yield
    finally:
        app.dependency_overrides.clear()


class TestGetGitLabelsRouter:

    route_url = "/api/v1/git_tokens/"

    @pytest.fixture
    def override_git_label_service_with_data(self):
        def _override():
            store = FakeGitLabelStore()
            label = make_fake_git_label(user_id="user123", label="feature")
            store.set_fake_data([label], total_count=1)
            return GetGitLabelService(label_store=store)

        app.dependency_overrides[GetGitLabelService.with_dependency] = _override
        try:
            yield
        finally:
            app.dependency_overrides.clear()

    @pytest.fixture
    def override_git_label_service_empty(self):
        def _override():
            store = FakeGitLabelStore()
            store.set_fake_data([], total_count=0)
            return GetGitLabelService(label_store=store)

        app.dependency_overrides[GetGitLabelService.with_dependency] = _override
        try:
            yield
        finally:
            app.dependency_overrides.clear()

    @pytest.fixture
    def override_git_label_service_exception(self):
        def _override():
            store = FakeGitLabelStore()
            store.set_exception("count_by_user_id", ValueError("Simulated error"))
            return GetGitLabelService(label_store=store)

        app.dependency_overrides[GetGitLabelService.with_dependency] = _override
        try:
            yield
        finally:
            app.dependency_overrides.clear()

    @pytest.fixture
    def override_auth_user_unauthorized(self):
        async def _override():
            raise UnauthorizedAccess("Invalid token")

        app.dependency_overrides[get_authenticated_user] = _override
        try:
            yield
        finally:
            app.dependency_overrides.clear()

    def test_get_git_labels_success(
        self, t_client, override_auth_user, override_git_label_service_with_data
    ):
        response = t_client.get(f"{self.route_url}?limit=10&offset=0")

        assert response.status_code == status.HTTP_200_OK
        body = response.json()
        assert body["success"] is True
        assert body["message"] == "Git labels retrieved successfully"
        assert body["data"]["items"][0]["label"] == "feature"
        assert body["data"]["total"] == 1

    def test_get_git_labels_empty(
        self, t_client, override_auth_user, override_git_label_service_empty
    ):
        response = t_client.get(f"{self.route_url}?limit=10&offset=0")

        assert response.status_code == status.HTTP_200_OK
        body = response.json()
        assert body["data"]["items"] == []
        assert body["data"]["total"] == 0

    def test_get_git_labels_auth_failure(
        self, t_client, override_auth_user_unauthorized
    ):
        response = t_client.get(f"{self.route_url}?limit=10&offset=0")

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_get_git_labels_service_raises(
        self, per_t_client, override_auth_user, override_git_label_service_exception
    ):
        response = per_t_client.get(f"{self.route_url}?limit=10&offset=0")
        assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE


class TestGetGitLabelByLabelRouter:

    route_url = "/api/v1/git_tokens/feature"

    @pytest.fixture
    def override_git_label_service_label(self):
        def _override():
            store = FakeGitLabelStore()
            label = make_fake_git_label(user_id="user123", label="feature")
            store.set_fake_data([label])
            return GetGitLabelService(label_store=store)

        app.dependency_overrides[GetGitLabelService.with_dependency] = _override
        try:
            yield
        finally:
            app.dependency_overrides.clear()

    @pytest.fixture
    def override_git_label_service_label_empty(self):
        def _override():
            store = FakeGitLabelStore()
            store.set_fake_data([])
            return GetGitLabelService(label_store=store)

        app.dependency_overrides[GetGitLabelService.with_dependency] = _override
        try:
            yield
        finally:
            app.dependency_overrides.clear()

    @pytest.fixture
    def override_git_label_service_label_exception(self):
        def _override():
            store = FakeGitLabelStore()
            store.set_exception(
                "get_by_user_id_and_label", ValueError("Simulated error")
            )
            return GetGitLabelService(label_store=store)

        app.dependency_overrides[GetGitLabelService.with_dependency] = _override
        try:
            yield
        finally:
            app.dependency_overrides.clear()

    def test_get_git_label_by_label_success(
        self, t_client, override_auth_user, override_git_label_service_label
    ):
        response = t_client.get(f"{self.route_url}?limit=10&offset=0")
        assert response.status_code == status.HTTP_200_OK
        body = response.json()
        assert body["success"] is True
        assert body["data"]["items"][0]["label"] == "feature"

    def test_get_git_label_by_label_empty(
        self, t_client, override_auth_user, override_git_label_service_label_empty
    ):
        response = t_client.get(f"{self.route_url}?limit=10&offset=0")
        assert response.status_code == status.HTTP_200_OK
        body = response.json()
        assert body["data"]["items"] == []

    def test_get_git_label_by_label_exception(
        self,
        per_t_client,
        override_auth_user,
        override_git_label_service_label_exception,
    ):
        response = per_t_client.get(f"{self.route_url}?limit=10&offset=0")
        assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE


class TestPostGitLabelRouter__AddGitToken:
    route_url = "/api/v1/git_tokens/"

    @pytest.fixture
    def override_post_git_label_service_success(self):
        def _override():
            fake_user_store = FakeUserStore()
            fake_crypto = FakeEncryptionHelper()
            fake_git_manager = FakeRepoFetcher()
            fake_label_store = FakeGitLabelStore()
            user = make_fake_user(user_id="user123")
            label = make_fake_git_label(label="label1", user_id="user123")
            fake_user_store.set_fake_user(user)
            fake_label_store.set_fake_data([label])
            return PostGitLabelService(
                user_store=fake_user_store,
                label_store=fake_label_store,
                crypto_store=fake_crypto,
                git_manager=fake_git_manager,
            )

        app.dependency_overrides[PostGitLabelService.with_dependency] = _override
        try:
            yield
        finally:
            app.dependency_overrides.clear()

    @pytest.fixture
    def override_post_git_label_service_user_not_found(self):
        def _override():
            fake_user_store = FakeUserStore()
            fake_crypto = FakeEncryptionHelper()
            fake_git_manager = FakeRepoFetcher()
            fake_label_store = FakeGitLabelStore()
            fake_user_store.set_fake_user(None)
            return PostGitLabelService(
                user_store=fake_user_store,
                label_store=fake_label_store,
                crypto_store=fake_crypto,
                git_manager=fake_git_manager,
            )

        app.dependency_overrides[PostGitLabelService.with_dependency] = _override
        try:
            yield
        finally:
            app.dependency_overrides.clear()

    @pytest.fixture
    def override_post_git_label_service_duplicate_label(self):
        def _override():
            fake_user_store = FakeUserStore()
            fake_crypto = FakeEncryptionHelper()
            fake_git_manager = FakeRepoFetcher()
            fake_label_store = FakeGitLabelStore()
            user = make_fake_user(user_id="user123")
            fake_user_store.set_fake_user(user)
            fake_label_store.set_exception(
                "create_new", BadRequest(reason=GENERIC_ALREADY_EXIST)
            )
            return PostGitLabelService(
                user_store=fake_user_store,
                label_store=fake_label_store,
                crypto_store=fake_crypto,
                git_manager=fake_git_manager,
            )

        app.dependency_overrides[PostGitLabelService.with_dependency] = _override
        try:
            yield
        finally:
            app.dependency_overrides.clear()

    def test_add_git_token_success(
        self, t_client, override_auth_user, override_post_git_label_service_success
    ):
        payload = {"label": "label1", "token_value": "abc123", "git_hosting": "GITHUB"}

        response = t_client.post(self.route_url, json=payload)

        assert response.status_code == status.HTTP_200_OK
        body = response.json()
        assert body["success"] is True
        assert body["message"] == TOKEN_SAVED_SUCCESSFULLY
        assert "id" in body["data"]

    def test_add_git_token_user_not_found(
        self,
        per_t_client,
        override_auth_user,
        override_post_git_label_service_user_not_found,
    ):
        payload = {"label": "label1", "token_value": "abc123", "git_hosting": "GITHUB"}

        response = per_t_client.post(self.route_url, json=payload)

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_add_git_token_duplicate_label(
        self,
        per_t_client,
        override_auth_user,
        override_post_git_label_service_duplicate_label,
    ):
        payload = {"label": "label1", "token_value": "abc123", "git_hosting": "GITHUB"}

        response = per_t_client.post(self.route_url, json=payload)

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_add_git_token_missing_token_value(self, per_t_client, override_auth_user):
        payload = {"label": "label1", "token_value": " ", "git_hosting": "GITHUB"}

        response = per_t_client.post(self.route_url, json=payload)

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_add_git_token_unauthorized(self, per_t_client):
        async def _unauth_override():
            raise UnauthorizedAccess("Unauthorized")

        app.dependency_overrides[get_authenticated_user] = _unauth_override

        payload = {"label": "label1", "token_value": "abc123", "git_hosting": "GITHUB"}

        try:
            response = per_t_client.post(self.route_url, json=payload)
            assert response.status_code == status.HTTP_401_UNAUTHORIZED
        finally:
            app.dependency_overrides.clear()

    def test_add_git_token_validation_error(self, per_t_client, override_auth_user):
        payload = {"token_value": "abc123"}

        response = per_t_client.post(self.route_url, json=payload)

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
