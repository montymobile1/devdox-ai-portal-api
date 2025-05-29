from github import Github
from github.GithubException import GithubException
import traceback


class GitHubManager:
    def __init__(
        self,
        base_url="https://api.github.com",
        owner="",
        repo="",
        access_token="",
        per_page=20,
        page=1,
    ):
        """Initialize GitHub manager with PyGithub."""
        # For GitHub Enterprise, you can specify base_url
        if base_url == "https://api.github.com":
            self.gh = Github(access_token)
        else:
            self.gh = Github(base_url=base_url, login_or_token=access_token)

        self.owner = owner
        self.repo = repo
        self.project = self.get_project()

    def get_project(self):
        """Get the GitHub repository object."""
        if self.owner != "" and self.repo != "":
            try:
                return self.gh.get_repo(f"{self.owner}/{self.repo}")
            except Exception as e:
                print(f"Error getting repository: {e}")
                return None
        else:
            return None

    def get_user(self):
        """Get the authenticated user information using PyGithub."""
        try:
            user = self.gh.get_user()
            return {
                "login": user.login,
                "id": user.id,
                "name": user.name,
                "email": user.email,
                "avatar_url": user.avatar_url,
                "html_url": user.html_url,
            }
        except GithubException as e:
            print(f"Error fetching user: {e}")
            return False
        except Exception as e:
            print(f"Unexpected error fetching user: {e}")
            return False

    def get_user_repositories(
            self,
            visibility="all",
            affiliation="owner,collaborator,organization_member",
            sort="updated",
            direction="desc",
            page=1,
            per_page=20,
    ):
        """
        Get list of repositories that the authenticated user has access to with pagination.
        """
        try:
            per_page = self._validate_per_page(per_page)
            page = self._validate_page(page)

            user = self.gh.get_user()
            repos_paginated = user.get_repos(
                visibility=visibility,
                affiliation=affiliation,
                sort=sort,
                direction=direction,
            )
            repos_paginated.per_page = per_page

            repos_page = repos_paginated.get_page(page - 1)
            repo_list = [self._extract_repo_info(repo) for repo in repos_page]

            pagination_info = self._get_pagination_info(
                total_count=repos_paginated.totalCount,
                page=page,
                per_page=per_page,
            )

            return {
                "repositories": repo_list,
                "pagination_info": pagination_info,
            }

        except GithubException as e:
            self.log_error("Error fetching user repositories", e)
            return False
        except Exception as e:
            self.log_error("Unexpected error fetching user repositories", e)
            return False

    def _validate_per_page(self, per_page):
        return per_page if 1 <= per_page <= 100 else 30

    def _validate_page(self, page):
        return page if page >= 1 else 1

    def _get_pagination_info(self, total_count, page, per_page):
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

    def _extract_repo_info(self, repo):
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
            "permissions": self._get_repo_permissions(repo),
        }

    def _get_repo_permissions(self, repo):
        permissions = getattr(repo, "permissions", None)
        return {
            "admin": getattr(permissions, "admin", False),
            "push": getattr(permissions, "push", False),
            "pull": getattr(permissions, "pull", False),
        }

    def log_error(self, message, exception):
        """Logs an error with traceback details."""
        print(f"{message}: {exception}")
        traceback.print_exc()
