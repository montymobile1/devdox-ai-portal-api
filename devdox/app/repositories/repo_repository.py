from typing import List

from app.models import Repo


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
