"""
Test cases for git label retrieval and creation API endpoints.
Updated for Tortoise ORM implementation with current route structure.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import status

from app.main import app
from app.utils.auth import AuthenticatedUserDTO, get_current_user

SAMPLE_USER_ID = "user-123"

SAMPLE_SALT = 123


@pytest.fixture(autouse=True)
def override_current_user():
    test_user = AuthenticatedUserDTO(
        id=SAMPLE_USER_ID, email="test@example.com", name="Test User"
    )
    app.dependency_overrides[get_current_user] = lambda: test_user
    yield
    app.dependency_overrides.clear()


@pytest.fixture
def mock_user_model():
    """Mock the User model with filter().first() pattern."""
    # Patch where User is imported in the route file, not the model file
    with patch("app.routes.git_tokens.User") as mock_user_class:
        # Create mock user instance
        mock_user_instance = MagicMock()
        mock_user_instance.id = SAMPLE_USER_ID
        mock_user_instance.encryption_salt = SAMPLE_SALT
        mock_user_instance.save = AsyncMock()

        # Setup the filter().first() chain
        mock_filter = AsyncMock()
        mock_filter.first = AsyncMock(return_value=mock_user_instance)
        mock_user_class.filter = MagicMock(return_value=mock_filter)

        yield mock_user_class

