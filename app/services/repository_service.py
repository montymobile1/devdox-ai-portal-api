from typing import List, Tuple

from app.repositories.git_label_repository import (
    IRepoStore,
    TortoiseRepoStore,
)
from app.schemas.basic import PaginationParams
from app.schemas.repo import RepoResponse
from app.utils.auth import UserClaims


class RepoQueryService:
    def __init__(self, repo_store: IRepoStore):
        self.repo_store = repo_store

    async def get_all_user_repositories(
        self, user: UserClaims, pagination: PaginationParams
    ) -> Tuple[int, List[RepoResponse]]:

        total_count = await self.repo_store.count_by_user(user.sub)

        if total_count == 0:
            return total_count, []

        repos = await self.repo_store.get_all_by_user(
            user.sub, pagination.offset, pagination.limit
        )
        repo_responses = [
            RepoResponse.model_validate(repo, from_attributes=True) for repo in repos
        ]

        return total_count, repo_responses


def repo_query_service_dependency_definition() -> RepoQueryService:
    return RepoQueryService(
        repo_store=TortoiseRepoStore(),
    )
