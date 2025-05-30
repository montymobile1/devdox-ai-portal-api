from unittest.mock import AsyncMock, MagicMock, patch
from urllib.parse import quote

import pytest
from fastapi import status


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
			assert "Could not retrieve GitLab user" in data["message"]
			
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


class TestDeleteGitLabelEndpoint:
	"""Test cases for DELETE /api/v1/git_tokens/{git_label_id} endpoint."""
	
	@staticmethod
	def get_url(git_label_id: str) -> str:
		return f"/api/v1/git_tokens/{git_label_id}"
	
	def test_delete_git_label_success(self, client, sample_token_id, mock_authenticated_user):
		"""Test successful git label deletion."""
		with patch("app.routes.git_tokens.GitLabel") as mock_git_label:
			mock_label = MagicMock()
			mock_label.delete = AsyncMock()
			mock_git_label.filter.return_value.first = AsyncMock(
				return_value=mock_label
			)
			
			response = client.delete(TestDeleteGitLabelEndpoint.get_url(sample_token_id))
			
			assert response.status_code == status.HTTP_200_OK
			data = response.json()
			assert data["success"] is True
			assert "Token deleted successfully" in data["message"]
			
			mock_label.delete.assert_called_once()
	
	def test_delete_git_label_not_found(self, client, sample_token_id, mock_authenticated_user):
		"""Test deletion when git label doesn't exist."""
		with patch("app.routes.git_tokens.GitLabel") as mock_git_label:
			mock_git_label.filter.return_value.first = AsyncMock(return_value=None)
			
			response = client.delete(TestDeleteGitLabelEndpoint.get_url(sample_token_id))
			
			assert response.status_code == status.HTTP_404_NOT_FOUND
			data = response.json()
			assert data["success"] is False
			assert "Token not found" in data["message"]
	
	def test_delete_git_label_invalid_uuid(self, client, mock_authenticated_user):
		"""Test deletion with invalid UUID format."""
		
		response = client.delete(TestDeleteGitLabelEndpoint.get_url("invalid-uuid"))
		
		assert response.status_code == status.HTTP_400_BAD_REQUEST
		data = response.json()
		assert data["success"] is False
		assert "Invalid UUID format" in data["message"]
	
	def test_delete_token_database_error_on_get(self, client, sample_token_id, mock_authenticated_user):
		"""Test handling of database error during get operation"""
		with patch("app.routes.git_tokens.GitLabel") as mock_git_label:
			mock_git_label.get = AsyncMock(
				side_effect=Exception("Database connection failed")
			)
			
			response = client.delete(TestDeleteGitLabelEndpoint.get_url(sample_token_id))
			
			assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
			data = response.json()
			assert data["success"] is False
			assert "Service temporarily unavailable" in data["message"]
	
	@pytest.mark.parametrize(
		"token_id",
		[
			"550e8400-e29b-41d4-a716-446655440000",  # Valid UUID
			"123e4567-e89b-12d3-a456-426614174000",  # Another valid UUID
		],
	)
	def test_delete_token_valid_uuid_formats(self, client, token_id, mock_authenticated_user):
		"""Test deletion with valid UUID formats"""
		with patch("app.routes.git_tokens.GitLabel") as mock_git_label:
			mock_label = MagicMock()
			mock_label.delete = AsyncMock()
			mock_git_label.filter.return_value.first = AsyncMock(
				return_value=mock_label
			)
			
			response = client.delete(TestDeleteGitLabelEndpoint.get_url(token_id))
			
			assert response.status_code == status.HTTP_200_OK
			data = response.json()
			assert data["success"] is True
