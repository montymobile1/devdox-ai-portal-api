from unittest.mock import AsyncMock, MagicMock, patch
from urllib.parse import quote

import pytest
from fastapi import status

from app.routes.git_tokens import mask_token
from app.utils import constants


class TestMaskToken:
	"""Test cases for token masking functionality."""
	
	def test_mask_token_normal_length(self):
		"""Test masking for normal length token."""
		token = "ghp_1234567890abcdef"
		result = mask_token(token)
		assert result == "ghp_************cdef"
		assert len(result) == len(token)
	
	@staticmethod
	def __generate_test_data_with_ids_for_test_mask_token_short_token():
		"""Generates test data and custom IDs."""
		character = "a"
		max_characters = 9
		
		for i in range(1, max_characters):
			yield pytest.param(character * i, "*" * i, id=f"test_{i}_characters")
	
	@pytest.mark.parametrize("input_value, expected_output",
	                         __generate_test_data_with_ids_for_test_mask_token_short_token())
	def test_mask_token_short_token(self, input_value, expected_output):
		"""Test masking for short token (8 chars or less)."""
		result = mask_token(input_value)
		assert result == expected_output
	
	@pytest.mark.parametrize(
		"token",
		[None, "", " "],
		ids=["when token None", "when token empty string", "when token blank string"]
	)
	def test_mask_token_for_empty_token_forms(self, token):
		"""Test masking for invalid token."""
		result = mask_token(token)
		assert result == ""
	
	def test_mask_token_exact_eight_chars(self):
		"""Test masking for a token of exactly 8 characters."""
		token = "12345678"
		result = mask_token(token)
		assert result == "********"
		assert len(result) == 8
	
	def test_mask_token_nine_chars(self):
		"""Test masking for a token of exactly 9 characters."""
		token = "123456789"
		result = mask_token(token)
		assert result == "1234*6789"
		assert len(result) == 9


class TestGetByLabelEndpoint:
	"""Test cases for GET /api/v1/git_tokens/{label} endpoint."""
	
	@staticmethod
	def get_url(raw_label: str) -> str:
		label = quote(raw_label, safe="")
		return f"/api/v1/git_tokens/{label}"
	
	def test_get_git_label_by_label_success(self, client, mock_encryption_helper, mock_authenticated_user):
		"""Test successful retrieval of git label by label."""
		
		mock_labels = [
			MagicMock(
				id="1",
				label="GitHub Production",
				git_hosting="github",
				token_value="encrypted_token",
				username="testuser",
				masked_token=mask_token("encrypted_token"),
				created_at=MagicMock(
					isoformat=MagicMock(return_value="2024-01-01T10:00:00+00:00")
				),
				updated_at=MagicMock(
					isoformat=MagicMock(return_value="2024-01-02T10:00:00+00:00")
				),
			)
		]
		
		with patch("app.routes.git_tokens.GitLabel") as mock_git_label:
			mock_query = MagicMock()
			mock_query.order_by.return_value = mock_query
			mock_query.offset.return_value = mock_query
			mock_query.limit.return_value = mock_query
			mock_query.all = AsyncMock(return_value=mock_labels)
			
			mock_git_label.filter.return_value = mock_query
			
			response = client.get(TestGetByLabelEndpoint.get_url("GitHub Production"))
			
			assert response.status_code == status.HTTP_200_OK
			data = response.json()
			assert data["success"] is True
			assert len(data["data"]["items"]) == 1
			
			label = data["data"]["items"][0]
			assert label["id"] == "1"
			assert label["label"] == "GitHub Production"
			assert label["git_hosting"] == "github"
	
	def test_get_git_label_by_nonexistent_label(self, client, mock_authenticated_user):
		"""Test getting git label with label that doesn't exist."""
		
		with patch("app.routes.git_tokens.GitLabel") as mock_git_label:
			mock_query = MagicMock()
			mock_query.order_by.return_value = mock_query
			mock_query.offset.return_value = mock_query
			mock_query.limit.return_value = mock_query
			mock_query.all = AsyncMock(return_value=[])
			
			mock_git_label.filter.return_value = mock_query
			
			response = client.get(TestGetByLabelEndpoint.get_url("NonExistentLabel"))
			
			assert response.status_code == status.HTTP_200_OK
			data = response.json()
			assert data["success"] is True
			assert data["data"]["items"] == []
	
	def test_get_git_label_by_label_database_error(self, client, mock_authenticated_user):
		"""Test error handling when database query fails."""
		
		with patch("app.routes.git_tokens.GitLabel") as mock_git_label:
			mock_git_label.filter.side_effect = Exception("Database error")
			
			response = client.get(TestGetByLabelEndpoint.get_url("SomeLabel"))
			
			assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
			data = response.json()
			assert data["success"] is False
			assert "Service temporarily unavailable" in data["message"]


# Constants for mock data
INVALID_TOKENS = [
	("", ""),  # Empty token
	(None, ""),  # None token
	("short", "*****"),  # Very short token
]

ENCRYPTION_EXCEPTION = Exception("Decryption failed")


class TestGetByLabelEdgeCases:
	"""Edge test cases for GET /api/v1/git_tokens/{label} endpoint."""
	
	@staticmethod
	def get_url(raw_label: str) -> str:
		label = quote(raw_label, safe="")
		return f"/api/v1/git_tokens/{label}"
	
	def test_get_git_label_with_missing_token(self, client, mock_authenticated_user):
		"""Should return masked empty string for labels with missing token_value."""
		label = "GitHub Missing Token"
		
		mock_labels = [
			MagicMock(
				id="1",
				label=label,
				git_hosting="github",
				token_value=None,
				masked_token="",
				username="devuser",
				created_at=MagicMock(isoformat=MagicMock(return_value="2025-01-01T10:00:00Z")),
				updated_at=MagicMock(isoformat=MagicMock(return_value="2025-01-02T10:00:00Z")),
			)
		]
		
		with patch("app.routes.git_tokens.GitLabel") as mock_git_label, \
				patch("app.routes.git_tokens.EncryptionHelper.decrypt", return_value=""):
			mock_query = MagicMock()
			mock_query.order_by.return_value = mock_query
			mock_query.offset.return_value = mock_query
			mock_query.limit.return_value = mock_query
			mock_query.all = AsyncMock(return_value=mock_labels)
			mock_git_label.filter.return_value = mock_query
			
			response = client.get(self.get_url(label))
			assert response.status_code == status.HTTP_200_OK
			data = response.json()
			assert data["success"] is True
			assert data["data"]["items"][0]["masked_token"] == ""
	
	def test_get_git_label_with_encryption_exception(self, client, mock_authenticated_user):
		"""Should return 503 when decryption fails unexpectedly."""
		label = "GitHub Encrypted Fail"
		
		mock_labels = [
			MagicMock(
				id="1",
				label=label,
				git_hosting="github",
				token_value="corrupted_data",
				username="devuser",
				created_at=MagicMock(isoformat=MagicMock(return_value="2025-01-01T10:00:00Z")),
				updated_at=MagicMock(isoformat=MagicMock(return_value="2025-01-02T10:00:00Z")),
			)
		]
		
		with patch("app.routes.git_tokens.GitLabel") as mock_git_label, \
				patch("app.routes.git_tokens.EncryptionHelper.decrypt", side_effect=ENCRYPTION_EXCEPTION):
			mock_query = MagicMock()
			mock_query.order_by.return_value = mock_query
			mock_query.offset.return_value = mock_query
			mock_query.limit.return_value = mock_query
			mock_query.all = AsyncMock(return_value=mock_labels)
			mock_git_label.filter.return_value = mock_query
			
			response = client.get(self.get_url(label))
			assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
			data = response.json()
			assert data["success"] is False
			assert "Service temporarily unavailable" in data["message"]
	
	def test_get_git_label_with_non_ascii_label(self, client, mock_authenticated_user):
		"""Should handle non-ASCII labels (e.g., emojis, Arabic, Japanese) gracefully."""
		non_ascii_label = "🚀🔥中文ラベル"
		with patch("app.routes.git_tokens.GitLabel") as mock_git_label:
			mock_query = MagicMock()
			mock_query.order_by.return_value = mock_query
			mock_query.offset.return_value = mock_query
			mock_query.limit.return_value = mock_query
			mock_query.all = AsyncMock(return_value=[])
			mock_git_label.filter.return_value = mock_query
			
			response = client.get(self.get_url(non_ascii_label))
			assert response.status_code == status.HTTP_200_OK
			assert response.json()["data"]["items"] == []
	
	def test_get_git_label_extreme_pagination(self, client, mock_authenticated_user):
		"""Should correctly apply very large pagination offset."""
		url = self.get_url("ValidLabel") + "?limit=10&offset=10000"
		with patch("app.routes.git_tokens.GitLabel") as mock_git_label:
			mock_query = MagicMock()
			mock_query.order_by.return_value = mock_query
			mock_query.offset.return_value = mock_query
			mock_query.limit.return_value = mock_query
			mock_query.all = AsyncMock(return_value=[])
			mock_git_label.filter.return_value = mock_query
			
			response = client.get(url)
			assert response.status_code == status.HTTP_200_OK
			assert response.json()["data"]["items"] == []
	
	def test_get_git_label_filter_applies_user_id_correctly(self, client, mock_authenticated_user):
		"""Should filter GitLabel using user_id from auth DTO."""
		label = "UniqueFilterTest"
		with patch("app.routes.git_tokens.GitLabel") as mock_git_label:
			mock_query = MagicMock()
			mock_query.order_by.return_value = mock_query
			mock_query.offset.return_value = mock_query
			mock_query.limit.return_value = mock_query
			mock_query.all = AsyncMock(return_value=[])
			mock_git_label.filter.return_value = mock_query
			
			client.get(self.get_url(label))
			
			mock_git_label.filter.assert_called_once_with(
				user_id="user_abc123", label=label
			)


class TestAddGitTokenEndpoint:
	"""Test cases for POST /api/v1/git_tokens/ endpoint."""
	
	@staticmethod
	def get_url() -> str:
		return f"/api/v1/git_tokens/"
	
	def test_add_github_token_success(
			self, client, token_payload_github, mock_encryption_helper, mock_authenticated_user
	):
		"""Test successful creation of a GitHub token."""
		with patch("app.routes.git_tokens.GitHubManager") as mock_github_manager:
			# Setup successful GitHub manager
			mock_instance = MagicMock()
			mock_instance.get_user.return_value = {"login": "testuser"}
			mock_github_manager.return_value = mock_instance
			
			with patch("app.routes.git_tokens.GitLabel") as mock_git_label:
				# Setup successful GitLabel creation
				mock_created_label = MagicMock()
				mock_created_label.id = "999"
				mock_git_label.create = AsyncMock(return_value=mock_created_label)
				
				response = client.post(TestAddGitTokenEndpoint.get_url(), json=token_payload_github)
				
				assert response.status_code == status.HTTP_200_OK
				data = response.json()
				assert data["success"] is True
				assert data["data"]["id"] == "999"
				
				# Verify GitLabel.create was called
				mock_git_label.create.assert_called_once()
	
	def test_add_gitlab_token_success(
			self, client, token_payload_gitlab, mock_encryption_helper, mock_authenticated_user
	):
		"""Test successful creation of a GitLab token."""
		with patch("app.routes.git_tokens.GitLabManager") as mock_gitlab_manager:
			# Setup successful GitLab manager
			mock_instance = MagicMock()
			mock_instance.auth_status = True
			mock_instance.get_user.return_value = {"username": "testuser"}
			mock_gitlab_manager.return_value = mock_instance
			
			with patch("app.routes.git_tokens.GitLabel") as mock_git_label:
				mock_created_label = MagicMock()
				mock_created_label.id = "999"
				mock_git_label.create = AsyncMock(return_value=mock_created_label)
				
				response = client.post(TestAddGitTokenEndpoint.get_url(), json=token_payload_gitlab)
				
				assert response.status_code == status.HTTP_200_OK
				data = response.json()
				assert data["success"] is True
				assert data["data"]["id"] == "999"
	
	def test_add_github_token_authentication_failure(
			self, client, token_payload_github, mock_encryption_helper, mock_authenticated_user
	):
		"""Test GitHub token creation with authentication failure."""
		with patch("app.routes.git_tokens.GitHubManager") as mock_github_manager:
			mock_instance = MagicMock()
			mock_instance.get_user.return_value = None
			mock_github_manager.return_value = mock_instance
			
			response = client.post(TestAddGitTokenEndpoint.get_url(), json=token_payload_github)
			
			assert response.status_code == status.HTTP_400_BAD_REQUEST
			data = response.json()
			assert data["success"] is False
			assert "Failed to authenticate with GitHub" in data["message"]
	
	def test_add_gitlab_token_authentication_failure(
			self, client, token_payload_gitlab, mock_encryption_helper, mock_authenticated_user
	):
		"""Test GitLab token creation with authentication failure."""
		with patch("app.routes.git_tokens.GitLabManager") as mock_gitlab_manager:
			# Setup failed GitLab manager
			mock_instance = MagicMock()
			mock_instance.auth_status = False
			mock_gitlab_manager.return_value = mock_instance
			
			response = client.post(TestAddGitTokenEndpoint.get_url(), json=token_payload_gitlab)
			
			assert response.status_code == status.HTTP_400_BAD_REQUEST
			data = response.json()
			assert data["success"] is False
			assert "Failed to authenticate with GitLab" in data["message"]
	
	def test_add_gitlab_token_user_fetch_failure(self, client, mock_encryption_helper, mock_authenticated_user):
		"""Test GitLab token creation with user fetch failure."""
		with patch("app.routes.git_tokens.GitLabManager") as mock_gitlab_manager:
			# Mock GitLab auth success but user fetch failure
			mock_instance = MagicMock()
			mock_instance.auth_status = True
			mock_instance.get_user.return_value = None
			mock_gitlab_manager.return_value = mock_instance
			
			payload = {
				"label": "Test GitLab Token",
				"git_hosting": "gitlab",
				"token_value": "glpat-1234567890abcdef",
			}
			
			response = client.post(TestAddGitTokenEndpoint.get_url(), json=payload)
			
			assert response.status_code == status.HTTP_400_BAD_REQUEST
			data = response.json()
			assert data["success"] is False
			assert constants.GITLAB_USER_RETRIEVE_FAILED in data["message"]
			
			# Verify user data was attempted to be fetched
			mock_gitlab_manager.return_value.get_user.assert_called_once()
	
	def test_add_token_unsupported_provider(self, client, mock_encryption_helper, mock_authenticated_user):
		"""Test creation with unsupported git hosting provider."""
		payload = {
			"label": "Test Token",
			"git_hosting": "bitbucket",  # Unsupported provider
			"token_value": "token123456",
		}
		
		response = client.post(TestAddGitTokenEndpoint.get_url(), json=payload)
		
		assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
		data = response.json()
		assert data["success"] is False
		assert "Unsupported git hosting provider" in data["message"]
	
	def test_add_token_empty_token(self, client, mock_encryption_helper, mock_authenticated_user):
		"""Test creation with empty token."""
		payload = {
			"label": "Test GitHub Token",
			"git_hosting": "github",
			"token_value": "",  # Empty token
		}
		
		response = client.post(TestAddGitTokenEndpoint.get_url(), json=payload)
		
		assert response.status_code in [
			status.HTTP_422_UNPROCESSABLE_ENTITY,
			status.HTTP_400_BAD_REQUEST,
		]
	
	def test_user_id_override_security(self, client, mock_encryption_helper, mock_authenticated_user):
		"""Test that user_id is overridden with authenticated user for security."""
		with patch("app.routes.git_tokens.GitHubManager") as mock_github_manager:
			mock_instance = MagicMock()
			mock_instance.get_user.return_value = {"login": "testuser"}
			mock_github_manager.return_value = mock_instance
			
			with patch("app.routes.git_tokens.GitLabel") as mock_git_label:
				mock_created_label = MagicMock()
				mock_created_label.id = "999"
				mock_git_label.create = AsyncMock(return_value=mock_created_label)
				
				payload = {
					"label": "Test GitHub Token",
					"git_hosting": "github",
					"token_value": "ghp_1234567890abcdef",
					"user_id": "malicious-user-id",  # This should be overridden
				}
				
				response = client.post(TestAddGitTokenEndpoint.get_url(), json=payload)
				
				assert response.status_code == status.HTTP_200_OK
				
				# Verify that GitLabel.create was called with the authenticated user ID, not the provided one
				call_args = mock_git_label.create.call_args
				assert call_args.kwargs["user_id"] == mock_authenticated_user.id
	
	def test_add_gitlab_auth_status_false(self, client, mock_encryption_helper, mock_authenticated_user):
		"""Test GitLab token creation auth status failure."""
		with patch("app.routes.git_tokens.GitLabManager") as mock_gitlab_manager:
			# Mock GitLab auth success but user fetch failure
			mock_instance = MagicMock()
			mock_instance.auth_status = False
			mock_instance.get_user.return_value = None
			mock_gitlab_manager.return_value = mock_instance
			
			payload = {
				"label": "Test GitLab Token",
				"git_hosting": "gitlab",
				"token_value": "glpat-1234567890abcdef",
			}
			
			response = client.post(TestAddGitTokenEndpoint.get_url(), json=payload)
			
			assert response.status_code == status.HTTP_400_BAD_REQUEST
			data = response.json()
			assert data["success"] is False
			assert constants.GITLAB_AUTH_FAILED in data["message"]
