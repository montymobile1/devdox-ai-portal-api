import gitlab
import requests
from gitlab import Gitlab, GitlabError

from app.exceptions.custom_exceptions import DevDoxAPIException


class AuthenticatedGitLabManager:

    def __init__(self, base_url, git_client, access_token, rq=requests):
        self.base_url = base_url
        self._header = {"PRIVATE-TOKEN": access_token}
        self._git_client:Gitlab = git_client
        self._rq= rq.Session()

    def get_project(self, project_id):
        try:
            return self._git_client.projects.get(project_id)
        except GitlabError as e:
            raise DevDoxAPIException(
                user_message="Unable to fetch GitLab project",
                log_message="GitLab project fetch failed",
                root_exception=e,
            )

    def get_user(self):
        try:
            url = f"{self.base_url}/api/v4/user"
            response = self._rq.get(url, headers=self._header)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            raise DevDoxAPIException(
                user_message="Unable to fetch GitLab user.",
                log_message="GitLab user fetch failed",
                root_exception=e,
            )

    def get_user_repositories(self, page=1, per_page=20):
        try:
            per_page = max(1, min(per_page, 100))
            page = max(1, page)

            url = (
                f"{self.base_url}/api/v4/projects"
                f"?membership=true&min_access_level=30&per_page={per_page}&page={page}"
            )
            response = self._rq.get(url, headers=self._header)
            response.raise_for_status()

            repos = response.json()
            pagination = {
                "current_page": page,
                "per_page": per_page,
                "total_pages": int(response.headers.get("X-Total-Pages", 1)),
                "next_page": int(response.headers.get("X-Next-Page") or 0) or None,
                "prev_page": int(response.headers.get("X-Prev-Page") or 0) or None,
            }
            return {"repositories": repos, "pagination_info": pagination}
        except requests.exceptions.RequestException as e:
            raise DevDoxAPIException(
                user_message="Unable to fetch GitLab repositories.",
                log_message="GitLab repository list fetch failed",
                root_exception=e,
            )

class GitLabManager:

    default_base_url = "https://gitlab.com"

    def __init__(self, base_url=default_base_url):
        self.base_url = base_url.rstrip("/")

    def authenticate(self, access_token):
        try:
            gl = gitlab.Gitlab(url=self.base_url, private_token=access_token)
            gl.auth()
            return AuthenticatedGitLabManager(base_url=self.base_url, git_client=gl, access_token=access_token)

        except Exception as e:
            raise DevDoxAPIException(
                user_message="GitLab authentication failed",
                log_message="Failed to authenticate GitLabManager",
                root_exception=e
            )
