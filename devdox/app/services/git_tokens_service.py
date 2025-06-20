from typing import Optional

from fastapi import Depends

from app.repositories.git_label_repository import TortoiseGitLabelStore
from app.schemas.basic import RequiredPaginationParams


class GetGitLabelService:

    def __init__(
            self,
            label_store: TortoiseGitLabelStore = Depends()
    ):
        self.label_store = label_store

    async def get_git_labels_by_user(self, pagination:RequiredPaginationParams, user_claims, git_hosting:Optional[str]):

        # Get total count
        total = await self.label_store.count_by_user_id(
            user_id=user_claims.id,
            git_hosting=git_hosting
        )

        if total == 0:
            return {
                "items": [],
                "total": total,
                "page": (pagination.offset // pagination.limit) + 1,
                "size": pagination.limit,
            }

        git_labels = await self.label_store.get_by_user_id(
            offset=pagination.offset,
            limit=pagination.limit,
            user_id=user_claims.id,
            git_hosting=git_hosting
        )
        
        # Format response data with masked tokens
        formatted_data = []
        for gl in git_labels:
            formatted_data.append(
                {
                    "id": str(gl.id),
                    "label": gl.label,
                    "git_hosting": gl.git_hosting,
                    "masked_token": gl.masked_token,
                    "username": gl.username,
                    "created_at": gl.created_at.isoformat(),
                    "updated_at": gl.updated_at.isoformat(),
                }
            )

        return {
            "items": formatted_data,
            "total": total,
            "page": (pagination.offset // pagination.limit) + 1,
            "size": pagination.limit,
        }
