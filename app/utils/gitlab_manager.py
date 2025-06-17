import gitlab
import requests

# ==================================================================================================================
# TODO: THIS SECTION WILL BE DEPRECATED SLOWLY AS WE GO IN FAVOR OF THE OTHER NEW PART IN app/utils/git_managers.py
# ==================================================================================================================

class GitLabManager:
    def __init__(self, base_url="https://gitlab.com", project_id="", access_token=""):
        self.base_url = base_url.rstrip("/")
        self.project_id = project_id
        self.headers = {"PRIVATE-TOKEN": access_token}

        self.session = requests.Session()
        try:
            self.gl = gitlab.Gitlab(url=self.base_url, private_token=access_token)
            self.gl.auth()
            self.project = self.get_project()
            self.auth_status = True
        except Exception as e:
            print(f"Error initializing GitLabManager: {e}")
            self.project = None
            self.gl = None
            self.auth_status = False

    def get_project(self):
        if self.project_id != "":
            return self.gl.projects.get(self.project_id)
        else:
            return None

    def get_user(self):
        try:
            url = f"{self.base_url}/api/v4/user"
            response = self.session.get(url, headers=self.headers)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Error fetching repos: {e}")
            return False

    def get_repos(self, page=1, per_page=20):
        try:
            per_page = max(1, min(per_page, 100))
            page = max(1, page)

            url = (
                f"{self.base_url}/api/v4/projects"
                f"?membership=true&min_access_level=30&per_page={per_page}&page={page}"
            )
            response = self.session.get(url, headers=self.headers)
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
            self.log_error("GitLab API request failed", e)
            return []

    def log_error(self, message, exception):
        """Logs an error with traceback details."""
        print(f"{message}: {exception}")
        import traceback

        traceback.print_exc()
