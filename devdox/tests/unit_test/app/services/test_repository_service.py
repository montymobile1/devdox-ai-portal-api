import datetime
import random
import uuid

import pytest
from devdox_ai_git.schema.repo import NormalizedGitRepo
from models_src.dto.repo import GitHosting, RepoResponseDTO

from app.exceptions.exception_constants import (
    GIT_LABEL_TOKEN_RESOURCE_NOT_FOUND,
    USER_RESOURCE_NOT_FOUND,
)
from models_src.dto.git_label import GitLabelResponseDTO
from models_src.dto.user import UserResponseDTO
from models_src.exceptions.utils import internal_error, RepoErrors

from app.schemas.basic import RequiredPaginationParams
from app.services.repository import RepoManipulationService, RepoQueryService
from app.schemas.repo import AddRepositoryRequest
from app.utils.auth import UserClaims
from app.exceptions.local_exceptions import (
    BadRequest,
    ResourceNotFound,
)
from app.exceptions.base_exceptions import DevDoxAPIException
from models_src.test_doubles.repositories.git_label import FakeGitLabelStore, StubGitLabelStore
from models_src.test_doubles.repositories.repo import FakeRepoStore
from models_src.test_doubles.repositories.user import StubUserStore


class StubEncryption:
    def decrypt_for_user(self, encrypted, salt_b64):
        return "decrypted_token"

    def decrypt(self, encrypted_text: str):
        return "decrypt"


class StubTransformer:
    def from_git(self, data):
        return NormalizedGitRepo(
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
        if provider in [GitHosting.GITLAB.value, GitHosting.GITHUB.value]:
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
            stub_git_label_store.find_by_token_id_and_user,
            output=GitLabelResponseDTO(
                token_value= "encrypted_token",
                git_hosting=GitHosting.GITHUB.value
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
            stub_git_label_store.find_by_token_id_and_user,
            output=GitLabelResponseDTO(
                token_value="encrypted_token", git_hosting=GitHosting.GITHUB.value
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
            stub_git_label_store.find_by_token_id_and_user,
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
            stub_git_label_store.find_by_token_id_and_user,
            output=GitLabelResponseDTO(
                token_value="encrypted_token", git_hosting=GitHosting.GITHUB.value
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
            stub_git_label_store.find_by_token_id_and_user,
            output=GitLabelResponseDTO(
                token_value="encrypted_token", git_hosting=GitHosting.GITHUB.value
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

class TestRepoQueryService__GetAllUserRepositories:
    
    @pytest.mark.asyncio
    async def test_with_no_repo(self):
        repo_store = FakeRepoStore()
        fake_git_label_store = FakeGitLabelStore()
        
        service = RepoQueryService(
            git_label_repository=fake_git_label_store,
            repo_repository=repo_store
        )
        
        result = await service.get_all_user_repositories(UserClaims(sub="u1"), RequiredPaginationParams(limit=10, offset=0))
        
        assert result == (0, [])
    
    @pytest.mark.asyncio
    async def test_with_no_git_label_data(self):
        user_claim = UserClaims(sub="1")
        
        repo_store = FakeRepoStore()
        fake_git_label_store = FakeGitLabelStore()
        
        current_datetime = datetime.datetime.now(datetime.timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
        
        repo_fakes = []
        
        MAX_USER = 2
        MAX_GIT_LABEL = 4
        MAX_REPOS = 3
        
        for user_id in range(MAX_USER):
            
            clerk_id = user_id + 1
            
            for git_label in range(MAX_GIT_LABEL):
                
                random_git_hosting = random.choice(list(GitHosting))
                random_git_hosting_value = random_git_hosting.value
                
                git_label_record = GitLabelResponseDTO(
                    id=uuid.uuid4(),
                    user_id=f"{clerk_id}",
                    label=f"Label {clerk_id}-{git_label}",
                    git_hosting=random_git_hosting_value,
                    username=f"{random_git_hosting_value} username",
                    token_value=f"Hashed {clerk_id}-{git_label} actual token",
                    masked_token=f"Masked {clerk_id}-{git_label} actual token",
                    created_at=current_datetime + datetime.timedelta(hours=git_label),
                )
                
                for repo in range(MAX_REPOS):
                    
                    repo_record = RepoResponseDTO(
                        id=uuid.uuid4(),
                        user_id=f"{clerk_id}",
                        repo_id=f"{clerk_id}-{git_label}-{repo}",
                        repo_name=f"repo_name_{clerk_id}-{git_label}-{repo}",
                        token_id=str(git_label_record.id),
                        html_url=f"html_url_{clerk_id}-{git_label}-{repo}",
                        default_branch=f"default_branch_{clerk_id}-{git_label}-{repo}",
                        forks_count=1,
                        stargazers_count=1,
                        is_private=True,
                        created_at=current_datetime + datetime.timedelta(hours=git_label),
                        updated_at=current_datetime + datetime.timedelta(hours=git_label),
                    )
                    
                    repo_fakes.append(repo_record)
        
        repo_store.set_fake_data(repo_fakes)
        
        service = RepoQueryService(
            git_label_repository=fake_git_label_store,
            repo_repository=repo_store
        )
        
        LIMIT = 10
        OFFSET = 0
        
        pagination = RequiredPaginationParams(limit=LIMIT, offset=OFFSET)
        
        result = await service.get_all_user_repositories(user_claim, pagination)
        
        assert result[0] == MAX_GIT_LABEL * MAX_REPOS
        assert len(result[1]) == LIMIT
        assert {(str(res.id), res.git_hosting) for res in result[1]} <= {(str(res.id), None) for res in repo_fakes}
    
    @pytest.mark.asyncio
    async def test_with_all_data(self):
        user_claim = UserClaims(sub="1")
        
        repo_store = FakeRepoStore()
        fake_git_label_store = FakeGitLabelStore()
        
        current_datetime = datetime.datetime.now(datetime.timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
        
        git_label_fakes = []
        repo_fakes = []
        
        MAX_USER = 2
        MAX_GIT_LABEL = 4
        MAX_REPOS = 3
        
        for user_id in range(MAX_USER):
            
            clerk_id = user_id + 1
            
            for git_label in range(MAX_GIT_LABEL):
                
                random_git_hosting = random.choice(list(GitHosting))
                random_git_hosting_value = random_git_hosting.value
                
                git_label_record = GitLabelResponseDTO(
                    id=uuid.uuid4(),
                    user_id=f"{clerk_id}",
                    label=f"Label {clerk_id}-{git_label}",
                    git_hosting=random_git_hosting_value,
                    username=f"{random_git_hosting_value} username",
                    token_value=f"Hashed {clerk_id}-{git_label} actual token",
                    masked_token=f"Masked {clerk_id}-{git_label} actual token",
                    created_at=current_datetime + datetime.timedelta(hours=git_label),
                )
                
                git_label_fakes.append(git_label_record)
                
                for repo in range(MAX_REPOS):
                    
                    repo_record = RepoResponseDTO(
                        id=uuid.uuid4(),
                        user_id=f"{clerk_id}",
                        repo_id=f"{clerk_id}-{git_label}-{repo}",
                        repo_name=f"repo_name_{clerk_id}-{git_label}-{repo}",
                        token_id=str(git_label_record.id),
                        html_url=f"html_url_{clerk_id}-{git_label}-{repo}",
                        default_branch=f"default_branch_{clerk_id}-{git_label}-{repo}",
                        forks_count=1,
                        stargazers_count=1,
                        is_private=True,
                        created_at=current_datetime + datetime.timedelta(hours=git_label),
                        updated_at=current_datetime + datetime.timedelta(hours=git_label),
                    )
                    
                    repo_fakes.append(repo_record)
        
        fake_git_label_store.set_fake_data(git_label_fakes)
        repo_store.set_fake_data(repo_fakes)
        
        service = RepoQueryService(
            git_label_repository=fake_git_label_store,
            repo_repository=repo_store
        )
        
        LIMIT = 10
        OFFSET = 0
        
        pagination = RequiredPaginationParams(limit=LIMIT, offset=OFFSET)
        
        result = await service.get_all_user_repositories(user_claim, pagination)
        
        assert result[0] == MAX_GIT_LABEL * MAX_REPOS
        assert len(result[1]) == LIMIT
        
        assert {str(res.id) for res in result[1]} <= {str(res.id) for res in repo_fakes}
        assert all(res.git_hosting is not None for res in result[1])
    
    