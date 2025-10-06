import uuid

import pytest
from devdox_ai_git.test_doubles.repo_fetcher_doubles import FakeRepoFetcher
from encryption_src.test_doubles import FakeEncryptionHelper
from fastapi import status
from fastapi.testclient import TestClient

from app.exceptions.exception_constants import GENERIC_ALREADY_EXIST
from app.main import app
from app.services.git_tokens import (
    DeleteGitLabelService,
    GetGitLabelService,
    PostGitLabelService,
)
from app.utils.auth import get_authenticated_user
from app.exceptions.local_exceptions import (
    BadRequest,
    UnauthorizedAccess,
    ValidationFailed,
)
from app.utils.constants import TOKEN_DELETED_SUCCESSFULLY, TOKEN_SAVED_SUCCESSFULLY
from models_src.dto.git_label import GitLabelResponseDTO
from models_src.test_doubles.repositories.git_label import (
    FakeGitLabelStore,
    make_fake_git_label,
)
from models_src.test_doubles.repositories.user import (
    FakeUserStore,
    make_fake_user,
)


class TestGetGitLabelsRouter:

    route_url = "/api/v1/git_tokens/"

    @pytest.fixture
    def override_git_label_service_with_data(self):
        def _override():
            store = FakeGitLabelStore()
            label = make_fake_git_label(user_id="user123", label="feature")
            store.set_fake_data([label])
            return GetGitLabelService(label_repository=store)

        app.dependency_overrides[GetGitLabelService.with_dependency] = _override
        try:
            yield
        finally:
            app.dependency_overrides.clear()

    @pytest.fixture
    def override_git_label_service_empty(self):
        def _override():
            store = FakeGitLabelStore()
            store.set_fake_data([])
            return GetGitLabelService(label_repository=store)

        app.dependency_overrides[GetGitLabelService.with_dependency] = _override
        try:
            yield
        finally:
            app.dependency_overrides.clear()

    @pytest.fixture
    def override_git_label_service_exception(self):
        def _override():
            store = FakeGitLabelStore()
            store.set_exception(store.count_by_user_id, ValueError("Simulated error"))
            return GetGitLabelService(label_repository=store)

        app.dependency_overrides[GetGitLabelService.with_dependency] = _override
        try:
            yield
        finally:
            app.dependency_overrides.clear()

    def test_get_git_labels_success(
        self, test_client, override_auth_user, override_git_label_service_with_data
    ):
        response = test_client.get(f"{self.route_url}?limit=10&offset=0")

        assert response.status_code == status.HTTP_200_OK
        body = response.json()
        assert body["success"] is True
        assert body["message"] == "Git labels retrieved successfully"
        assert body["data"]["items"][0]["label"] == "feature"
        assert body["data"]["total"] == 1

    def test_get_git_labels_empty(
        self, test_client, override_auth_user, override_git_label_service_empty
    ):
        response = test_client.get(f"{self.route_url}?limit=10&offset=0")

        assert response.status_code == status.HTTP_200_OK
        body = response.json()
        assert body["data"]["items"] == []
        assert body["data"]["total"] == 0

    def test_get_git_labels_auth_failure(
        self, test_client, override_auth_user_unauthorized
    ):
        response = test_client.get(f"{self.route_url}?limit=10&offset=0")

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_get_git_labels_service_raises(
        self,
        permissible_test_client,
        override_auth_user,
        override_git_label_service_exception,
    ):
        response = permissible_test_client.get(f"{self.route_url}?limit=10&offset=0")
        assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE


class TestGetGitLabelByLabelRouter:

    route_url = "/api/v1/git_tokens/feature"

    @pytest.fixture
    def override_git_label_service_label(self):
        def _override():
            store = FakeGitLabelStore()
            label = make_fake_git_label(user_id="user123", label="feature")
            store.set_fake_data([label])
            return GetGitLabelService(label_repository=store)

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
            return GetGitLabelService(label_repository=store)

        app.dependency_overrides[GetGitLabelService.with_dependency] = _override
        try:
            yield
        finally:
            app.dependency_overrides.clear()

    @pytest.fixture
    def override_git_label_service_label_exception(self):
        def _override():
            store = FakeGitLabelStore()
            store.total_count = 1
            store.set_exception(
                store.count_by_user_id_and_label, ValueError("Simulated error")
            )
            return GetGitLabelService(label_repository=store)

        app.dependency_overrides[GetGitLabelService.with_dependency] = _override
        try:
            yield
        finally:
            app.dependency_overrides.clear()

    def test_get_git_label_by_label_success(
        self, test_client, override_auth_user, override_git_label_service_label
    ):
        response = test_client.get(f"{self.route_url}?limit=10&offset=0")
        assert response.status_code == status.HTTP_200_OK
        body = response.json()
        assert body["success"] is True
        assert body["data"]["items"][0]["label"] == "feature"

    def test_get_git_label_by_label_empty(
        self, test_client, override_auth_user, override_git_label_service_label_empty
    ):
        response = test_client.get(f"{self.route_url}?limit=10&offset=0")
        assert response.status_code == status.HTTP_200_OK
        body = response.json()
        assert body["data"]["items"] == []

    def test_get_git_label_by_label_exception(
        self,
        permissible_test_client,
        override_auth_user,
        override_git_label_service_label_exception,
    ):
        response = permissible_test_client.get(f"{self.route_url}?limit=10&offset=0")
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
            fake_user_store.set_fake_data([user])
            fake_label_store.set_fake_data([label])
            return PostGitLabelService(
                user_repository=fake_user_store,
                label_repository=fake_label_store,
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
            
            fake_user_store.set_fake_data(fake_data=[])
            
            return PostGitLabelService(
                user_repository=fake_user_store,
                label_repository=fake_label_store,
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
            fake_user_store.set_fake_data(fake_data=[user])
            fake_label_store.set_exception(
                fake_label_store.save, BadRequest(reason=GENERIC_ALREADY_EXIST)
            )
            return PostGitLabelService(
                user_repository=fake_user_store,
                label_repository=fake_label_store,
                crypto_store=fake_crypto,
                git_manager=fake_git_manager,
            )

        app.dependency_overrides[PostGitLabelService.with_dependency] = _override
        try:
            yield
        finally:
            app.dependency_overrides.clear()

    def test_add_git_token_success(
        self, test_client, override_auth_user, override_post_git_label_service_success
    ):
        payload = {"label": "label1", "token_value": "abc123", "git_hosting": "github"}

        response = test_client.post(self.route_url, json=payload)

        assert response.status_code == status.HTTP_200_OK
        body = response.json()
        assert body["success"] is True
        assert body["message"] == TOKEN_SAVED_SUCCESSFULLY
        assert "id" in body["data"]

    def test_add_git_token_user_not_found(
        self,
        permissible_test_client,
        override_auth_user,
        override_post_git_label_service_user_not_found,
    ):
        payload = {"label": "label1", "token_value": "abc123", "git_hosting": "github"}

        response = permissible_test_client.post(self.route_url, json=payload)

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_add_git_token_duplicate_label(
        self,
        permissible_test_client,
        override_auth_user,
        override_post_git_label_service_duplicate_label,
    ):
        payload = {"label": "label1", "token_value": "abc123", "git_hosting": "github"}

        response = permissible_test_client.post(self.route_url, json=payload)

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_add_git_token_missing_token_value(
        self, permissible_test_client, override_auth_user
    ):
        payload = {"label": "label1", "token_value": " ", "git_hosting": "github"}

        response = permissible_test_client.post(self.route_url, json=payload)

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_add_git_token_unauthorized(self, permissible_test_client):
        async def _unauth_override():
            raise UnauthorizedAccess("Unauthorized")

        app.dependency_overrides[get_authenticated_user] = _unauth_override

        payload = {"label": "label1", "token_value": "abc123", "git_hosting": "github"}

        try:
            response = permissible_test_client.post(self.route_url, json=payload)
            assert response.status_code == status.HTTP_401_UNAUTHORIZED
        finally:
            app.dependency_overrides.clear()

    def test_add_git_token_validation_error(
        self, permissible_test_client, override_auth_user
    ):
        payload = {"token_value": "abc123"}

        response = permissible_test_client.post(self.route_url, json=payload)

        assert response.status_code == ValidationFailed.http_status


class TestDeleteGitLabel:

    route_url = "/api/v1/git_tokens/fb3e5e80-88ae-4b59-9e6f-088fb6e7c8e0"

    @pytest.fixture
    def override_delete_service_success(self):
        def _override():
            store = FakeGitLabelStore()
            store.set_fake_data([
                GitLabelResponseDTO(
                    id = uuid.UUID("fb3e5e80-88ae-4b59-9e6f-088fb6e7c8e0"),
                    user_id="user123",
                    label="Some git label",
                    git_hosting="github",
                )
            ])  # only the behavior matters here
            
            return DeleteGitLabelService(label_repository=store)

        app.dependency_overrides[DeleteGitLabelService.with_dependency] = _override
        try:
            yield
        finally:
            app.dependency_overrides.clear()

    @pytest.fixture
    def override_delete_service_not_found(self):
        def _override():
            store = FakeGitLabelStore()
            store.set_fake_data([])
            return DeleteGitLabelService(label_repository=store)

        app.dependency_overrides[DeleteGitLabelService.with_dependency] = _override
        try:
            yield
        finally:
            app.dependency_overrides.clear()

    def test_delete_git_label_success(
        self,
        test_client: TestClient,
        override_auth_user,
        override_delete_service_success,
    ):
        response = test_client.delete(self.route_url)

        assert response.status_code == status.HTTP_200_OK
        body = response.json()
        assert body["success"] is True
        assert body["message"] == TOKEN_DELETED_SUCCESSFULLY

    def test_delete_git_label_not_found(
        self,
        permissible_test_client: TestClient,
        override_auth_user,
        override_delete_service_not_found,
    ):
        response = permissible_test_client.delete(self.route_url)
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_delete_git_label_unauthorized(
        self, permissible_test_client: TestClient, override_auth_user_unauthorized
    ):
        response = permissible_test_client.delete(self.route_url)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
