from typing import List, Tuple

from fastapi import Depends

from app.repositories.git_label_repository import TortoiseGitLabelStore
from app.repositories.repo_repository import TortoiseRepoStore
from app.schemas.basic import PaginationParams
from app.schemas.repo import RepoResponse
from app.utils.auth import UserClaims


class RepoQueryService:
    def __init__(self, repo_store: TortoiseRepoStore = Depends(), gl_store:TortoiseGitLabelStore = Depends()):
        self.repo_store = repo_store
        self.gl_store = gl_store

    async def get_all_user_repositories(
        self, user: UserClaims, pagination: PaginationParams
    ) -> Tuple[int, List[RepoResponse]]:
        
        total_count = await self.repo_store.count_by_user(user.sub)

        if total_count == 0:
            return total_count, []

        repos = await self.repo_store.get_all_by_user(
            user.sub, pagination.offset, pagination.limit
        )

        token_ids = {str(r.token_id) for r in repos if r.token_id}
        labels = await self.gl_store.get_git_hosting_map_by_token_id(token_ids)
        label_map = {str(l["id"]): l["git_hosting"] for l in labels}

        repo_responses = []

        for rp in repos:
            if val := label_map.get(str(rp.token_id)):
                rp.git_hosting = val

            repo_responses.append(
                RepoResponse.model_validate(rp, from_attributes=True)
            )

        return total_count, repo_responses
