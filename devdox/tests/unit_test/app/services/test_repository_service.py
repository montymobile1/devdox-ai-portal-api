import pytest
from tortoise.exceptions import IntegrityError

from models import Repo
from app.services.repository_service import RepoManipulationService
from app.schemas.repo import GitRepoResponse
from app.utils.auth import UserClaims
from app.exceptions.custom_exceptions import (
    BadRequest,
    DevDoxAPIException,
    ResourceNotFound,
)


class StubUserStore:
    async def get_by_user_id(self, user_id):
        return (
            None
            if user_id == "missing_user"
            else type("User", (), {"encryption_salt": "salt=="})()
        )


class StubLabelStore:
    async def get_by_token_id_and_user(self, token_id, user_id):
        if token_id == "missing_token":
            return None
        return type(
            "Label", (), {"token_value": "encrypted_token", "git_hosting": "github"}
        )()


class StubEncryption:
    def decrypt_for_user(self, encrypted, salt_b64):
        return "decrypted_token"


class StubFetcher:
    def get(self, provider):
        if provider == "github":
            return self, lambda repo: GitRepoResponse(
                id="r1",
                repo_name="test",
                description=None,
                html_url="url",
                default_branch="main",
                forks_count=1,
                stargazers_count=2,
                size=100,
                repo_created_at=None,
                private=True,
                visibility="private",
                relative_path="relative_url",
            )
        return None, None

    def fetch_single_repo(self, token, relative_path):
        return (object(), ["Python"])


class FakeRepoStore:
    def __init__(self):
        self.saved = []
        self.raise_integrity_error = False

    async def create_new_repo(self, repo_model: Repo):
        if self.raise_integrity_error:
            raise IntegrityError("Duplicate")
        self.saved.append(repo_model)
        return repo_model


class TestRepoManipulationService:

    @pytest.mark.asyncio
    async def test_add_repo_from_provider_success(self):
        service = RepoManipulationService(
            label_store=StubLabelStore(),
            repo_store=FakeRepoStore(),
            user_store=StubUserStore(),
            encryption=StubEncryption(),
            git_fetcher=StubFetcher(),
        )
        claims = UserClaims(sub="u1")
        await service.add_repo_from_provider(claims, "t1", "owner/repo")
        assert service.repo_store.saved  # should have one saved repo

    @pytest.mark.asyncio
    async def test_add_repo_user_not_found(self):
        service = RepoManipulationService(
            label_store=StubLabelStore(),
            repo_store=FakeRepoStore(),
            user_store=StubUserStore(),
            encryption=StubEncryption(),
            git_fetcher=StubFetcher(),
        )
        with pytest.raises(ResourceNotFound):
            await service.add_repo_from_provider(
                UserClaims(sub="missing_user"), "t1", "p"
            )

    @pytest.mark.asyncio
    async def test_add_repo_label_not_found(self):
        service = RepoManipulationService(
            label_store=StubLabelStore(),
            repo_store=FakeRepoStore(),
            user_store=StubUserStore(),
            encryption=StubEncryption(),
            git_fetcher=StubFetcher(),
        )
        with pytest.raises(ResourceNotFound):
            await service.add_repo_from_provider(
                UserClaims(sub="u1"), "missing_token", "p"
            )

    @pytest.mark.asyncio
    async def test_add_repo_unsupported_provider(self):
        class BadFetcher(StubFetcher):
            def get(self, provider):
                return None, None

        service = RepoManipulationService(
            label_store=StubLabelStore(),
            repo_store=FakeRepoStore(),
            user_store=StubUserStore(),
            encryption=StubEncryption(),
            git_fetcher=BadFetcher(),
        )
        with pytest.raises(DevDoxAPIException) as exc:
            await service.add_repo_from_provider(UserClaims(sub="u1"), "t1", "p")

        assert exc

    @pytest.mark.asyncio
    async def test_add_repo_duplicate(self):
        repo_store = FakeRepoStore()
        repo_store.raise_integrity_error = True
        service = RepoManipulationService(
            label_store=StubLabelStore(),
            repo_store=repo_store,
            user_store=StubUserStore(),
            encryption=StubEncryption(),
            git_fetcher=StubFetcher(),
        )
        with pytest.raises(BadRequest):
            await service.add_repo_from_provider(UserClaims(sub="u1"), "t1", "p")
