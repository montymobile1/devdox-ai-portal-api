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
        per_page=30,
    ):
        """
        Get list of repositories that the authenticated user has access to with pagination.

        Args:
            visibility (str): Can be 'all', 'public', or 'private'. Default: 'all'
            affiliation (str): Comma-separated list of values. Can include:
                             'owner', 'collaborator', 'organization_member'. Default: 'owner,collaborator,organization_member'
            sort (str): Can be 'created', 'updated', 'pushed', 'full_name'. Default: 'updated'
            direction (str): Can be 'asc' or 'desc'. Default: 'desc'
            page (int): Page number (1-based). Default: 1
            per_page (int): Number of results per page (1-100). Default: 30

        Returns:
            dict: Dictionary containing 'repositories', 'pagination_info' or False if error
        """
        try:
            # Validate per_page parameter
            if per_page < 1 or per_page > 100:
                per_page = 30

            # Validate page parameter
            if page < 1:
                page = 1

            user = self.gh.get_user()
            repos_paginated = user.get_repos(
                visibility=visibility,
                affiliation=affiliation,
                sort=sort,
                direction=direction,
            )

            # Get the specific page
            repos_page = repos_paginated.get_page(
                page - 1
            )  # PyGithub uses 0-based indexing

            repo_list = []
            for repo in repos_page:
                repo_info = {
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
                    "created_at": (
                        repo.created_at.isoformat() if repo.created_at else None
                    ),
                    "updated_at": (
                        repo.updated_at.isoformat() if repo.updated_at else None
                    ),
                    "pushed_at": repo.pushed_at.isoformat() if repo.pushed_at else None,
                    "owner": {
                        "login": repo.owner.login,
                        "id": repo.owner.id,
                        "type": repo.owner.type,
                    },
                    "permissions": {
                        "admin": (
                            repo.permissions.admin
                            if hasattr(repo, "permissions")
                            else False
                        ),
                        "push": (
                            repo.permissions.push
                            if hasattr(repo, "permissions")
                            else False
                        ),
                        "pull": (
                            repo.permissions.pull
                            if hasattr(repo, "permissions")
                            else False
                        ),
                    },
                }
                repo_list.append(repo_info)

            # Calculate pagination info
            total_count = repos_paginated.totalCount
            total_pages = (total_count + per_page - 1) // per_page  # Ceiling division
            has_next_page = page < total_pages
            has_prev_page = page > 1

            return {
                "repositories": repo_list,
                "pagination_info": {
                    "current_page": page,
                    "per_page": per_page,
                    "total_count": total_count,
                    "total_pages": total_pages,
                    "has_next_page": has_next_page,
                    "has_prev_page": has_prev_page,
                    "next_page": page + 1 if has_next_page else None,
                    "prev_page": page - 1 if has_prev_page else None,
                },
            }

        except GithubException as e:
            self.log_error("Error fetching user repositories", e)
            return False
        except Exception as e:
            self.log_error("Unexpected error fetching user repositories", e)
            return False

    def log_error(self, message, exception):
        """Logs an error with traceback details."""
        print(f"{message}: {exception}")
        traceback.print_exc()
