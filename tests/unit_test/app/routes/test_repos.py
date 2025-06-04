import datetime
from unittest.mock import AsyncMock, MagicMock

import pytest
from pydantic_core import ValidationError

from app.exceptions.custom_exceptions import UnauthorizedAccess
from app.exceptions.exception_constants import INVALID_BEARER_TOKEN_SCHEMA
from app.exceptions.handlers import generic_exception_handler_status_code
from app.models import Repo

# Simulated database document structure for Repo
MOCK_REPO_DOCUMENT = {
    "id": 1,
    "user_id": "user_123",
    "repo_id": "repo_gh_1",
    "repo_name": "Test Repo",
    "description": "This is a test repo",
    "html_url": "https://github.com/testuser/test-repo",
    "default_branch": "main",
    "forks_count": 10,
    "stargazers_count": 5,
    "is_private": False,
    "visibility": "public",
    "git_hosting": "github",
    "language": "Python",
    "size": 1234,
    "repo_created_at": datetime.datetime(2023, 1, 1, 0, 0, 0),
    "repo_updated_at": datetime.datetime(2023, 5, 1, 12, 0, 0),
    "token_id": "token_abc123",
    "created_at": datetime.datetime(2024, 1, 1, 0, 0, 0),
    "updated_at": datetime.datetime(2024, 1, 1, 0, 0, 0),
}


class TestGetReposRoute:

    def _build_mock_repo_query(
        self,
        count_result=0,
        all_result=None,
        simulate_partial_chain=False,
    ):
        """
        Build a mock query chain for Repo.filter().
        """

        if all_result is None:
            all_result = []

        mock_query = MagicMock()
        mock_query.count = AsyncMock(return_value=count_result)
        mock_query.all = AsyncMock(return_value=all_result)

        if simulate_partial_chain:
            mock_query.order_by.return_value = MagicMock()  # breaks offset chaining
        else:
            mock_query.order_by.return_value = mock_query
            mock_query.offset.return_value = mock_query
            mock_query.limit.return_value = mock_query

        return mock_query

    endpoint = "/api/v1/repos/"
    headers = {"Authorization": "Bearer faketoken123"}

    def test_empty_repo_list(self, monkeypatch, client, mock_authenticated_user):
        monkeypatch.setattr("app.models.Repo.filter", lambda *a, **k: self._build_mock_repo_query())
        response = client.get(self.endpoint, headers=self.headers)
        assert response.status_code == 200
        payload = response.json()
        assert payload["total_count"] == 0
        assert payload["repos"] == []

    def test_single_repo(self, monkeypatch, client, mock_authenticated_user):
        monkeypatch.setattr("app.models.Repo.filter", lambda *a, **k: self._build_mock_repo_query(1, [MOCK_REPO_DOCUMENT]))
        response = client.get(self.endpoint, headers=self.headers)
        assert response.status_code == 200
        data = response.json()
        assert data["total_count"] == 1
        assert data["repos"][0]["id"] == 1

    def test_multiple_repos(self, monkeypatch, client, mock_authenticated_user):
        repo_docs = [dict(MOCK_REPO_DOCUMENT, id=i) for i in range(5)]
        monkeypatch.setattr("app.models.Repo.filter", lambda *a, **k: self._build_mock_repo_query(5, repo_docs))
        response = client.get(self.endpoint, headers=self.headers)
        assert response.status_code == 200
        data = response.json()
        assert data["total_count"] == 5
        assert len(data["repos"]) == 5

    def test_extreme_pagination(self, monkeypatch, client, mock_authenticated_user):
        repo_docs = [dict(MOCK_REPO_DOCUMENT, id=i) for i in range(1000)]
        monkeypatch.setattr("app.models.Repo.filter", lambda *a, **k: self._build_mock_repo_query(1000, repo_docs))
        response = client.get(f"{self.endpoint}?limit=1000&offset=0", headers=self.headers)

        assert response.status_code == 200
        data = response.json()
        assert data["total_count"] == 1000
        assert len(data["repos"]) == 1000

    def test_created_at_ordering(self, monkeypatch, client, mock_authenticated_user):
        repo_docs = [
            dict(MOCK_REPO_DOCUMENT, id=i, created_at=(datetime.datetime(2025, 1, 1) - datetime.timedelta(days=i)).isoformat())
            for i in range(3)
        ]
        monkeypatch.setattr("app.models.Repo.filter", lambda *a, **k: self._build_mock_repo_query(3, repo_docs))
        response = client.get(self.endpoint, headers=self.headers)
        assert response.status_code == 200
        data = response.json()
        assert data["total_count"] == 3
        assert len(data["repos"]) == 3

    def test_handles_database_error(self, monkeypatch, client_permissive, mock_authenticated_user):

        expected_exception = Exception("DB failure")

        monkeypatch.setattr(Repo, "filter", lambda *a, **kw: (_ for _ in ()).throw(expected_exception))
        response = client_permissive.get(self.endpoint, headers=self.headers)
        assert response.status_code == generic_exception_handler_status_code
        json_data = response.json()
        assert json_data["debug"]["exception"] == type(expected_exception).__name__
        assert json_data["debug"]["str"] == str(expected_exception)

    def test_all_returns_non_list(self, monkeypatch, client_permissive, mock_authenticated_user):
        monkeypatch.setattr(Repo, "filter", lambda *a, **kw: self._build_mock_repo_query(1, "not-a-list"))
        response = client_permissive.get(self.endpoint, headers=self.headers)
        assert response.status_code == generic_exception_handler_status_code

        json_data = response.json()
        assert json_data["debug"]["exception"] == ValidationError.__name__

    def test_broken_query_chain(self, monkeypatch, client_permissive, mock_authenticated_user):
        mock_query = self._build_mock_repo_query(2, [MOCK_REPO_DOCUMENT], simulate_partial_chain=True)
        monkeypatch.setattr(Repo, "filter", lambda *a, **k: mock_query)

        response = client_permissive.get(self.endpoint, headers=self.headers)
        assert response.status_code == generic_exception_handler_status_code
        json_data = response.json()
        assert json_data["debug"]["exception"] == TypeError.__name__

    def test_invalid_repo_schema(self, monkeypatch, client_permissive, mock_authenticated_user):
        bad_doc = dict(MOCK_REPO_DOCUMENT)
        del bad_doc["repo_name"]  # Required field

        monkeypatch.setattr(Repo, "filter", lambda *a, **k: self._build_mock_repo_query(1, [bad_doc]))
        response = client_permissive.get(self.endpoint, headers=self.headers)
        assert response.status_code == generic_exception_handler_status_code

        json_data = response.json()
        assert json_data["debug"]["exception"] == ValidationError.__name__

    @pytest.mark.parametrize("input_header", [None, "Bearer", "BearerInvalid", "Token faketoken123"])
    def test_invalid_authorization_header(self, monkeypatch, client, input_header):
        monkeypatch.setattr("app.models.Repo.filter", lambda *a, **k: self._build_mock_repo_query())

        h = {"Authorization": input_header} if input_header else {}
        response = client.get(self.endpoint, headers=h)
        assert response.status_code in [401, 403]

        json_data = response.json()
        assert json_data["debug"]["exception"].lower() == UnauthorizedAccess.__name__.lower()
        assert INVALID_BEARER_TOKEN_SCHEMA in json_data["debug"]["str"]
