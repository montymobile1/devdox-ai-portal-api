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

    async def create_new_repo(self, user_id, token_id, repo_id, repo_name, description, html_url, default_branch,
                          forks_count, stargazers_count, is_private, visibility, size, repo_created_at, language):
        return await Repo.create(
            user_id=user_id,
            token_id=token_id,
            repo_id=repo_id,
            repo_name=repo_name,
            description=description,
            html_url=html_url,
            default_branch=default_branch,
            forks_count=forks_count,
            stargazers_count=stargazers_count,
            is_private=is_private,
            visibility=visibility,
            size=size,
            repo_created_at=repo_created_at,
            language=language,
        )