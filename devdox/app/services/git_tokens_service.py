from typing import Annotated, Optional

from fastapi import Depends

from app.repositories.git_label_repository import TortoiseGitLabelStore
from app.schemas.basic import PaginationParams, RequiredPaginationParams
from app.schemas.git_label import GitLabelResponse
from app.utils.auth import AuthenticatedUserDTO, UserClaims


def format_git_label_data(raw_git_labels):
    formatted_data = []
    for git_label in raw_git_labels:
        
        formatted_data.append(
            GitLabelResponse(
                id= git_label.id,
                user_id=git_label.user_id,
                label= git_label.label,
                git_hosting= git_label.git_hosting,
                masked_token= git_label.masked_token,
                username= git_label.username,
                created_at= git_label.created_at.isoformat(),
                updated_at= git_label.updated_at.isoformat(),
                token_value=git_label.token_value,
            ).model_dump(exclude={"token_value", "user_id"})
        )
    
    return formatted_data


class GetGitLabelService:

    def __init__(
            self,
            label_store: TortoiseGitLabelStore
    ):
        self.label_store = label_store
    
    @classmethod
    def with_dependency(cls, label_store: Annotated[TortoiseGitLabelStore, Depends()],
    ) -> "GetGitLabelService":
        return cls(label_store)
    
    async def get_git_labels_by_user(self, pagination:RequiredPaginationParams, user_claims:UserClaims, git_hosting:Optional[str]):

        # Get total count
        total = await self.label_store.count_by_user_id(
            user_id=user_claims.sub,
            git_hosting=git_hosting
        )

        if total == 0:
            return {
                "items": [],
                "total": total,
                "page": pagination.offset  + 1,
                "size": pagination.limit,
            }

        git_labels = await self.label_store.get_by_user_id(
            offset=pagination.offset,
            limit=pagination.limit,
            user_id=user_claims.sub,
            git_hosting=git_hosting
        )

        # Format response data with masked tokens
        formatted_data = format_git_label_data(git_labels)

        return {
            "items": formatted_data,
            "total": total,
            "page": pagination.offset  + 1,
            "size": pagination.limit,
        }

    async def get_git_labels_by_label(self, pagination: PaginationParams, user_claims: AuthenticatedUserDTO, label: str):

        git_labels = await self.label_store.get_by_user_id_and_label(
            offset=pagination.offset,
            limit=pagination.limit,
            user_id=user_claims.id,
            label=label
        )

        formatted_data = format_git_label_data(git_labels)

        return formatted_data
