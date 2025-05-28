"""
Test cases for token retrieval and creation API endpoints.
"""

from unittest.mock import patch
from urllib.parse import quote

import pytest
from fastapi import status

from app.config import GitHosting
from app.routes.git_tokens import mask_token


class TestTokenMasking:
	"""Test cases for token masking functionality."""
	
	def test_mask_token_normal_length(self):
		"""Test masking for normal length token."""
		token = "ghp_1234567890abcdef"
		result = mask_token(token)
		assert result == "ghp_************cdef"
		assert len(result) == len(token)
	
	def test_mask_token_short_token(self):
		"""Test masking for short token (8 chars or less)."""
		token = "short123"
		result = mask_token(token)
		assert result == "********"
		assert len(result) == len(token)
	
	def test_mask_token_empty_string(self):
		"""Test masking for empty token."""
		token = ""
		result = mask_token(token)
		assert result == ""
	
	def test_mask_token_none(self):
		"""Test masking for None token."""
		token = None
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


class TestAuthenticatedGetTokensEndpoint:
	"""Tests for GET /api/git_tokens with Clerk authentication."""
	
	def test_successful_token_retrieval(self, client, mock_clerk_signed_in, mock_supabase_filter):
		"""Should return tokens for the authenticated user"""
		user_payload = {"sub": "user_abc", "email": "abc@example.com", "name": "Abc"}
		token = "mock-token"
		
		mock_clerk_signed_in(payload=user_payload, token=token)
		
		response = client.get(
			"/api/v1/git_tokens/",
			headers={"Authorization": f"Bearer {token}"}
		)
		
		assert response.status_code == status.HTTP_200_OK
		data = response.json()["data"]
		assert isinstance(data, list)
		assert all("id" in token for token in data)
	
	def test_unauthenticated_request_returns_401(self, client):
		"""Should reject requests without a valid Bearer token"""
		response = client.get("/api/v1/git_tokens/")
		assert response.status_code == status.HTTP_401_UNAUTHORIZED
		assert "WWW-Authenticate" in response.headers
	
	def test_signed_in_but_supabase_raises_error(self, client, mock_clerk_signed_in, mock_supabase):
		"""Should return 503 if Supabase raises an exception"""
		user_payload = {"sub": "user_abc", "email": "abc@example.com", "name": "Abc"}
		token = "mock-token"
		
		mock_clerk_signed_in(payload=user_payload, token=token)
		
		mock_instance = mock_supabase.return_value
		mock_instance.filter.side_effect = Exception("Supabase failure")
		
		response = client.get(
			"/api/v1/git_tokens/",
			headers={"Authorization": f"Bearer {token}"}
		)
		
		assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
		assert "Service temporarily unavailable" in response.text
	
	def test_empty_token_list(self, client, mock_clerk_signed_in, mock_supabase_empty):
		"""Should return an empty list if the user has no tokens"""
		user_payload = {"sub": "user_abc", "email": "abc@example.com", "name": "Abc"}
		token = "mock-token"
		
		mock_clerk_signed_in(payload=user_payload, token=token)
		
		response = client.get(
			"/api/v1/git_tokens/",
			headers={"Authorization": f"Bearer {token}"}
		)
		
		assert response.status_code == status.HTTP_200_OK
		assert response.json()["data"] == []
	
	def test_different_user_filter_returns_empty(self, client, mock_clerk_signed_in, mock_supabase_filter):
		"""Should not return tokens that belong to another user"""
		# Clerk returns user_abc, but tokens are mocked for user_xyz
		clerk_payload = {"sub": "user_abc", "email": "abc@example.com", "name": "Abc"}
		token = "mock-token"
		
		mock_clerk_signed_in(payload=clerk_payload, token=token)
		
		def side_effect_filter(table, filters=None, **kwargs):
			if filters and filters.get("user_id") != "user_abc":
				return []
			return []  # Simulating that no tokens exist for user_abc
		
		mock_supabase_filter.filter.side_effect = side_effect_filter
		
		response = client.get(
			"/api/v1/git_tokens/",
			headers={"Authorization": f"Bearer {token}"}
		)
		
		assert response.status_code == status.HTTP_200_OK
		assert response.json()["data"] == []


@pytest.mark.skip(
	reason="This test is deprecated in favor of `TestAuthenticatedGetTokensEndpoint` and will be removed in a future release.")
class TestGetTokensEndpointOld:
	"""Test cases for GET /api/tokens endpoint."""
	
	def test_successful_token_retrieval(self, client, mock_supabase_select):
		"""Test successful retrieval of tokens."""
		# Make the request
		response = client.get("/api/v1/git_tokens/")
		
		# Verify response
		assert response.status_code == status.HTTP_200_OK
		data = response.json()
		assert len(data) == 2
		
		# Verify first token
		token1 = data[0]
		assert token1["id"] == "1"
		assert token1["label"] == "GitHub Production"
		assert token1["git_hosting"] == "github"
		# assert token1["token_value"] == "ghp_************cdef"
		assert token1["created_at"] == "2024-01-01T10:00:00Z"
		
		# Verify second token
		token2 = data[1]
		assert token2["id"] == "2"
		assert token2["label"] == "GitLab Staging"
		assert token2["git_hosting"] == "gitlab"
		# assert token2["token_value"] == "ghp_************cdef"
		
		# Verify supabase was called correctly
		mock_supabase_select.select.assert_called_once_with(
			table="git_label",
			columns="label, id, git_hosting,masked_token, created_at"
		)
	
	def test_invalid_token_data(self, client, mock_supabase_invalid_data):
		"""Test handling of invalid token data."""
		
		# Make request
		
		response = client.get("/api/v1/git_tokens/")
		
		# Verify response
		
		assert response.status_code == status.HTTP_200_OK
		
		data = response.json()
		
		# Since format_token_response returns None for invalid data, we should get an empty list
		
		assert isinstance(data, list)
		
		assert len(data) == 0
	
	def test_empty_token_list(self, client, mock_supabase):
		"""Test retrieval when no tokens exist."""
		# Mock empty database response
		mock_instance = mock_supabase.return_value
		mock_instance.select.return_value = []
		
		# Make request
		response = client.get("/api/v1/git_tokens/")
		
		# Verify response
		assert response.status_code == status.HTTP_200_OK
		data = response.json()
		assert data == []
		assert isinstance(data, list)
		
		# Verify supabase was called
		mock_instance.select.assert_called_once()
	
	def test_database_connection_error(self, client, mock_supabase):
		"""Test error handling when database connection fails."""
		# Mock database error
		mock_instance = mock_supabase.return_value
		mock_instance.select.side_effect = Exception("Database connection failed")
		
		# Make request
		response = client.get("/api/v1/git_tokens/")
		
		# Verify error response
		assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
		data = response.json()
		assert "detail" in data
		assert "Service temporarily unavailable. Please try again later." in data["detail"]
	
	def test_database_timeout_error(self, client, mock_supabase):
		"""Test error handling for database timeout."""
		# Mock timeout error
		mock_instance = mock_supabase.return_value
		mock_instance.select.side_effect = TimeoutError("Database timeout")
		
		# Make request
		response = client.get("/api/v1/git_tokens/")
		
		# Verify error response
		assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
		data = response.json()
		assert "Service temporarily unavailable. Please try again later" in data["detail"]


class TestGetTokenByLabelEndpoint:
	"""Test cases for GET /api/v1/git_tokens/{label} endpoint."""
	
	def test_get_token_by_label_success(self, client, mock_supabase_filter):
		"""Test successful retrieval of token by label."""
		
		# Make the request for a known label
		
		response = client.get("/api/v1/git_tokens/GitHub%20Production")
		
		# Verify response
		
		assert response.status_code == status.HTTP_200_OK
		
		data = response.json()
		
		assert len(data) == 1
		
		token = data[0]
		
		assert token["id"] == "1"
		
		assert token["label"] == "GitHub Production"
		
		assert token["git_hosting"] == "github"
		
		assert token["masked_token"] == "ghp_************cdef"
		
		# Verify filter was called with correct parameters
		
		mock_supabase_filter.filter.assert_called_once_with(
			
			table="git_label",
			
			filters={"label": "GitHub Production"},
			
			columns='label, id, git_hosting, masked_token, created_at'
		
		)
	
	def test_get_token_by_nonexistent_label(self, client, mock_supabase_empty):
		"""Test getting token with label that doesn't exist."""
		
		# Make request for a non-existent label
		
		response = client.get("/api/v1/git_tokens/NonExistentLabel")
		
		# Verify response
		
		assert response.status_code == status.HTTP_200_OK
		
		data = response.json()
		
		assert data == []
	
	def test_get_token_by_label_database_error(self, client, mock_supabase):
		"""Test error handling when database query fails."""
		
		# Mock database error
		
		mock_instance = mock_supabase.return_value
		
		mock_instance.filter.side_effect = Exception("Database error")
		
		# Make request
		
		response = client.get("/api/v1/git_tokens/SomeLabel")
		
		# Verify error response
		
		assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
		
		data = response.json()
		
		assert "Service temporarily unavailable" in data["detail"]
	
	def test_get_token_by_label_invalid_data(self, client, mock_supabase_invalid_label):
		"""Test handling of invalid token data when filtering by label."""
		
		mock_supabase_invalid_label.filter.return_value = None
		
		# Make request for a label that returns invalid data
		response = client.get("/api/v1/git_tokens/Missing%20Token%20Value")
		
		# Verify response
		
		assert response.status_code == status.HTTP_200_OK
		
		data = response.json()
		
		# Since format_token_response returns None for invalid data, we should get an empty list
		
		assert isinstance(data, list)
		
		assert len(data) == 0


class TestAddTokenEndpoint:
	"""Test cases for POST /api/v1/git_tokens/ endpoint."""
	
	def test_add_github_token_success(self, client, token_payload_github, mock_github_manager_success,
	                                  mock_supabase_insert_success, token_decrypted1, token_decrypted1_masked
	                                  ):
		# Make the request
		response = client.post("/api/v1/git_tokens/", json=token_payload_github)
		
		# Verify response
		assert response.status_code == status.HTTP_200_OK
		data = response.json()
		
		assert "success" in data and data["success"] is True
		assert "data" in data and "id" in data["data"]
		assert data["data"]["id"] == "999"
		
		# Verify GitHub manager was initialized with correct token
		mock_github_manager_success.assert_called_once_with(access_token=token_decrypted1)
		
		# Verify Supabase insert was called
		mock_supabase_insert_success.insert.assert_called_once()
		
		# Get the actual call args
		args, kwargs = mock_supabase_insert_success.insert.call_args
		
		# Verify the table name (first argument)
		assert args[0] == "git_label"
		
		# Verify all fields in the data dict except token_value
		data_dict = args[1]
		assert data_dict["label"] == "Test GitHub Token"
		assert data_dict["user_id"] == "user123"
		
		# Import the GitHosting enum for comparison
		from app.routes.git_tokens import GitHosting
		assert data_dict["git_hosting"] == GitHosting.GITHUB
		
		assert data_dict["masked_token"] == token_decrypted1_masked
		assert data_dict["username"] == "testuser"
		
		# Verify token_value exists but don't check its value
		assert "token_value" in data_dict
	
	def test_add_gitlab_token_success(self, token_payload_gitlab, client, mock_gitlab_manager_success,
	                                  mock_supabase_insert_success, token_gitlab_decrypted1,
	                                  token_gitlab_decrypted1_masked):
		"""Test successful creation of a GitLab token."""
		# Mock GitLab auth status and user response
		
		# mock_gitlab_manager.return_value.get_user.return_value = {"username": "testuser"}
		# mock_gitlab_manager.return_value.auth_status = True
		# Mock successful insert
		mock_supabase_insert_success.return_value = {"id": "888"}
		
		# Make the request
		response = client.post("/api/v1/git_tokens/", json=token_payload_gitlab)
		
		# Verify response
		assert response.status_code == status.HTTP_200_OK
		data = response.json()
		assert "success" in data and data["success"] is True
		assert "data" in data and "id" in data["data"]
		assert data["data"]["id"] == "999"
		
		# Verify GitLab manager was initialized with correct parameters
		mock_gitlab_manager_success.assert_called_once_with(
			base_url="https://gitlab.com",
			access_token=token_gitlab_decrypted1.replace(" ", "")
		)
		
		# Verify user data was fetched
		mock_gitlab_manager_success.return_value.get_user.assert_called_once()
		
		# Get the actual call args
		args, kwargs = mock_supabase_insert_success.insert.call_args
		
		# Verify the table name (first argument)
		assert args[0] == "git_label"
		
		# Verify all fields in the data dict except token_value
		data_dict = args[1]
		assert data_dict["label"] == "Test GitLab Token"
		assert data_dict["user_id"] == "user123"
		
		assert data_dict["git_hosting"] == GitHosting.GITLAB
		
		assert data_dict["masked_token"] == token_gitlab_decrypted1_masked
		assert data_dict["username"] == "testuser"
		
		# Verify token_value exists but don't check its value
		assert "token_value" in data_dict
	
	def test_add_github_token_authentication_failure(self, token_payload_github, client, mock_github_manager_failure):
		"""Test GitHub token creation with authentication failure."""
		# Mock GitHub authentication failure
		mock_github_manager_failure.return_value.get_user.return_value = None
		token_payload_github["token_value"] = "invalid_token"
		# Make the request
		response = client.post("/api/v1/git_tokens/", json=token_payload_github)
		
		# Verify response
		assert response.status_code == status.HTTP_400_BAD_REQUEST
		data = response.json()
		assert data["success"] is False
		assert "Failed to authenticate with GitHub" in data["message"]
		
		# Verify GitHub manager was initialized with the invalid token
		mock_github_manager_failure.assert_called_once_with(access_token="invalid_token")
		
		# Verify get_user was called
		mock_github_manager_failure.return_value.get_user.assert_called_once()
	
	def test_add_gitlab_token_authentication_failure(self, client, mock_gitlab_manager):
		"""Test GitLab token creation with authentication failure."""
		# Mock GitLab authentication failure
		mock_gitlab_manager.return_value.auth_status = False
		
		# Create payload
		payload = {
			"label": "Test GitLab Token",
			"user_id": "user123",
			"git_hosting": "gitlab",
			"token_value": "invalid_token"
		}
		
		# Make the request
		response = client.post("/api/v1/git_tokens/", json=payload)
		
		# Verify response
		assert response.status_code == status.HTTP_400_BAD_REQUEST
		data = response.json()
		assert data["success"] is False
		assert "Failed to authenticate with GitLab" in data["message"]
		
		# Verify GitLab manager was initialized with the invalid token
		mock_gitlab_manager.assert_called_once_with(
			base_url="https://gitlab.com",
			access_token="invalid_token"
		)
	
	def test_add_gitlab_token_user_fetch_failure(self, client, mock_gitlab_manager, mock_supabase_invalid_data):
		"""Test GitLab token creation with user fetch failure."""
		# Mock GitLab auth success but user fetch failure
		mock_gitlab_manager.return_value.auth_status = True
		mock_gitlab_manager.return_value.get_user.return_value = None
		
		# Create payload
		payload = {
			"label": "Test GitLab Token",
			"user_id": "user123",
			"git_hosting": "gitlab",
			"token_value": "glpat-1234567890abcdef"
		}
		
		# Make the request
		response = client.post("/api/v1/git_tokens/", json=payload)
		
		# Verify response
		assert response.status_code == status.HTTP_400_BAD_REQUEST
		data = response.json()
		assert data["success"] is False
		assert "Could not retrieve GitLab user" in data["message"]
		
		# Verify user data was attempted to be fetched
		mock_gitlab_manager.return_value.get_user.assert_called_once()
	
	def test_add_token_insert_failure(self, client, mock_github_manager, mock_supabase_insert):
		"""Test token creation with database insert failure."""
		# Mock GitHub user response
		mock_github_manager.return_value.get_user.return_value = {"login": "testuser"}
		
		# Mock failed insert
		mock_supabase_insert.return_value = None
		mock_supabase_insert.insert.return_value = None
		
		# Create payload
		payload = {
			"label": "Test GitHub Token",
			"user_id": "user123",
			"git_hosting": "github",
			"token_value": "ghp_1234567890abcdef"
		}
		
		# Make the request
		response = client.post("/api/v1/git_tokens/", json=payload)
		
		# Verify response
		assert response.status_code == status.HTTP_400_BAD_REQUEST
		data = response.json()
		assert data["success"] is False
		assert "Failed to save GitHub token" in data["message"]
		
		# Verify Supabase insert was called
		mock_supabase_insert.insert.assert_called_once()
	
	def test_add_token_unsupported_provider(self, client):
		"""Test creation with unsupported git hosting provider."""
		# Create payload with unsupported provider
		payload = {
			"label": "Test Token",
			"user_id": "user123",
			"git_hosting": "bitbucket",  # Unsupported provider
			"token_value": "token123456"
		}
		
		# Make the request
		response = client.post("/api/v1/git_tokens/", json=payload)
		
		# Verify response
		assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
		data = response.json()
		
		assert "Input should be 'gitlab' or 'github" in data["detail"][0]["msg"]
	
	def test_add_token_empty_token(self, client, mock_github_manager, mock_supabase_insert):
		"""Test creation with empty token."""
		
		# Create payload with empty token
		payload = {
			"label": "Test GitHub Token",
			"user_id": "user123",
			"git_hosting": "github",
			"token_value": ""  # Empty token
		}
		
		# Make the request
		response = client.post("/api/v1/git_tokens/", json=payload)
		
		assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


class TestDeleteToken:
	"""Test cases for delete_token endpoint"""
	
	def test_delete_token_success(self, client, mock_supabase_client, sample_token_id, sample_token_data):
		"""Test successful token deletion"""
		# Arrange
		mock_supabase_client.get_by_id.return_value = sample_token_data
		mock_supabase_client.delete.return_value = True
		
		# Act
		response = client.delete(f"/api/v1/git_tokens/{sample_token_id}")
		
		# Assert
		assert response.status_code == status.HTTP_200_OK
		response_data = response.json()
		assert response_data["success"] is True
		assert response_data["message"] == "Token deleted successfully"
		
		# Verify the correct methods were called
		mock_supabase_client.get_by_id.assert_called_once_with(
			table="git_label",
			id_value=sample_token_id
		)
		mock_supabase_client.delete.assert_called_once_with(
			table="git_label",
			id_value=sample_token_id
		)
	
	def test_delete_token_not_found(self, client, mock_supabase_client, sample_token_id):
		"""Test deletion when token doesn't exist"""
		# Arrange
		mock_supabase_client.get_by_id.return_value = None
		
		# Act
		response = client.delete(f"/api/v1/git_tokens/{sample_token_id}")
		
		# Assert
		assert response.status_code == status.HTTP_404_NOT_FOUND
		response_data = response.json()
		assert response_data["message"] == "Token not found"
		
		# Verify get_by_id was called but delete was not
		mock_supabase_client.get_by_id.assert_called_once_with(
			table="git_label",
			id_value=sample_token_id
		)
		mock_supabase_client.delete.assert_not_called()
	
	def test_delete_token_empty_response(self, client, mock_supabase_client, sample_token_id):
		"""Test deletion when get_by_id returns empty dict or falsy value"""
		# Arrange
		mock_supabase_client.get_by_id.return_value = {}
		
		# Act
		response = client.delete(f"/api/v1/git_tokens/{sample_token_id}")
		
		# Assert
		assert response.status_code == status.HTTP_404_NOT_FOUND
		response_data = response.json()
		assert response_data["message"] == "Token not found"
	
	def test_delete_token_database_error_on_get(self, client, mock_supabase_client, sample_token_id):
		"""Test handling of database error during get operation"""
		# Arrange
		mock_supabase_client.get_by_id.side_effect = Exception("Database connection failed")
		
		# Act
		response = client.delete(f"/api/v1/git_tokens/{sample_token_id}")
		
		# Assert
		assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
		response_data = response.json()
		assert response_data["detail"] == "Service temporarily unavailable. Please try again later."
	
	def test_delete_token_database_error_on_delete(self, client, mock_supabase_client, sample_token_id,
	                                               sample_token_data):
		"""Test handling of database error during delete operation"""
		# Arrange
		mock_supabase_client.get_by_id.return_value = sample_token_data
		mock_supabase_client.delete.side_effect = Exception("Delete operation failed")
		
		# Act
		response = client.delete(f"/api/v1/git_tokens/{sample_token_id}")
		
		# Assert
		assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
		response_data = response.json()
		assert response_data["detail"] == "Service temporarily unavailable. Please try again later."
	
	def test_delete_token_with_special_characters_in_id(self, client, mock_supabase_client, sample_token_data):
		"""Test deletion with special characters in token ID"""
		# Arrange
		special_id = "token-with-special-chars!@#$%"
		encoded_id = quote(special_id, safe='')
		mock_supabase_client.get_by_id.return_value = sample_token_data
		mock_supabase_client.delete.return_value = True
		
		# Act
		response = client.delete(f"/api/v1/git_tokens/{encoded_id}")
		
		# Assert
		assert response.status_code == status.HTTP_200_OK
		mock_supabase_client.get_by_id.assert_called_once_with(
			table="git_label",
			id_value=special_id
		)
	
	def test_delete_token_supabase_client_initialization_error(self, client, sample_token_id):
		"""Test handling of SupabaseClient initialization error"""
		# Arrange
		with patch('app.routes.git_tokens.SupabaseClient') as mock_client_class:  # Adjust import path
			mock_client_class.side_effect = Exception("Failed to initialize client")
			
			# Act
			response = client.delete(f"/api/v1/git_tokens/{sample_token_id}")
			
			# Assert
			assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
			response_data = response.json()
			assert response_data["detail"] == "Service temporarily unavailable. Please try again later."
	
	@pytest.mark.parametrize("token_id", [
		"simple-id",
		"123456789",
		"uuid-like-id-with-dashes",
		"very-long-token-id-with-many-characters-that-should-still-work"
	])
	def test_delete_token_various_id_formats(self, client, mock_supabase_client, sample_token_data, token_id):
		"""Test deletion with various token ID formats"""
		# Arrange
		mock_supabase_client.get_by_id.return_value = sample_token_data
		mock_supabase_client.delete.return_value = True
		
		# Act
		response = client.delete(f"/api/v1/git_tokens/{token_id}")
		
		# Assert
		assert response.status_code == status.HTTP_200_OK
		mock_supabase_client.get_by_id.assert_called_once_with(
			table="git_label",
			id_value=token_id
		)
	
	def test_delete_token_response_structure(self, client, mock_supabase_client, sample_token_id, sample_token_data):
		"""Test that the response follows the expected structure"""
		# Arrange
		mock_supabase_client.get_by_id.return_value = sample_token_data
		mock_supabase_client.delete.return_value = True
		
		# Act
		response = client.delete(f"/api/v1/git_tokens/{sample_token_id}")
		
		# Assert
		assert response.status_code == status.HTTP_200_OK
		response_data = response.json()
		
		# Check response structure (assuming APIResponse.success returns this structure)
		assert "success" in response_data
		assert "message" in response_data
		assert isinstance(response_data["success"], bool)
		assert isinstance(response_data["message"], str)


# Additional integration-style tests if needed
class TestDeleteTokenIntegration:
	"""Integration tests for delete_token endpoint"""
	
	def test_delete_token_endpoint_exists(self, client):
		"""Test that the delete endpoint exists and is accessible"""
		# This will return 404 or 503 depending on the mock, but not 405 (Method Not Allowed)
		response = client.delete("/api/v1/git_tokens/test-id")
		assert response.status_code != status.HTTP_405_METHOD_NOT_ALLOWED
