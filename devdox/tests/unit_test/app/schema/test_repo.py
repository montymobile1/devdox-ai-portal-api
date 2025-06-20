from datetime import datetime
from types import SimpleNamespace

import pytest

from app.schemas.repo import GitHubRepoResponseTransformer, GitLabRepoResponseTransformer, GitRepoResponse


class TestGitLabRepoResponseTransformer:
    def test_derive_storage_size_with_none(self):
        assert GitLabRepoResponseTransformer.derive_storage_size(None) is None

    def test_derive_storage_size_with_value(self):
        statistics = {"storage_size": 1234}
        assert GitLabRepoResponseTransformer.derive_storage_size(statistics) == 1234

    def test_derived_private_field_with_none(self):
        assert GitLabRepoResponseTransformer.derived_private_field(None) is None

    @pytest.mark.parametrize("visibility,expected", [
        ("private", True),
        ("internal", True),
        ("public", False),
        ("", None)
    ])
    def test_derived_private_field_various_inputs(self, visibility, expected):
        assert GitLabRepoResponseTransformer.derived_private_field(visibility) == expected

    def test_transform_project_to_dict_basic(self):
        now = datetime.utcnow()
        project = SimpleNamespace(
            id=1,
            name="project",
            description="desc",
            default_branch="main",
            forks_count=10,
            visibility="public",
            created_at=now,
            star_count=5,
            http_url_to_repo="http://example.com/repo",
            path_with_namespace="repo",
            statistics={"storage_size": 2000},
        )
        result = GitLabRepoResponseTransformer.transform_project_to_dict(project)
        assert result["name"] == "project"
        assert result["statistics"]["storage_size"] == 2000

    def test_from_gitlab_none_returns_none(self):
        assert GitLabRepoResponseTransformer.from_gitlab(None) is None

    def test_from_gitlab_dict_returns_expected_schema(self):
        data = {
            "id": 42,
            "name": "test-repo",
            "description": "test desc",
            "default_branch": "main",
            "forks_count": 2,
            "star_count": 3,
            "http_url_to_repo": "http://example.com",
            "path_with_namespace": "repo",
            "visibility": "internal",
            "created_at": datetime.utcnow(),
            "statistics": {"storage_size": 512},
        }
        response = GitLabRepoResponseTransformer.from_gitlab(data)
        assert isinstance(response, GitRepoResponse)
        assert response.private is True
        assert response.size == 512

    @pytest.mark.parametrize("invalid_input", [123, 3.14, ["list"], object()])
    def test_from_gitlab_with_invalid_type_raises(self, invalid_input):
        with pytest.raises(TypeError):
            GitLabRepoResponseTransformer.from_gitlab(invalid_input)

    def test_gitlab_statistics_not_dict(self):
        project = SimpleNamespace(
            id=1, name="x", default_branch="main", forks_count=0,
            visibility="public", created_at=None, star_count=0,
            http_url_to_repo="http://url", statistics="not-a-dict"
        )
        with pytest.raises(AttributeError):
            GitLabRepoResponseTransformer.from_gitlab(project)



class TestGitHubRepoResponseTransformer:
    def test_transform_repository_to_dict(self):
        now = datetime.utcnow()
        repo = SimpleNamespace(
            id=1,
            name="repo",
            description="description",
            default_branch="main",
            forks_count=10,
            stargazers_count=100,
            html_url="http://github.com/repo",
            full_name="repo",
            private=True,
            visibility="private",
            size=2048,
            created_at=now
        )
        result = GitHubRepoResponseTransformer.transform_repository_to_dict(repo)
        assert result["name"] == "repo"
        assert result["private"] is True

    def test_from_github_none_returns_none(self):
        assert GitHubRepoResponseTransformer.from_github(None) is None

    def test_from_github_dict_returns_expected_schema(self):
        now = datetime.utcnow()
        data = {
            "id": 99,
            "name": "gh-repo",
            "description": "GitHub repo",
            "default_branch": "main",
            "forks_count": 5,
            "stargazers_count": 50,
            "html_url": "http://github.com/repo",
            "full_name": "repo",
            "private": False,
            "visibility": "public",
            "size": 100,
            "repo_created_at": now,
        }
        response = GitHubRepoResponseTransformer.from_github(data)
        assert isinstance(response, GitRepoResponse)
        assert response.repo_name == "gh-repo"
        assert response.private is False

    def test_from_github_with_invalid_type_raises(self):
        with pytest.raises(TypeError):
            GitHubRepoResponseTransformer.from_github(123)
