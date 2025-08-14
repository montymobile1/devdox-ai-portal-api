import pytest

from app.exceptions.exception_constants import (
    GIT_LABEL_TOKEN_RESOURCE_NOT_FOUND,
    USER_RESOURCE_NOT_FOUND,
)
from models_src.dto.git_label import GitLabelResponseDTO
from models_src.dto.user import UserResponseDTO
from models_src.exceptions.utils import internal_error, RepoErrors
from app.services.repository import RepoManipulationService
from app.schemas.repo import AddRepositoryRequest, GitRepoResponse
from app.utils.auth import UserClaims
from app.exceptions.local_exceptions import (
    BadRequest,
    ResourceNotFound,
)
from app.exceptions.base_exceptions import DevDoxAPIException
from models_src.test_doubles.repositories.git_label import StubGitLabelStore
from models_src.test_doubles.repositories.repo import FakeRepoStore
from models_src.test_doubles.repositories.user import StubUserStore


class StubEncryption:
    def decrypt_for_user(self, encrypted, salt_b64):
        return "decrypted_token"

    def decrypt(self, encrypted_text: str):
        return "decrypt"


class StubTransformer:
    def from_git(self, data):
        return GitRepoResponse(
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


class StubFetcher:
    def get_components(self, provider):
        if provider == "github":
            return self, StubTransformer()
        elif provider == "gitlab":
            return self, StubTransformer()
        return None, None

    def fetch_single_repo(self, token, relative_path):
        return object(), ["Python"]

class TestRepoManipulationService:

    @pytest.mark.asyncio
    async def test_add_repo_from_provider_success(self):

        claims = UserClaims(sub="u1")

        fake_repo_repository = FakeRepoStore()
        stub_git_label_store = StubGitLabelStore()

        stub_git_label_store.set_output(
            stub_git_label_store.get_by_token_id_and_user,
            output=GitLabelResponseDTO(
                token_value= "encrypted_token",
                git_hosting="github"
            )
        )

        stub_user_store = StubUserStore()
        stub_user_store.set_output(
            stub_user_store.find_by_user_id,
            output=UserResponseDTO(
                encryption_salt="salt=="
            )
        )

        service = RepoManipulationService(
            git_label_repository=stub_git_label_store,
            repo_repository=fake_repo_repository,
            user_repository=stub_user_store,
            encryption=StubEncryption(),
            git_fetcher=StubFetcher(),
        )

        await service.add_repo_from_provider(claims, "t1", AddRepositoryRequest(relative_path="owner/repo", repo_alias_name="xyz"))
        assert fake_repo_repository.data_store.get(claims.sub) # should have one saved repo

    @pytest.mark.asyncio
    async def test_add_repo_user_not_found(self):

        fake_repo_repository = FakeRepoStore()
        stub_git_label_store = StubGitLabelStore()

        stub_git_label_store.set_output(
            stub_git_label_store.get_by_token_id_and_user,
            output=GitLabelResponseDTO(
                token_value="encrypted_token", git_hosting="github"
            ),
        )

        stub_user_store = StubUserStore()
        stub_user_store.set_exception(
            stub_user_store.find_by_user_id,
            ResourceNotFound(reason=USER_RESOURCE_NOT_FOUND)
        )

        service = RepoManipulationService(
            git_label_repository=stub_git_label_store,
            repo_repository=fake_repo_repository,
            user_repository=stub_user_store,
            encryption=StubEncryption(),
            git_fetcher=StubFetcher(),
        )
        with pytest.raises(ResourceNotFound):
            await service.add_repo_from_provider(
                UserClaims(sub="missing_user"), "t1", AddRepositoryRequest(relative_path="p", repo_alias_name="xyz")
            )

    @pytest.mark.asyncio
    async def test_add_repo_label_not_found(self):

        fake_repo_repository = FakeRepoStore()
        stub_git_label_store = StubGitLabelStore()

        stub_git_label_store.set_exception(
            stub_git_label_store.get_by_token_id_and_user,
            ResourceNotFound(reason=GIT_LABEL_TOKEN_RESOURCE_NOT_FOUND)
        )

        

        stub_user_store = StubUserStore()
        stub_user_store.set_output(
            stub_user_store.find_by_user_id,
            output=UserResponseDTO(encryption_salt="salt=="),
        )

        service = RepoManipulationService(
            git_label_repository=stub_git_label_store,
            repo_repository=fake_repo_repository,
            user_repository=stub_user_store,
            encryption=StubEncryption(),
            git_fetcher=StubFetcher(),
        )
        with pytest.raises(ResourceNotFound):
            await service.add_repo_from_provider(
                UserClaims(sub="u1"), "missing_token", AddRepositoryRequest(relative_path="p", repo_alias_name="xyz")
            )

    @pytest.mark.asyncio
    async def test_add_repo_unsupported_provider(self):
        class BadFetcher(StubFetcher):
            def get_components(self, provider):
                return None, None

        fake_repo_repository = FakeRepoStore()
        stub_git_label_store = StubGitLabelStore()

        stub_git_label_store.set_output(
            stub_git_label_store.get_by_token_id_and_user,
            output=GitLabelResponseDTO(
                token_value="encrypted_token", git_hosting="github"
            ),
        )

        stub_user_store = StubUserStore()
        stub_user_store.set_output(
            stub_user_store.find_by_user_id,
            output=UserResponseDTO(encryption_salt="salt=="),
        )

        service = RepoManipulationService(
            git_label_repository=stub_git_label_store,
            repo_repository=fake_repo_repository,
            user_repository=stub_user_store,
            encryption=StubEncryption(),
            git_fetcher=BadFetcher(),
        )
        with pytest.raises(DevDoxAPIException) as exc:
            await service.add_repo_from_provider(UserClaims(sub="u1"), "t1", AddRepositoryRequest(relative_path="p", repo_alias_name="xyz"))

        assert exc

    @pytest.mark.asyncio
    async def test_add_repo_duplicate(self):
        repo_store = FakeRepoStore()

        repo_store.set_exception(repo_store.save, internal_error(
                **RepoErrors.REPOSITORY_ALREADY_EXIST.value
        ))
        stub_git_label_store = StubGitLabelStore()

        stub_git_label_store.set_output(
            stub_git_label_store.get_by_token_id_and_user,
            output=GitLabelResponseDTO(
                token_value="encrypted_token", git_hosting="github"
            ),
        )

        stub_user_store = StubUserStore()
        stub_user_store.set_output(
            stub_user_store.find_by_user_id,
            output=UserResponseDTO(encryption_salt="salt=="),
        )

        service = RepoManipulationService(
            git_label_repository=stub_git_label_store,
            repo_repository=repo_store,
            user_repository=stub_user_store,
            encryption=StubEncryption(),
            git_fetcher=StubFetcher(),
        )
        with pytest.raises(BadRequest):
            await service.add_repo_from_provider(UserClaims(sub="u1"), "t1", AddRepositoryRequest(relative_path="p", repo_alias_name="xyz"))
