from app.utils.git_managers import IManager


class FakeAuthenticatedGitHubManager:
    def __init__(self):
        self.user = {
            "username": "fakeuser",
            "id": 123,
            "name": "Fake User",
            "email": "fake@github.com",
            "avatar_url": "https://fake-avatar.com",
            "html_url": "https://github.com/fakeuser"
        }

    def get_user(self):
        return self.user

    def get_project(self, full_name_or_id):
        return {"id": full_name_or_id, "name": "fake-project"}

    def get_project_languages(self, repo):
        return {"Python": 100}

    def get_user_repositories(self, *args, **kwargs):
        return {
            "repositories": [{"name": "repo1"}, {"name": "repo2"}],
            "pagination_info": {"total_count": 2}
        }


class FakeAuthenticatedGitLabManager:
    def __init__(self):
        self.user = {
            "username": "fakeuser",
            "id": 456,
            "name": "Fake User",
            "email": "fake@gitlab.com",
            "avatar_url": "https://fake-avatar.com",
            "web_url": "https://gitlab.com/fakeuser"
        }

    def get_user(self, timeout=30):
        return self.user

    def get_project(self, project_id, timeout=30):
        return {"id": project_id, "name": "fake-project"}

    def get_project_languages(self, project, timeout=30):
        return {"Python": 100}

    def get_user_repositories(self, *args, **kwargs):
        return {
            "repositories": [{"name": "repo1"}, {"name": "repo2"}],
            "pagination_info": {"total_count": 2}
        }


class FakeGitHubManager(IManager):
    def authenticate(self, access_token: str):
        return FakeAuthenticatedGitHubManager()


class FakeGitLabManager(IManager):
    def authenticate(self, access_token: str):
        return FakeAuthenticatedGitLabManager()

