import pytest

from app.main import app
from app.utils import get_current_user
from app.utils.auth import AuthenticatedUserDTO


@pytest.fixture
def mock_authenticated_user():
	override_data = AuthenticatedUserDTO(
		id="user_abc123",
		email="user@example.com",
		name="Test User"
	)
	
	# Set the override
	app.dependency_overrides[get_current_user] = lambda: override_data
	
	# Yield control to the test
	yield override_data
	
	# Cleanup after the test
	app.dependency_overrides.pop(get_current_user, None)


@pytest.fixture
def sample_token_id():
	"""Simple sample token ID for testing"""
	return "67dff10e-d80e-4a90-a737-20afab09a321"
