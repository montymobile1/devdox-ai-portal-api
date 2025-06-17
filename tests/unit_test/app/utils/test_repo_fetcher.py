import pytest
from types import SimpleNamespace
from app.utils.repo_fetcher import GitHubRepoFetcher, GitLabRepoFetcher, RepoFetcher
from app.config import GitHosting
from app.schemas.repo import GitRepoResponseTransformer

real_module_path = "app.utils.repo_fetcher"

class DummyAuthenticatedManager:
    def __init__(self, repos=None, repo=None, languages=None):
        self._repos = repos or []
        self._repo = repo
        self._languages = languages or []

    def get_user_repositories(self, *args, **kwargs):
        return {
            "repositories": self._repos,
            "pagination_info": {"total_count": len(self._repos)},
        }

    def get_project(self, identifier):
        return self._repo

    def get_project_languages(self, repo):
        return self._languages


@pytest.fixture
def dummy_github_repo():
    return SimpleNamespace(
        id=1,
        name="gh-repo",
        full_name="user/gh-repo",
        description="GitHub test repo",
        private=False,
        html_url="https://github.com/user/gh-repo",
        clone_url="git@github.com:user/gh-repo.git",
        ssh_url="ssh://git@github.com:user/gh-repo.git",
        default_branch="main",
        language="Python",
        size=1234,
        stargazers_count=42,
        watchers_count=100,
        forks_count=5,
        open_issues_count=2,
        created_at=None,
        updated_at=None,
        pushed_at=None,
        owner=SimpleNamespace(login="user", id=1, type="User"),
        permissions=SimpleNamespace(admin=True, push=True, pull=True),
        visibility="public",
    )


@pytest.fixture
def dummy_gitlab_project():
    return SimpleNamespace(
        id=2,
        name="gl-repo",
        description="GitLab test repo",
        default_branch="main",
        forks_count=1,
        star_count=10,
        http_url_to_repo="https://gitlab.com/user/gl-repo",
        private=False,
        visibility="private",
        statistics={"storage_size": 999},
        created_at="2023-01-01T00:00:00",
    )


class TestGitHubRepoFetcher:
    @pytest.mark.asyncio
    async def test_fetch_repo(self, monkeypatch, dummy_github_repo):
        monkeypatch.setattr(
            f"{real_module_path}.GitHubManager.authenticate",
            lambda self, token: DummyAuthenticatedManager(repos=[dummy_github_repo]),
        )
        fetcher = GitHubRepoFetcher()
        count, repos = await fetcher.fetch_user_repositories("token", 0, 10)
        assert count == 1
        assert repos[0].repo_name == dummy_github_repo.name

    @pytest.mark.asyncio
    async def test_fetch_single_repo(self, monkeypatch, dummy_github_repo):
        monkeypatch.setattr(
            f"{real_module_path}.GitHubManager.authenticate",
            lambda self, token: DummyAuthenticatedManager(repo=dummy_github_repo, languages={"Python": 100}),
        )
        fetcher = GitHubRepoFetcher()
        repo, langs = await fetcher.fetch_single_repo("token", dummy_github_repo.full_name)
        assert repo == dummy_github_repo
        assert "Python" in langs

    @pytest.mark.asyncio
    async def test_fetch_single_repo_not_found(self, monkeypatch):
        monkeypatch.setattr(
            f"{real_module_path}.GitHubManager.authenticate",
            lambda self, token: DummyAuthenticatedManager(repo=None),
        )
        fetcher = GitHubRepoFetcher()
        result = await fetcher.fetch_single_repo("token", "unknown")
        assert result is None


class TestGitLabRepoFetcher:
    @pytest.mark.asyncio
    async def test_fetch_repo(self, monkeypatch, dummy_gitlab_project):
        monkeypatch.setattr(
            f"{real_module_path}.GitLabManager.authenticate",
            lambda self, token: DummyAuthenticatedManager(repos=[dummy_gitlab_project]),
        )
        fetcher = GitLabRepoFetcher()
        count, repos = await fetcher.fetch_user_repositories("token", 0, 10)
        assert count == 1
        assert repos[0].repo_name == dummy_gitlab_project.name

    @pytest.mark.asyncio
    async def test_fetch_single_repo(self, monkeypatch, dummy_gitlab_project):
        monkeypatch.setattr(
            f"{real_module_path}.GitLabManager.authenticate",
            lambda self, token: DummyAuthenticatedManager(repo=dummy_gitlab_project, languages=["Python"]),
        )
        fetcher = GitLabRepoFetcher()
        repo, langs = await fetcher.fetch_single_repo("token", "namespace/project")
        assert repo == dummy_gitlab_project
        assert "Python" in langs

    @pytest.mark.asyncio
    async def test_fetch_single_repo_not_found(self, monkeypatch):
        monkeypatch.setattr(
            f"{real_module_path}.GitLabManager.authenticate",
            lambda self, token: DummyAuthenticatedManager(repo=None),
        )
        fetcher = GitLabRepoFetcher()
        result = await fetcher.fetch_single_repo("token", "namespace/project")
        assert result is None


class TestRepoFetcher:
    def test_get_github(self):
        fetcher = RepoFetcher()
        impl, transformer = fetcher.get(GitHosting.GITHUB)
        assert isinstance(impl, GitHubRepoFetcher)
        assert transformer.__name__ == GitRepoResponseTransformer.from_github.__name__

    def test_get_gitlab(self):
        fetcher = RepoFetcher()
        impl, transformer = fetcher.get(GitHosting.GITLAB)
        assert isinstance(impl, GitLabRepoFetcher)
        assert transformer.__name__ == GitRepoResponseTransformer.from_gitlab.__name__

    def test_get_invalid(self):
        fetcher = RepoFetcher()
        assert fetcher.get("bitbucket") is None