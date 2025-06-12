from typing import List, Optional, Protocol

from app.models import GitLabel, Repo


class IGitLabelStore(Protocol):
    async def get_by_id_and_user(
        self, token_id: str, user_id: str
    ) -> Optional[GitLabel]: ...


class TortoiseGitLabelStore(IGitLabelStore):
    async def get_by_id_and_user(self, token_id: str, user_id: str):
        return await GitLabel.filter(id=token_id, user_id=user_id).first()


class IRepoStore(Protocol):
    async def get_all_by_user(
        self, user_id: str, offset: int, limit: int
    ) -> List[Repo]: ...
    async def count_by_user(self, user_id: str) -> int: ...


class TortoiseRepoStore(IRepoStore):

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
