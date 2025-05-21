import gitlab
import requests


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
        if self.project_id !="":
            return self.gl.projects.get(self.project_id)
        else:
            None

    def get_user(self):
        try:
            url = f"{self.base_url}/api/v4/user"
            response = self.session.get(url, headers=self.headers)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Error fetching repos: {e}")
            return False

    def log_error(self, message, exception):
        """Logs an error with traceback details."""
        print(f"{message}: {exception}")
        import traceback
        traceback.print_exc()

