from typing import List, Optional

from models import Repo

from app.repositories.repo import IRepoStore


class FakeRepoStore(IRepoStore):
    def __init__(self):
        self.repos: List[Repo] = []
        self.total_count = 0
        self.received_calls = []
        self.exceptions = {}

    def set_fake_data(self, repos: List[Repo], total_count: Optional[int] = None):
        self.repos = repos
        self.total_count = total_count if total_count is not None else len(repos)

    def set_exception(self, method_name: str, exception: Exception):
        self.exceptions[method_name] = exception

    async def get_all_by_user(
        self, user_id: str, offset: int, limit: int
    ) -> List[Repo]:
        if "get_all_by_user" in self.exceptions:
            raise self.exceptions["get_all_by_user"]
        self.received_calls.append(("get_all_by_user", user_id, offset, limit))
        return self.repos

    async def count_by_user(self, user_id: str) -> int:
        if "count_by_user" in self.exceptions:
            raise self.exceptions["count_by_user"]
        self.received_calls.append(("count_by_user", user_id))
        return self.total_count

    async def create_new_repo(self, repo_model: Repo):
        self.repos.append(repo_model)
        return repo_model
