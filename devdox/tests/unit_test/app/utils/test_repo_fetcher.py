from types import SimpleNamespace

from app.config import GitHosting
from app.schemas.repo import (
    GitHubRepoResponseTransformer,
    GitLabRepoResponseTransformer,
)
from app.utils.repo_fetcher import GitHubRepoFetcher, GitLabRepoFetcher, RepoFetcher

path_to_actual_module = "app.utils.repo_fetcher"


class TestGitHubRepoFetcher:
    def test_fetch_user_repositories_returns_expected_dict(self, monkeypatch):
        mock_auth = SimpleNamespace(
            get_user_repositories=lambda page, per_page: {
                "pagination_info": {"total_count": 2},
                "repositories": ["repo1", "repo2"],
            }
        )
        monkeypatch.setattr(
            f"{path_to_actual_module}.GitHubManager.authenticate",
            lambda self, token: mock_auth,
        )

        fetcher = GitHubRepoFetcher("https://fake.api")
        result = fetcher.fetch_user_repositories("token123", 0, 2)
        assert result == {"data_count": 2, "data": ["repo1", "repo2"]}

    def test_fetch_single_repo_success(self, monkeypatch):
        repo = SimpleNamespace(id=1)
        mock_auth = SimpleNamespace(
            get_project=lambda full_name: repo,
            get_project_languages=lambda r: {"Python": 50, "Go": 50},
        )
        monkeypatch.setattr(
            f"{path_to_actual_module}.GitHubManager.authenticate",
            lambda self, token: mock_auth,
        )

        fetcher = GitHubRepoFetcher()
        result = fetcher.fetch_single_repo("token123", "some/repo")
        assert result[0] is repo
        assert set(result[1]) == {"Python", "Go"}

    def test_fetch_single_repo_not_found(self, monkeypatch):
        mock_auth = SimpleNamespace(get_project=lambda full_name: None)
        monkeypatch.setattr(
            f"{path_to_actual_module}.GitHubManager.authenticate",
            lambda self, token: mock_auth,
        )

        fetcher = GitHubRepoFetcher()
        assert fetcher.fetch_single_repo("token123", "missing") is None


class TestGitLabRepoFetcher:
    def test_fetch_user_repositories_returns_expected_dict(self, monkeypatch):
        mock_auth = SimpleNamespace(
            get_user_repositories=lambda page, per_page: {
                "pagination_info": {"total_count": 3},
                "repositories": ["lab1", "lab2", "lab3"],
            }
        )
        monkeypatch.setattr(
            f"{path_to_actual_module}.GitLabManager.authenticate",
            lambda self, token: mock_auth,
        )

        fetcher = GitLabRepoFetcher("https://fake.gitlab")
        result = fetcher.fetch_user_repositories("token123", 1, 3)
        assert result == {"data_count": 3, "data": ["lab1", "lab2", "lab3"]}

    def test_fetch_single_repo_success(self, monkeypatch):
        repo = SimpleNamespace(id=2)
        mock_auth = SimpleNamespace(
            get_project=lambda name: repo, get_project_languages=lambda r: {"Java": 100}
        )
        monkeypatch.setattr(
            f"{path_to_actual_module}.GitLabManager.authenticate",
            lambda self, token: mock_auth,
        )

        fetcher = GitLabRepoFetcher()
        result = fetcher.fetch_single_repo("token123", "some/project")
        assert result[0] is repo
        assert result[1] == ["Java"]

    def test_fetch_single_repo_not_found(self, monkeypatch):
        mock_auth = SimpleNamespace(get_project=lambda full_name: None)
        monkeypatch.setattr(
            f"{path_to_actual_module}.GitLabManager.authenticate",
            lambda self, token: mock_auth,
        )

        fetcher = GitLabRepoFetcher()
        assert fetcher.fetch_single_repo("token123", "invalid") is None


class TestRepoFetcher:
    def test_get_github_returns_expected_types(self):
        fetcher, transformer = RepoFetcher().get_components(GitHosting.GITHUB)
        assert isinstance(fetcher, GitHubRepoFetcher)
        assert isinstance(transformer, GitHubRepoResponseTransformer)

    def test_get_gitlab_returns_expected_types(self):
        fetcher, transformer = RepoFetcher().get_components(GitHosting.GITLAB)
        assert isinstance(fetcher, GitLabRepoFetcher)
        assert isinstance(transformer, GitLabRepoResponseTransformer)

    def test_get_invalid_provider_returns_none(self):

        fetcher, transformer = RepoFetcher().get_components("BITBUCKET")

        assert fetcher is None
        assert transformer is None
