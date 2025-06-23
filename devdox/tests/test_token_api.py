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

class TestEdgeCases:
    """Test edge cases and boundary conditions"""

    def test_very_long_label(self, client, mock_encryption_helper, mock_user_model):
        """Test handling of very long labels"""
        long_label = "a" * 1000  # Very long label
        payload = {
            "label": long_label,
            "git_hosting": "github",
            "token_value": "ghp_1234567890abcdef",
        }

        response = client.post("/api/v1/git_tokens/", json=payload)
        print("response json ", response.json())
        # Should either succeed or return appropriate validation error
        assert response.status_code in [
            status.HTTP_201_CREATED,
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            status.HTTP_200_OK,
        ]

    def test_malformed_uuid_variations(self, client):
        """Test various malformed UUID formats"""
        malformed_uuids = [
            "not-a-uuid",
            "123",
            "123e4567-e89b-12d3-a456",  # Too short
            "123e4567-e89b-12d3-a456-426614174000-extra",  # Too long
            "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",  # Invalid characters
            # "",  # Empty string
            # "123e4567e89b12d3a456426614174000",  # Missing hyphens
        ]

        for uuid_str in malformed_uuids:
            response = client.delete(f"/api/v1/git_tokens/{uuid_str}")
            data = response.json()

            assert response.status_code == status.HTTP_400_BAD_REQUEST

            assert data["success"] is False
