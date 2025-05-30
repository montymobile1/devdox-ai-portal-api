from unittest.mock import AsyncMock, MagicMock, patch
from urllib.parse import quote

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
