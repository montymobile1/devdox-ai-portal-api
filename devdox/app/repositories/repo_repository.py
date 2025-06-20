from typing import Any, Coroutine, List

from tortoise.exceptions import IntegrityError

from app.exceptions.custom_exceptions import BadRequest
from models import Repo


class TortoiseRepoStore:

    async def get_all_by_user(
        self, user_id: str, offset: int, limit: int
    ) -> List[Repo]:
        return (
            await Repo.filter(user_id=user_id)
            .order_by("-created_at")
            .offset(offset)
            .limit(limit)
            .all()
        )

    async def count_by_user(self, user_id: str) -> int:
        return await Repo.filter(user_id=user_id).count()

    async def create_new_repo(self, repo_model: Repo):
        await repo_model.save(force_create=True)
        await repo_model.refresh_from_db()
        return repo_model
