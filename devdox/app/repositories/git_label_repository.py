from typing import Any, Collection, Coroutine, Dict, List, Optional, Union
from uuid import UUID

from models import GitLabel


class TortoiseGitLabelStore:
    async def get_git_hosting_map_by_token_id(
        self, token_ids: Collection[Union[str, UUID]]
    ) -> List[Dict]:
        if not token_ids:
            return []
        return await GitLabel.filter(id__in=token_ids).values("id", "git_hosting")

    async def get_by_token_id_and_user(self, token_id: str, user_id: str) -> GitLabel | None:
        if not token_id or not token_id.strip() or not user_id or not user_id.strip():
            return None

        return await GitLabel.filter(id=token_id, user_id=user_id).first()

    def __get_by_user_id_query(self, user_id, git_hosting: Optional[str] = None):
        if not user_id:
            return None

        query = GitLabel.filter(user_id=user_id)

        if git_hosting:
            query = query.filter(git_hosting=git_hosting)

        return query

    async def get_by_user_id(self, offset, limit, user_id, git_hosting: Optional[str] = None):

        if not user_id:
            return None
        
        query = self.__get_by_user_id_query(user_id, git_hosting)

        git_labels = (
            await query.order_by("-created_at")
            .offset(offset)
            .limit(limit)
            .all()
        )

        return git_labels

    async def count_by_user_id(
        self, user_id, git_hosting: Optional[str] = None
    ):
        if not user_id:
            return None

        query = self.__get_by_user_id_query(user_id, git_hosting)

        return await query.count()
