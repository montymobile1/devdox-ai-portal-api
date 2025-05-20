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


    def get_repos(self,page=1):
        try:
            url = f"{self.base_url}/api/v4/projects?membership=true&min_access_level=30&per_page=10&page={page}"
            response = self.session.get(url, headers=self.headers)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Error fetching repos: {e}")
            return []


    def get_wiki_pages(self):
        """Fetch all wiki pages of the project."""
        url = f"{self.base_url}/api/v4/projects/{self.project_id}/wikis/"
        response = self.session.get(url, headers=self.headers)
        response.raise_for_status()
        return response.json()

    def ensure_branch_exists(self, branch_name):
        """Ensure the branch exists; creates it if needed."""
        try:

            return self.project.branches.create({'branch': branch_name, 'ref': "main"})
        except gitlab.exceptions.GitlabCreateError:
            return self.project.branches.get(branch_name)

    def prepare_file_actions(self, files, branch_name):
        """Prepares file actions for commit."""
        actions = []
        for file in files:
            file_path = file.get("file_path", "").replace("\\", "/").strip()
            file_content = file.get("content", "")

            if not file_path or file_content is None:
                continue  # Skip invalid files

            try:
                self.project.files.get(file_path=file_path, ref=branch_name)
                action_type = "update"
            except gitlab.exceptions.GitlabGetError:
                action_type = "create"

            actions.append({
                "action": action_type,
                "file_path": file_path,
                "content": file_content
            })

        return actions

    def commit_files(self, branch_name, commit_message, actions):
        """Commits all file changes to the branch."""
        try:
            self.project.commits.create({
                "branch": branch_name,
                "commit_message": commit_message,
                "actions": actions
            })
            print("Successfully committed all file changes")
            return True
        except Exception as e:
            self.log_error("Error committing files", e)
            return False

    def create_merge_request(self, branch_name, merge_descripton):
        """Creates a merge request from the feature branch to main."""
        try:
            mr = self.project.mergerequests.create({
                "source_branch": branch_name,
                "target_branch": "main",
                "title": merge_descripton,
                "description": merge_descripton,
                "remove_source_branch": True
            })

        except gitlab.exceptions.GitlabCreateError as e:
            self.log_error("Merge request creation error", e)

    def log_error(self, message, exception):
        """Logs an error with traceback details."""
        print(f"{message}: {exception}")
        import traceback
        traceback.print_exc()

