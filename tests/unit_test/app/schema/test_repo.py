from types import SimpleNamespace

import pytest

from app.schemas.repo import GitRepoResponseTransformer

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


class TestGitRepoResponseTransformer:
    def test_from_github(self, dummy_github_repo):
        result = GitRepoResponseTransformer.from_github(dummy_github_repo)
        assert result.repo_name == dummy_github_repo.name
        assert result.html_url == dummy_github_repo.html_url
        assert result.private == dummy_github_repo.private

    def test_from_gitlab(self, dummy_gitlab_project):
        result = GitRepoResponseTransformer.from_gitlab(dummy_gitlab_project)
        assert result.repo_name == dummy_gitlab_project.name
        assert result.private is True

    def test_gitlab_missing_statistics(self, dummy_gitlab_project):
        proj = SimpleNamespace(
            **{
                k: v
                for k, v in dummy_gitlab_project.__dict__.items()
                if k != "statistics"
            }
        )
        result = GitRepoResponseTransformer.from_gitlab(proj)
        assert result.size == 0

    def test_gitlab_missing_visibility_defaults_to_public(self, dummy_gitlab_project):
        proj = SimpleNamespace(
            **{
                k: v
                for k, v in dummy_gitlab_project.__dict__.items()
                if k != "visibility"
            }
        )
        result = GitRepoResponseTransformer.from_gitlab(proj)
        assert result.private is None
