from unittest.mock import MagicMock, patch, AsyncMock

import pytest

from app.main import app
from app.utils.auth import AuthenticatedUserDTO, get_current_user


@pytest.fixture
def mock_authenticated_user():
    override_data = AuthenticatedUserDTO(
        id="user_abc123", email="user@example.com", name="Test User"
    )

    # Set the override
    app.dependency_overrides[get_current_user] = lambda: override_data

    # Yield control to the test
    yield override_data

    # Cleanup after the test
    app.dependency_overrides.pop(get_current_user, None)


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
