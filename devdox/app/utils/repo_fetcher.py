from typing import Callable, List, Protocol, Tuple

from github.Repository import Repository
from gitlab.v4.objects import Project

from app.config import GitHosting
from app.schemas.repo import GitRepoResponse, GitRepoResponseTransformer
from app.utils.git_managers import GitHubManager, GitLabManager


class IRepoFetcher(Protocol):
    def fetch_user_repositories(
        self, token: str, offset: int, limit: int
    ) -> Tuple[int, List[GitRepoResponse]]: ...
    
    def fetch_single_repo(self, token: str, full_name_or_id: str | int): ...
    
class GitHubRepoFetcher(IRepoFetcher):
    def __init__(self, base_url: str = GitHubManager.default_base_url):
        self.manager = GitHubManager(base_url)

    def fetch_user_repositories(
        self, token: str, offset: int, limit: int
    ) -> Tuple[int, List[GitRepoResponse]]:
        authenticated_github_manager = self.manager.authenticate(token)
        result = authenticated_github_manager.get_user_repositories(
            page=offset + 1, per_page=limit
        )

        return (
            result["pagination_info"]["total_count"],
            [GitRepoResponseTransformer.from_github(r) for r in result["repositories"]],
        )

    def fetch_single_repo(
        self, token: str, full_name_or_id: str | int
    ) -> tuple[Repository, list[str]] | None:

        authenticated_github_manager = self.manager.authenticate(token)

        repository = authenticated_github_manager.get_project(full_name_or_id)

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
    ) -> Tuple[int, List[GitRepoResponse]]:
        authenticated_gitlab_manager = self.manager.authenticate(token)
        result = authenticated_gitlab_manager.get_user_repositories(
            page=offset + 1, per_page=limit
        )
        return (
            result["pagination_info"]["total_count"],
            [GitRepoResponseTransformer.from_gitlab(r) for r in result["repositories"]],
        )

    def fetch_single_repo(
        self, token: str, full_name: str
    ) -> tuple[Project, list[str]] | None:
        # full_name can be ID or 'namespace/project'
        authenticated_gitlab_manager = self.manager.authenticate(token)
        repository = authenticated_gitlab_manager.get_project(full_name)

        if not repository:
            return None

        repository_languages = authenticated_gitlab_manager.get_project_languages(
            repository
        )

        return repository, [*repository_languages]


class RepoFetcher:

    def get(
        self, provider: GitHosting
    ) -> tuple[GitHubRepoFetcher, Callable[[Repository], GitRepoResponse]] | tuple[
	    GitLabRepoFetcher, Callable[[Project], GitRepoResponse]] | None:
        """bool represents whether it has a data transformer which can aid"""
        if provider == GitHosting.GITHUB:
            return GitHubRepoFetcher(), GitRepoResponseTransformer.from_github
        elif provider == GitHosting.GITLAB:
            return GitLabRepoFetcher(), GitRepoResponseTransformer.from_gitlab
        else:
            return None
