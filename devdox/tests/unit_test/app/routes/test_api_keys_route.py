import uuid
import pytest
from types import SimpleNamespace
from fastapi import status
from fastapi.testclient import TestClient

from app.main import app
from app.services.api_keys import RevokeApiKeyService
from app.utils.auth import UserClaims, get_authenticated_user
from app.utils.constants import API_KEY_REVOKED_SUCCESSFULLY
from app.exceptions.custom_exceptions import UnauthorizedAccess

from tests.unit_test.test_doubles.app.repository.api_key_repository_test_doubles import (
    FakeApiKeyStore,
)


@pytest.fixture(scope="module")
def client():
    return TestClient(app)


@pytest.fixture
def override_auth_user():
    async def _override():
        return UserClaims(sub="user123")

    app.dependency_overrides[get_authenticated_user] = _override
    yield
    app.dependency_overrides.clear()


@pytest.fixture
def override_auth_user_unauth():
    async def _override():
        raise UnauthorizedAccess("Invalid token")

    app.dependency_overrides[get_authenticated_user] = _override
    yield
    app.dependency_overrides.clear()


@pytest.fixture
def override_revoke_service_success():
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
def override_revoke_service_not_found():
    store = FakeApiKeyStore()  # no matching keys stored
    service = RevokeApiKeyService(api_key_store=store)

    def _override():
        return service

    app.dependency_overrides[RevokeApiKeyService.with_dependency] = _override
    yield
    app.dependency_overrides.clear()


class TestRevokeApiKeyRouter:

    route_url = "/api/v1/api-keys/"

    def test_successful_revoke(
        self, client, override_auth_user, override_revoke_service_success
    ):
        _, fake_key_id = override_revoke_service_success
        response = client.delete(f"{self.route_url}{fake_key_id}")
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["success"] is True
        assert response.json()["message"] == API_KEY_REVOKED_SUCCESSFULLY

    def test_revoke_not_found(
        self, client, override_auth_user, override_revoke_service_not_found
    ):
        response = client.delete(f"{self.route_url}{uuid.uuid4()}")
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_revoke_unauthorized(
        self, client, override_auth_user_unauth, override_revoke_service_success
    ):
        _, fake_key_id = override_revoke_service_success
        response = client.delete(f"{self.route_url}{fake_key_id}")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_invalid_uuid_path(
        self, client, override_auth_user, override_revoke_service_success
    ):
        response = client.delete(f"{self.route_url}not-a-uuid")
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
