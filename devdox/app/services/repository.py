from typing import Annotated, List, Tuple
from uuid import UUID, uuid4

from devdox_ai_git.repo_fetcher import RepoFetcher
from devdox_ai_git.schema.repo import NormalizedGitRepo
from fastapi import Depends

from app.exceptions import exception_constants
from app.exceptions.base_exceptions import DevDoxAPIException
from app.exceptions.local_exceptions import (
    BadRequest,
    ResourceNotFound,
)
from app.exceptions.exception_constants import (
    GIT_LABEL_TOKEN_RESOURCE_NOT_FOUND,
    REPOSITORY_ALREADY_EXISTS,
    TOKEN_NOT_FOUND,
    USER_RESOURCE_NOT_FOUND,
    REPOSITORY_TOKEN_RESOURCE_NOT_FOUND,
)
from models_src.dto.repo import RepoRequestDTO
from app.config import supabase_queue

from app.schemas.basic import RequiredPaginationParams
from app.schemas.repo import AddRepositoryRequest, GitRepoResponse, RepoResponse
from app.utils.auth import UserClaims
from app.utils.encryption import get_encryption_helper, FernetEncryptionHelper
from app.utils.git_managers import retrieve_git_fetcher_or_die
from models_src.exceptions.base_exceptions import DevDoxModelsException
from models_src.exceptions.utils import RepoErrors
from models_src.repositories.git_label import TortoiseGitLabelStore as GitLabelRepository
from models_src.repositories.repo import TortoiseRepoStore as RepoRepository
from models_src.repositories.user import TortoiseUserStore as UserRepository

class RepoQueryService:
    def __init__(
        self,
        repo_repository: Annotated[RepoRepository, Depends()],
        git_label_repository: Annotated[GitLabelRepository, Depends()],
    ):
        self.repo_repository = repo_repository
        self.git_label_repository = git_label_repository

    async def get_all_user_repositories(
        self, user: UserClaims, pagination: RequiredPaginationParams
    ) -> Tuple[int, List[RepoResponse]]:

        total_count = await self.repo_repository.count_by_user_id(user.sub)

        if total_count == 0:
            return total_count, []

        repos = await self.repo_repository.find_all_by_user_id(
            user_id=user.sub, offset=pagination.offset, limit=pagination.limit
        )

        token_ids = {repo.token_id for repo in repos if repo.token_id}
        labels = await self.git_label_repository.find_git_hostings_by_ids(token_ids)
        label_map = {str(label["id"]): label["git_hosting"] for label in labels}

        repo_responses = []

        for rp in repos:
            if val := label_map.get(str(rp.token_id)):
                rp.git_hosting = val

            repo_responses.append(RepoResponse.model_validate(rp, from_attributes=True))

        return total_count, repo_responses


class RepoProviderService:
    def __init__(
        self,
        git_label_repository: Annotated[GitLabelRepository, Depends()],
        user_repository: Annotated[UserRepository, Depends()],
        encryption: Annotated[FernetEncryptionHelper, Depends(get_encryption_helper)],
        git_fetcher: Annotated[RepoFetcher, Depends()]
    ):
        self.git_label_repository = git_label_repository
        self.user_repository = user_repository
        self.encryption = encryption
        self.git_fetcher = git_fetcher

    async def get_all_provider_repos(
        self,
        token_id: str,
        user_claims: UserClaims,
        pagination: RequiredPaginationParams,
    ) -> Tuple[int, List[GitRepoResponse]]:

        retrieved_user_data = await self.user_repository.find_by_user_id(user_claims.sub)

        if retrieved_user_data is None:
            raise ResourceNotFound(reason=USER_RESOURCE_NOT_FOUND)

        label = await self.git_label_repository.find_by_token_id_and_user(
            token_id=token_id, user_id=user_claims.sub
        )
        if label is None:
            raise ResourceNotFound(reason=TOKEN_NOT_FOUND)

        decrypted_label_token = self.encryption.decrypt_for_user(
            label.token_value,
            salt_b64=self.encryption.decrypt(retrieved_user_data.encryption_salt),
        )

        fetcher, response_mapper = retrieve_git_fetcher_or_die(
            store=self.git_fetcher, provider=label.git_hosting
        )

        fetched_data = fetcher.fetch_user_repositories(
            decrypted_label_token, pagination.offset, pagination.limit
        )

        if fetched_data.get("data_count", 0) == 0:
            return 0, []

        transformed_response = [
            response_mapper.from_git(r) for r in fetched_data.get("data", [])
        ]

        return fetched_data["data_count"], transformed_response


async def retrieve_user_by_id_or_die(user_repository_instance: UserRepository, user_id):
    retrieved_user_data = await user_repository_instance.find_by_user_id(user_id)

    if retrieved_user_data is None:
        raise ResourceNotFound(reason=USER_RESOURCE_NOT_FOUND)

    return retrieved_user_data


async def retrieve_git_label_or_die(repository:GitLabelRepository, id, user_id):
    retrieved_git_label = await repository.find_by_token_id_and_user(id, user_id)
    if retrieved_git_label is None:
        raise ResourceNotFound(reason=GIT_LABEL_TOKEN_RESOURCE_NOT_FOUND)

    return retrieved_git_label


async def retrieve_repo_by_id(repo_repository_instance: RepoRepository, id):
    try:
        repo_info = await repo_repository_instance.get_by_id(id)
    except DevDoxModelsException as e:
        if e.error_type == RepoErrors.REPOSITORY_DOESNT_EXIST.value["error_type"]:
            raise DevDoxAPIException(
                user_message=exception_constants.SERVICE_UNAVAILABLE,
                log_message=exception_constants.REPOSITORY_DOESNT_EXIST_TITLE,
                error_type=exception_constants.REPOSITORY_DOESNT_EXIST_TITLE,
                log_level="exception"
            ) from e
        
        raise
    
    if repo_info is None:
        raise ResourceNotFound(reason=REPOSITORY_TOKEN_RESOURCE_NOT_FOUND)

    return repo_info


class RepoManipulationService:
    def __init__(
        self,
        git_label_repository: Annotated[GitLabelRepository, Depends()],
        repo_repository: Annotated[RepoRepository, Depends()],
        user_repository: Annotated[UserRepository, Depends()],
        encryption: Annotated[FernetEncryptionHelper, Depends(get_encryption_helper)],
        git_fetcher: Annotated[RepoFetcher, Depends()]
    ):
        self.git_label_repository = git_label_repository
        self.user_store = user_repository
        self.encryption = encryption
        self.git_fetcher = git_fetcher
        self.repo_repository = repo_repository

    async def add_repo_from_provider(
        self, user_claims: UserClaims, token_id: str, payload: AddRepositoryRequest
    ) -> str:

        retrieved_user_data = await retrieve_user_by_id_or_die(
            self.user_store, user_claims.sub
        )
        retrieved_git_label = await retrieve_git_label_or_die(
            self.git_label_repository, token_id, user_claims.sub
        )
        fetcher, fetcher_data_mapper = retrieve_git_fetcher_or_die(
            self.git_fetcher, retrieved_git_label.git_hosting
        )

        decrypted_label_token = self.encryption.decrypt_for_user(
            retrieved_git_label.token_value,
            salt_b64=self.encryption.decrypt(retrieved_user_data.encryption_salt),
        )

        repo_data, languages = fetcher.fetch_single_repo(
            decrypted_label_token, payload.relative_path
        )

        transformed_data: NormalizedGitRepo = fetcher_data_mapper.from_git(repo_data)

        try:
            saved_repo = await self.repo_repository.save(
                RepoRequestDTO(
                    user_id=user_claims.sub,
                    token_id=token_id,
                    repo_id=transformed_data.id,
                    repo_name=transformed_data.repo_name,
                    description=transformed_data.description,
                    html_url=transformed_data.html_url,
                    relative_path=transformed_data.relative_path,
                    default_branch=transformed_data.default_branch,
                    forks_count=transformed_data.forks_count,
                    stargazers_count=transformed_data.stargazers_count,
                    is_private=transformed_data.private,
                    visibility=transformed_data.visibility,
                    size=transformed_data.size,
                    repo_created_at=transformed_data.repo_created_at,
                    language=languages,
                    repo_alias_name=payload.repo_alias_name,
                    repo_user_reference=payload.repo_user_reference
                )
            )
            
            return str(saved_repo.id)

        except DevDoxModelsException as e:
            if e.error_type == RepoErrors.REPOSITORY_ALREADY_EXIST.value["error_type"]:
                raise BadRequest(reason=REPOSITORY_ALREADY_EXISTS) from e
            raise


    async def analyze_repo(self, user_claims: UserClaims, id: str | UUID) -> None:
        repo_info = await retrieve_repo_by_id(self.repo_repository, id)
        token_info = await retrieve_git_label_or_die(
            self.git_label_repository, repo_info.token_id, user_claims.sub
        )

        payload = {
            "job_type": "analyze",
            "payload": {
                "branch": repo_info.default_branch,
                "repo_id": str(repo_info.repo_id),
                "token_id": str(token_info.id),
                "config": {},
                "user_id": str(user_claims.sub),
                "priority": 1,
                "git_token": str(token_info.id),
                "token_value": token_info.token_value,
                "git_provider": token_info.git_hosting,
                "context_id": uuid4().hex,
            },
        }

        _ = await supabase_queue.enqueue(
            "processing",
            payload=payload,
            priority=1,
            job_type="analyze",
            user_id=user_claims.sub,
        )
