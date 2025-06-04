from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from starlette.testclient import TestClient

from app.main import app
from app.utils.auth import AuthenticatedUserDTO, get_current_user


@pytest.fixture
def mock_user() -> AuthenticatedUserDTO:
    return AuthenticatedUserDTO(
        id="user_abc123", email="user@example.com", name="Test User"
    )


@pytest.fixture
def mock_authenticated_user(mock_user):
    """
    Overrides the CurrentUser dependency globally during tests.
    """

    def _override():
        return mock_user

    app.dependency_overrides[get_current_user] = _override
    yield _override()
    app.dependency_overrides.clear()


@pytest.fixture
def client_permissive():
    with TestClient(app, raise_server_exceptions=False) as c:
        yield c


TOKEN_ENCRYPTED_1 = "gAAAAABoMFiNIvAc7WIFnoKXBjkpAVrdiTFrhlmZtG8BBwvmy1dtvfEFmupm0fcvDUo3unosoAQz5eclP2QFMnPMLG4Hj21MBt-xTdWL661JnWP-wQarnLI="


@pytest.fixture
def mock_encryption_helper():
	"""Mock EncryptionHelper for token encryption/decryption."""
	with patch("app.routes.git_tokens.EncryptionHelper") as mock_helper_class:
		# Create mock instance that will be returned when EncryptionHelper() is called
		mock_instance = MagicMock()
		mock_instance.encrypt_for_user = MagicMock(return_value=TOKEN_ENCRYPTED_1)
		mock_instance.decrypt_for_user = AsyncMock(return_value="ghp_1234567890abcdef")
		mock_instance.encrypt = MagicMock(return_value=TOKEN_ENCRYPTED_1)
		mock_instance.decrypt = MagicMock(return_value="ghp_1234567890abcdef")

		# Make the class mock return the instance when called
		mock_helper_class.return_value = mock_instance

		yield mock_helper_class
