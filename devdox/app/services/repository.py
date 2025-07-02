from typing import List, Tuple

from fastapi import Depends
from tortoise.exceptions import IntegrityError

from app.exceptions.custom_exceptions import (
    BadRequest,
    ResourceNotFound,
)
from app.exceptions.exception_constants import (
    GIT_LABEL_TOKEN_RESOURCE_NOT_FOUND,
    REPOSITORY_ALREADY_EXISTS,
    USER_RESOURCE_NOT_FOUND,
)
from models import Repo
from app.repositories.git_label import TortoiseGitLabelStore
from app.repositories.repo import TortoiseRepoStore
from app.repositories.user import TortoiseUserStore
from app.schemas.basic import RequiredPaginationParams
from app.schemas.repo import GitRepoResponse, RepoResponse
from app.utils.auth import UserClaims
from app.utils.encryption import get_encryption_helper, FernetEncryptionHelper
from app.utils.git_managers import retrieve_git_fetcher_or_die
from app.utils.repo_fetcher import RepoFetcher


class RepoQueryService:
    def __init__(
        self,
        repo_store=Depends(TortoiseRepoStore),
        gl_store=Depends(TortoiseGitLabelStore),
    ):
        self.repo_store = repo_store
        self.gl_store = gl_store

    async def get_all_user_repositories(
        self, user: UserClaims, pagination: RequiredPaginationParams
    ) -> Tuple[int, List[RepoResponse]]:

        total_count = await self.repo_store.count_by_user(user.sub)

        if total_count == 0:
            return total_count, []

        repos = await self.repo_store.get_all_by_user(
            user.sub, pagination.offset, pagination.limit
        )

        token_ids = {repo.token_id for repo in repos if repo.token_id}
        labels = await self.gl_store.get_git_hosting_map_by_token_id(token_ids)
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
        label_store: TortoiseGitLabelStore = Depends(),
        user_store: TortoiseUserStore = Depends(),
        encryption: FernetEncryptionHelper = Depends(get_encryption_helper),
        git_fetcher: RepoFetcher = Depends(),
    ):
        self.label_store = label_store
        self.user_store = user_store
        self.encryption = encryption
        self.git_fetcher = git_fetcher

    async def get_all_provider_repos(
        self,
        token_id: str,
        user_claims: UserClaims,
        pagination: RequiredPaginationParams,
    ) -> Tuple[int, List[GitRepoResponse]]:

        retrieved_user_data = await self.user_store.get_by_user_id(user_claims.sub)

        if retrieved_user_data is None:
            raise ResourceNotFound(reason="User not found")

        label = await self.label_store.get_by_token_id_and_user(
            token_id, user_claims.sub
        )
        if label is None:
            raise ResourceNotFound(reason="Token not found")

        decrypted_label_token = self.encryption.decrypt_for_user(
            label.token_value, salt_b64=retrieved_user_data.encryption_salt
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


async def retrieve_user_by_id_or_die(store: TortoiseUserStore, user_id):
    retrieved_user_data = await store.get_by_user_id(user_id)

    if retrieved_user_data is None:
        raise ResourceNotFound(reason=USER_RESOURCE_NOT_FOUND)

    return retrieved_user_data


async def retrieve_git_label_by_id_and_user_or_die(store, id, user_id):
    retrieved_git_label = await store.get_by_token_id_and_user(id, user_id)
    if retrieved_git_label is None:
        raise ResourceNotFound(reason=GIT_LABEL_TOKEN_RESOURCE_NOT_FOUND)

    return retrieved_git_label


class RepoManipulationService:
    def __init__(
        self,
        label_store: TortoiseGitLabelStore = Depends(),
        repo_store: TortoiseRepoStore = Depends(),
        user_store: TortoiseUserStore = Depends(),
        encryption: FernetEncryptionHelper = Depends(get_encryption_helper),
        git_fetcher: RepoFetcher = Depends(),
    ):
        self.label_store = label_store
        self.user_store = user_store
        self.encryption = encryption
        self.git_fetcher = git_fetcher
        self.repo_store = repo_store

    async def add_repo_from_provider(
        self, user_claims: UserClaims, token_id: str, relative_path: str
    ) -> None:

        retrieved_user_data = await retrieve_user_by_id_or_die(
            self.user_store, user_claims.sub
        )
        retrieved_git_label = await retrieve_git_label_by_id_and_user_or_die(
            self.label_store, token_id, user_claims.sub
        )
        fetcher, fetcher_data_mapper = retrieve_git_fetcher_or_die(
            self.git_fetcher, retrieved_git_label.git_hosting
        )

        decrypted_label_token = self.encryption.decrypt_for_user(
            retrieved_git_label.token_value,
            salt_b64=retrieved_user_data.encryption_salt,
        )

        repo_data, languages = fetcher.fetch_single_repo(
            decrypted_label_token, relative_path
        )

        transformed_data: GitRepoResponse = fetcher_data_mapper.from_git(repo_data)

        try:
            _ = await self.repo_store.create_new_repo(
                Repo(
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
                )
            )

        except IntegrityError:
            raise BadRequest(reason=REPOSITORY_ALREADY_EXISTS)
