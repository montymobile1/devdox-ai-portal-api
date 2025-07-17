import pytest
from starlette.testclient import TestClient

from app.exceptions.local_exceptions import UnauthorizedAccess
from app.main import app
from app.utils.auth import get_authenticated_user, UserClaims


@pytest.fixture(scope="module")
def test_client():
    yield TestClient(app)


@pytest.fixture(scope="module")
def permissible_test_client():
    """Prevents pytest from automatically handling exceptions as soon as they happen"""
    client = TestClient(app, raise_server_exceptions=False)
    yield client


@pytest.fixture
def override_auth_user():
    async def _override():
        return UserClaims(sub="user123")

    app.dependency_overrides[get_authenticated_user] = _override
    yield
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
