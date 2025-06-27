from typing import Any

from app.schemas.repo import (
    GitHubRepoResponseTransformer,
    GitLabRepoResponseTransformer,
)
from app.utils.repo_fetcher import IRepoFetcher

class FakeGitHubRepoFetcher(IRepoFetcher):
    def __init__(self):
        self.received_calls = []
        self.repo_user = {"login": "mockuser"}

    def fetch_user_repositories(self, token: str, offset: int, limit: int) -> dict[str, Any]:
        self.received_calls.append(("fetch_user_repositories", token, offset, limit))
        return {"data_count": 1, "data": ["mock-repo"]}

    def fetch_single_repo(self, token: str, relative_path: str | int):
        self.received_calls.append(("fetch_single_repo", token, relative_path))
        return ("mock-repo", ["Python"])

    def fetch_repo_user(self, token: str):
        self.received_calls.append(("fetch_repo_user", token))
        return self.repo_user

class FakeGitLabRepoFetcher(IRepoFetcher):
    def __init__(self):
        self.received_calls = []
        self.repo_user = {"username": "mockuser"}

    def fetch_user_repositories(self, token: str, offset: int, limit: int) -> dict[str, Any]:
        self.received_calls.append(("fetch_user_repositories", token, offset, limit))
        return {"data_count": 1, "data": ["mock-repo"]}

    def fetch_single_repo(self, token: str, relative_path: str):
        self.received_calls.append(("fetch_single_repo", token, relative_path))
        return ("mock-repo", ["Python"])

    def fetch_repo_user(self, token: str):
        self.received_calls.append(("fetch_repo_user", token))
        return self.repo_user


class FakeRepoFetcher:
    def __init__(self):
        self.github_fetcher = FakeGitHubRepoFetcher()
        self.gitlab_fetcher = FakeGitLabRepoFetcher()
        self.calls = []

    def get_components(self, provider: str):
        self.calls.append(("get_components", provider))
        if provider.lower() == "github":
            return self.github_fetcher, GitHubRepoResponseTransformer()
        elif provider.lower() == "gitlab":
            return self.gitlab_fetcher, GitLabRepoResponseTransformer()
        return None, None
