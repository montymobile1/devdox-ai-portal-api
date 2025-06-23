import datetime
from typing import List, Optional
from uuid import uuid4

from models import GitLabel


class FakeGitLabelStore:
    def __init__(self):
        self.git_labels: List[GitLabel] = []
        self.total_count = 0
        self.received_calls = []  # for optional spy behavior
        self.exceptions = {}  # method_name -> exception to raise

    def set_fake_data(self, git_labels: List[GitLabel], total_count: Optional[int] = None):
        self.git_labels = git_labels
        self.total_count = total_count if total_count is not None else len(git_labels)

    def set_exception(self, method_name: str, exception: Exception):
        self.exceptions[method_name] = exception

    async def get_by_user_id(self, offset, limit, user_id, git_hosting=None):
        if "get_by_user_id" in self.exceptions:
            raise self.exceptions["get_by_user_id"]
        self.received_calls.append(("get_by_user_id", offset, limit, user_id, git_hosting))
        return self.git_labels

    async def count_by_user_id(self, user_id, git_hosting=None):
        if "count_by_user_id" in self.exceptions:
            raise self.exceptions["count_by_user_id"]
        self.received_calls.append(("count_by_user_id", user_id, git_hosting))
        return self.total_count

    async def get_by_token_id_and_user(self, token_id, user_id):
        if "get_by_token_id_and_user" in self.exceptions:
            raise self.exceptions["get_by_token_id_and_user"]
        self.received_calls.append(("get_by_token_id_and_user", token_id, user_id))
        return next((lbl for lbl in self.git_labels if str(lbl.id) == token_id and lbl.user_id == user_id), None)

    async def get_git_hosting_map_by_token_id(self, token_ids):
        if "get_git_hosting_map_by_token_id" in self.exceptions:
            raise self.exceptions["get_git_hosting_map_by_token_id"]
        self.received_calls.append(("get_git_hosting_map_by_token_id", token_ids))
        return [{"id": str(lbl.id), "git_hosting": lbl.git_hosting} for lbl in self.git_labels if str(lbl.id) in token_ids]


def make_fake_git_label(**overrides) -> GitLabel:
    now = datetime.datetime.now()
    return GitLabel(
        id=overrides.get("id", uuid4()),
        user_id=overrides.get("user_id", "fake-user"),
        label=overrides.get("label", "fake-label"),
        git_hosting=overrides.get("git_hosting", "github"),
        username=overrides.get("username", "fakeuser"),
        token_value=overrides.get("token_value", "real-token"),
        masked_token=overrides.get("masked_token", "****1234"),
        created_at=overrides.get("created_at", now),
        updated_at=overrides.get("updated_at", now),
    )
