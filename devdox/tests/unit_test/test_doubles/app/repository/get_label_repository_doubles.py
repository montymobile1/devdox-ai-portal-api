import datetime
import uuid
from typing import List, Optional
from uuid import uuid4

from models import GitLabel

from app.repositories.git_label import ILabelStore
from app.schemas.git_label import GitLabelDBCreateDTO


class FakeGitLabelStore(ILabelStore):
    def __init__(self):
        self.git_labels: List[GitLabel] = []
        self.total_count = 0
        self.received_calls = []  # for optional spy behavior
        self.exceptions = {}  # method_name -> exception to raise
        self.created_label = None

    def set_created_label(self, label: GitLabel):
        self.created_label = label

    def set_fake_data(
        self, git_labels: List[GitLabel], total_count: Optional[int] = None
    ):
        self.git_labels = git_labels
        self.total_count = total_count if total_count is not None else len(git_labels)

    def set_exception(self, method_name: str, exception: Exception):
        self.exceptions[method_name] = exception

    async def get_by_user_id(self, offset, limit, user_id, git_hosting=None):
        if "get_by_user_id" in self.exceptions:
            raise self.exceptions["get_by_user_id"]
        self.received_calls.append(
            ("get_by_user_id", offset, limit, user_id, git_hosting)
        )
        return self.git_labels

    async def count_by_user_id(self, user_id, git_hosting=None):
        if "count_by_user_id" in self.exceptions:
            raise self.exceptions["count_by_user_id"]
        self.received_calls.append(("count_by_user_id", user_id, git_hosting))
        return self.total_count
    
    async def count_by_user_id_and_label(self, user_id, label=None):
        if "count_by_user_id_and_label" in self.exceptions:
            raise self.exceptions["count_by_user_id_and_label"]
        self.received_calls.append(("count_by_user_id_and_label", user_id, label))
        return self.total_count
    
    async def get_by_token_id_and_user(self, token_id, user_id):
        if "get_by_token_id_and_user" in self.exceptions:
            raise self.exceptions["get_by_token_id_and_user"]
        self.received_calls.append(("get_by_token_id_and_user", token_id, user_id))
        return next(
            (
                lbl
                for lbl in self.git_labels
                if str(lbl.id) == token_id and lbl.user_id == user_id
            ),
            None,
        )

    async def get_git_hosting_map_by_token_id(self, token_ids):
        if "get_git_hosting_map_by_token_id" in self.exceptions:
            raise self.exceptions["get_git_hosting_map_by_token_id"]
        self.received_calls.append(("get_git_hosting_map_by_token_id", token_ids))
        return [
            {"id": str(lbl.id), "git_hosting": lbl.git_hosting}
            for lbl in self.git_labels
            if str(lbl.id) in token_ids
        ]

    async def get_by_user_id_and_label(self, offset, limit, user_id, label):
        if "get_by_user_id_and_label" in self.exceptions:
            raise self.exceptions["get_by_user_id_and_label"]
        self.received_calls.append(
            ("get_by_user_id_and_label", offset, limit, user_id, label)
        )
        return [
            lbl
            for lbl in self.git_labels
            if lbl.user_id == user_id and lbl.label == label
        ]

    async def create_new(self, label_model: GitLabelDBCreateDTO):
        if "create_new" in self.exceptions:
            raise self.exceptions["create_new"]
        self.received_calls.append(("create_new", label_model))
        if self.created_label:
            return self.created_label
        result = GitLabel(**label_model.model_dump())
        self.git_labels.append(result)
        return result

    async def delete_by_id_and_user_id(self, label_id: uuid.UUID, user_id: str) -> int:
        if not label_id or not user_id or not user_id.strip():
            return -1

        self.received_calls.append(("delete_by_id_and_user_id", label_id, user_id))

        initial_count = len(self.git_labels)
        self.git_labels = [
            label
            for label in self.git_labels
            if not (label.id == label_id and label.user_id == user_id)
        ]
        return initial_count - len(self.git_labels)


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
