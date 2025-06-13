import datetime
import uuid
from typing import List

import pytest

from app.config import GitHosting
from app.repositories.git_label_repository import IRepoStore
from app.schemas.basic import PaginationParams
from app.schemas.repo import RepoResponse
from app.services.repository_service import RepoQueryService
from app.utils.auth import UserClaims


class FakeRepoStore(IRepoStore):
    def __init__(self, repos: List[RepoResponse]):
        self._repos = repos

    async def get_all_by_user(self, user_id: str, offset: int, limit: int):
        return self._repos[offset : offset + limit]

    async def count_by_user(self, user_id: str) -> int:
        return len(self._repos)


class TestRepoQueryService:
    @pytest.fixture
    def service(self):

        date_time = datetime.datetime.combine(
            datetime.datetime.now(datetime.timezone.utc).date(),
            datetime.time.min,
            tzinfo=datetime.timezone.utc,
        )

        repos = [
            RepoResponse(
                id=uuid.UUID("9479c7f8-9d4e-4b9a-8627-8c2082a6f7f1"),
                repo_name=f"repo_{i}",
                html_url=f"https://example.com/repo_{i}",
                is_private=False,
                visibility="public",
                repo_created_at=date_time,
                repo_updated_at=date_time,
                forks_count=0,
                stargazers_count=0,
                language="Python",
                size=123,
                description=None,
                git_hosting=GitHosting.GITHUB.value,
                user_id=f"user_id-{i}",
                repo_id=f"repo_id-{i}",
                token_id=None,
                created_at=date_time,
                updated_at=date_time,
            )
            for i in range(10)
        ]
        return RepoQueryService(repo_store=FakeRepoStore(repos))

    @pytest.mark.asyncio
    async def test_get_all_user_repositories_within_bounds(self, service):
        pagination = PaginationParams(offset=0, limit=5)
        user = UserClaims(sub="test_user")
        total, repos = await service.get_all_user_repositories(user, pagination)
        assert total == 10
        assert len(repos) == 5
        assert all(isinstance(repo, RepoResponse) for repo in repos)

    @pytest.mark.asyncio
    async def test_get_all_user_repositories_offset_exceeds(self, service):
        pagination = PaginationParams(offset=15, limit=5)
        user = UserClaims(sub="test_user")
        total, repos = await service.get_all_user_repositories(user, pagination)
        assert total == 10
        assert repos == []

    @pytest.mark.asyncio
    async def test_get_all_user_repositories_exact_bounds(self, service):
        pagination = PaginationParams(offset=5, limit=5)
        user = UserClaims(sub="test_user")
        total, repos = await service.get_all_user_repositories(user, pagination)
        assert total == 10
        assert len(repos) == 5
