from typing import Any, Callable, Protocol

from github.Repository import Repository
from gitlab.v4.objects import Project

from app.config import GitHosting
from app.schemas.repo import (
    GitHubRepoResponseTransformer,
    GitLabRepoResponseTransformer,
    GitRepoResponse,
)
from app.utils.git_managers import GitHubManager, GitLabManager


class IRepoFetcher(Protocol):
    def fetch_user_repositories(
        self, token: str, offset: int, limit: int
    ) -> dict[str, Any]: ...

    def fetch_single_repo(self, token: str, full_name_or_id: str | int): ...


class GitHubRepoFetcher(IRepoFetcher):
    def __init__(self, base_url: str = GitHubManager.default_base_url):
        self.manager = GitHubManager(base_url)

    def fetch_user_repositories(
        self, token: str, offset: int, limit: int
    ) -> dict[str, Any]:
        authenticated_github_manager = self.manager.authenticate(token)
        result = authenticated_github_manager.get_user_repositories(
            page=offset + 1, per_page=limit
        )

        return {
            "data_count": result["pagination_info"]["total_count"],
            "data": result["repositories"],
        }

    def fetch_single_repo(
        self, token: str, relative_path_or_id: str | int
    ) -> tuple[Any, list[Any]] | None:

        authenticated_github_manager = self.manager.authenticate(token)

        repository = authenticated_github_manager.get_project(relative_path_or_id)

        if not repository:
            return None

        repository_languages = authenticated_github_manager.get_project_languages(
            repository
        )

        return repository, [*repository_languages]


class GitLabRepoFetcher(IRepoFetcher):
    def __init__(self, base_url: str = GitLabManager.default_base_url):
        self.manager = GitLabManager(base_url)

    def fetch_user_repositories(
        self, token: str, offset: int, limit: int
    ) -> dict[str, Any]:
        authenticated_gitlab_manager = self.manager.authenticate(token)
        result = authenticated_gitlab_manager.get_user_repositories(
            page=offset + 1, per_page=limit
        )

        return {
            "data_count": result["pagination_info"]["total_count"],
            "data": result["repositories"],
        }

    def fetch_single_repo(
        self, token: str, relative_path: str
    ) -> tuple[Project, list[str]] | None:
        # full_name can be ID or 'namespace/project'
        authenticated_gitlab_manager = self.manager.authenticate(token)
        repository = authenticated_gitlab_manager.get_project(relative_path)

        if not repository:
            return None

        repository_languages = authenticated_gitlab_manager.get_project_languages(
            repository
        )

        return repository, [*repository_languages]


class RepoFetcher:

    def get(
        self, provider: GitHosting
    ) -> (
        tuple[GitHubRepoFetcher, Callable[[Repository], GitRepoResponse]]
        | tuple[GitLabRepoFetcher, Callable[[Project], GitRepoResponse]]
        | None
    ):
        """bool represents whether it has a data transformer which can aid"""
        if provider == GitHosting.GITHUB:
            return GitHubRepoFetcher(), GitHubRepoResponseTransformer.from_github
        elif provider == GitHosting.GITLAB:
            return GitLabRepoFetcher(), GitLabRepoResponseTransformer.from_gitlab
        else:
            return None
