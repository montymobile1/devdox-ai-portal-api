from github import Github
from github.GithubException import GithubException

from app.exceptions.custom_exceptions import DevDoxAPIException


class AuthenticatedGitHubManager:

    def __init__(self, base_url, git_client):
        self.base_url = base_url
        self._git_client:Github = git_client

    def get_project(self, owner: str, repo: str):
        try:
            return self._git_client.get_repo(f"{owner}/{repo}")
        except GithubException as e:
            raise DevDoxAPIException(
                user_message="Unable to fetch GithHub project",
                log_message="GitHub project fetch failed",
                root_exception=e
            )

    def get_user(self):
        """Get the authenticated user information using PyGithub."""
        try:
            user = self._git_client.get_user()
            return {
                "login": user.login,
                "id": user.id,
                "name": user.name,
                "email": user.email,
                "avatar_url": user.avatar_url,
                "html_url": user.html_url,
            }
        except GithubException as e:
            raise DevDoxAPIException(
                user_message="Unable to fetch GitHub user.",
                log_message="GitHub user fetch failed",
                root_exception=e,
            )

    def get_user_repositories(
        self,
        page=1,
        per_page=20,
        visibility="all",
        affiliation="owner,collaborator,organization_member",
        sort="updated",
        direction="desc",
    ):
        """
        Get list of repositories that the authenticated user has access to with pagination.
        """
        try:
            per_page = GitHubManager.validate_per_page(per_page)
            page = GitHubManager.validate_page(page)

            user = self._git_client.get_user()

            repos_paginated = user.get_repos(
                visibility=visibility,
                affiliation=affiliation,
                sort=sort,
                direction=direction,
            )
            repos_paginated.per_page = per_page

            repos_page = repos_paginated.get_page(page - 1)
            repo_list = [GitHubManager.extract_repo_info(repo) for repo in repos_page]

            pagination_info = GitHubManager.get_pagination_info(
                total_count=repos_paginated.totalCount,
                page=page,
                per_page=per_page,
            )

            return {
                "repositories": repo_list,
                "pagination_info": pagination_info,
            }

        except GithubException as e:
            raise DevDoxAPIException(
                user_message="Unable to fetch GitHub repositories.",
                log_message="GitHub repository list fetch failed",
                root_exception=e,
            )

class GitHubManager:

    default_base_url = "https://api.github.com"

    def __init__(self, base_url=default_base_url):
        self.base_url = base_url

    def authenticate(self, access_token: str) -> AuthenticatedGitHubManager:

        try:
            if self.base_url == self.default_base_url:
                github_client = Github(access_token)
            else:
                github_client = Github(base_url=self.base_url, login_or_token=access_token)

            return AuthenticatedGitHubManager(
                base_url=self.base_url, git_client=github_client
            )

        except GithubException as e:
            raise DevDoxAPIException(
                user_message="GitHub authentication failed",
                log_message="Failed to authenticate GitHubManager",
                root_exception=e
            )

    @staticmethod
    def validate_per_page(per_page):
        return per_page if 1 <= per_page <= 100 else 30

    @staticmethod
    def validate_page(page):
        return page if page >= 1 else 1
    
    @staticmethod
    def extract_repo_info(repo):
        return {
            "id": repo.id,
            "name": repo.name,
            "full_name": repo.full_name,
            "description": repo.description,
            "private": repo.private,
            "html_url": repo.html_url,
            "clone_url": repo.clone_url,
            "ssh_url": repo.ssh_url,
            "default_branch": repo.default_branch,
            "language": repo.language,
            "size": repo.size,
            "stargazers_count": repo.stargazers_count,
            "watchers_count": repo.watchers_count,
            "forks_count": repo.forks_count,
            "open_issues_count": repo.open_issues_count,
            "created_at": repo.created_at.isoformat() if repo.created_at else None,
            "updated_at": repo.updated_at.isoformat() if repo.updated_at else None,
            "pushed_at": repo.pushed_at.isoformat() if repo.pushed_at else None,
            "owner": {
                "login": repo.owner.login,
                "id": repo.owner.id,
                "type": repo.owner.type,
            },
            "permissions": GitHubManager._get_repo_permissions(repo),
        }
    
    @staticmethod
    def _get_repo_permissions(repo):
        permissions = getattr(repo, "permissions", None)
        return {
            "admin": getattr(permissions, "admin", False),
            "push": getattr(permissions, "push", False),
            "pull": getattr(permissions, "pull", False),
        }
    
    @staticmethod
    def get_pagination_info(total_count, page, per_page):
        total_pages = (total_count + per_page - 1) // per_page
        has_next_page = page < total_pages
        has_prev_page = page > 1

        return {
            "current_page": page,
            "per_page": per_page,
            "total_count": total_count,
            "total_pages": total_pages,
            "has_next_page": has_next_page,
            "has_prev_page": has_prev_page,
            "next_page": page + 1 if has_next_page else None,
            "prev_page": page - 1 if has_prev_page else None,
        }
