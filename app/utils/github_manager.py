from github import Github
from github.GithubException import GithubException
import traceback


class GitHubManager:
    def __init__(self, base_url="https://api.github.com", owner="", repo="", access_token=""):
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
                "html_url": user.html_url
            }
        except GithubException as e:
            print(f"Error fetching user: {e}")
            return False
        except Exception as e:
            print(f"Unexpected error fetching user: {e}")
            return False


    def log_error(self, message, exception):
        """Logs an error with traceback details."""
        print(f"{message}: {exception}")
        traceback.print_exc()