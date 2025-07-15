import datetime
import uuid
import pytest
from types import SimpleNamespace
from fastapi import status

from app.exceptions.custom_exceptions import ValidationFailed
from app.main import app
from app.schemas.api_key import APIKeyPublicResponse
from app.services.api_keys import GetApiKeyService, RevokeApiKeyService
from app.utils.auth import UserClaims
from app.utils.constants import API_KEY_REVOKED_SUCCESSFULLY, GENERIC_SUCCESS

from tests.unit_test.test_doubles.app.repository.api_key_repository_test_doubles import (
    FakeApiKeyStore,
)


class TestRevokeApiKeyRouter:

    route_url = "/api/v1/api-keys/"

    @pytest.fixture
    def override_revoke_service_success(self):
        store = FakeApiKeyStore()
        fake_key_id = uuid.uuid4()
        store.stored_keys.append(
            SimpleNamespace(id=fake_key_id, user_id="user123", is_active=True)
        )
        service = RevokeApiKeyService(api_key_store=store)

        def _override():
            return service

        app.dependency_overrides[RevokeApiKeyService.with_dependency] = _override
        yield store, fake_key_id
        app.dependency_overrides.clear()

    @pytest.fixture
    def override_revoke_service_not_found(self):
        store = FakeApiKeyStore()  # no matching keys stored
        service = RevokeApiKeyService(api_key_store=store)

        def _override():
            return service

        app.dependency_overrides[RevokeApiKeyService.with_dependency] = _override
        yield
        app.dependency_overrides.clear()

    def test_successful_revoke(
        self, test_client, override_auth_user, override_revoke_service_success
    ):
        _, fake_key_id = override_revoke_service_success
        response = test_client.delete(f"{self.route_url}{fake_key_id}")
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["success"] is True
        assert response.json()["message"] == API_KEY_REVOKED_SUCCESSFULLY

    def test_revoke_not_found(
        self, test_client, override_auth_user, override_revoke_service_not_found
    ):
        response = test_client.delete(f"{self.route_url}{uuid.uuid4()}")
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_revoke_unauthorized(
        self,
        test_client,
        override_auth_user_unauthorized,
        override_revoke_service_success,
    ):
        _, fake_key_id = override_revoke_service_success
        response = test_client.delete(f"{self.route_url}{fake_key_id}")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_invalid_uuid_path(
        self, test_client, override_auth_user, override_revoke_service_success
    ):
        response = test_client.delete(f"{self.route_url}not-a-uuid")
        assert response.status_code == ValidationFailed.http_status


class FakeGetApiKeyService:
    def __init__(self):
        self.return_keys = []
        self.should_raise = False
        self.received_calls = []

    def set_keys(self, keys):
        self.return_keys = keys

    def set_exception(self):
        self.should_raise = True

    async def get_api_keys_by_user(self, user_claims: UserClaims):
        self.received_calls.append(user_claims.sub)
        if self.should_raise:
            raise RuntimeError("Service failure")
        return self.return_keys


class TestGetApiKeyRouter:

    route_url = "/api/v1/api-keys/"

    @pytest.fixture
    def override_get_service_success(self):
        def _override():
            service = FakeGetApiKeyService()
            service.set_keys(
                [
                    APIKeyPublicResponse(
                        user_id="user123",
                        masked_api_key="****abcd",
                        created_at=datetime.datetime.now(datetime.UTC),
                        last_used_at=datetime.datetime.now(datetime.UTC),
                    )
                ]
            )
            return service

        app.dependency_overrides[GetApiKeyService.with_dependency] = _override

        try:
            yield
        finally:
            app.dependency_overrides.clear()

    @pytest.fixture
    def override_get_service_empty(self):
        def _override():
            return FakeGetApiKeyService()  # returns empty list by default

        app.dependency_overrides[GetApiKeyService.with_dependency] = _override

        try:
            yield
        finally:
            app.dependency_overrides.clear()

    @pytest.fixture
    def override_get_service_failure(self):
        def _override():
            service = FakeGetApiKeyService()
            service.set_exception()
            return service

        app.dependency_overrides[GetApiKeyService.with_dependency] = _override
        try:
            yield
        finally:
            app.dependency_overrides.clear()

    def test_successful_get_keys(
        self, test_client, override_auth_user, override_get_service_success
    ):
        response = test_client.get(self.route_url)
        assert response.status_code == status.HTTP_200_OK
        body = response.json()
        assert body["success"] is True
        assert body["message"] == GENERIC_SUCCESS
        assert "data" in body
        assert isinstance(body["data"], list)
        assert body["data"][0]["user_id"] == "user123"

    def test_empty_keys_list(
        self, test_client, override_auth_user, override_get_service_empty
    ):
        response = test_client.get(self.route_url)
        assert response.status_code == status.HTTP_200_OK
        body = response.json()
        assert body["success"] is True
        assert body["message"] == GENERIC_SUCCESS
        assert body["data"] == []

    def test_service_failure_raises_503(
        self, permissible_test_client, override_auth_user, override_get_service_failure
    ):
        response = permissible_test_client.get(self.route_url)
        assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE

    def test_unauthorized_access(
        self, test_client, override_auth_user_unauthorized, override_get_service_success
    ):
        response = test_client.get(self.route_url)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
