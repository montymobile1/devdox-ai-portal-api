from unittest.mock import AsyncMock, MagicMock, patch
from urllib.parse import quote

from fastapi import status

from app.routes.git_tokens import mask_token


class TestMaskToken:
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
