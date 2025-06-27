import logging
import uuid
from typing import Annotated, Optional

from fastapi import Depends
from models import GitLabel
from tortoise.exceptions import IntegrityError

from app.exceptions.custom_exceptions import BadRequest, ResourceNotFound
from app.exceptions.exception_constants import (
    GENERIC_ALREADY_EXIST,
    TOKEN_MISSING,
    TOKEN_NOT_FOUND,
    USER_RESOURCE_NOT_FOUND,
)
from app.repositories.git_label_repository import TortoiseGitLabelStore
from app.repositories.user_repository import TortoiseUserStore
from app.schemas.basic import PaginationParams, RequiredPaginationParams
from app.schemas.git_label import GitLabelBase, GitLabelDBCreateDTO, GitLabelResponse
from app.schemas.repo import GitUserResponse
from app.utils.auth import UserClaims
from app.utils.encryption import (
    FernetEncryptionHelper,
    get_encryption_helper,
)
from app.utils.git_managers import retrieve_git_fetcher_or_die
from app.utils.repo_fetcher import RepoFetcher

logger = logging.getLogger(__name__)


def format_git_label_data(raw_git_labels):
    formatted_data = []
    for git_label in raw_git_labels:

        formatted_data.append(
            GitLabelResponse(
                id=git_label.id,
                user_id=git_label.user_id,
                label=git_label.label,
                git_hosting=git_label.git_hosting,
                masked_token=git_label.masked_token,
                username=git_label.username,
                created_at=git_label.created_at.isoformat(),
                updated_at=git_label.updated_at.isoformat(),
                token_value=git_label.token_value,
            ).model_dump(exclude={"token_value", "user_id"})
        )

    return formatted_data


class GetGitLabelService:

    def __init__(self, label_store: TortoiseGitLabelStore):
        self.label_store = label_store

    @classmethod
    def with_dependency(
        cls,
        label_store: Annotated[TortoiseGitLabelStore, Depends()],
    ) -> "GetGitLabelService":
        return cls(label_store)

    async def get_git_labels_by_user(
        self,
        pagination: RequiredPaginationParams,
        user_claims: UserClaims,
        git_hosting: Optional[str],
    ):

        # Get total count
        total = await self.label_store.count_by_user_id(
            user_id=user_claims.sub, git_hosting=git_hosting
        )

        if total == 0:
            return {
                "items": [],
                "total": total,
                "page": pagination.offset + 1,
                "size": pagination.limit,
            }

        git_labels = await self.label_store.get_by_user_id(
            offset=pagination.offset,
            limit=pagination.limit,
            user_id=user_claims.sub,
            git_hosting=git_hosting,
        )

        # Format response data with masked tokens
        formatted_data = format_git_label_data(git_labels)

        return {
            "items": formatted_data,
            "total": total,
            "page": pagination.offset + 1,
            "size": pagination.limit,
        }

    async def get_git_labels_by_label(
        self, pagination: PaginationParams, user_claims: UserClaims, label: str
    ):

        git_labels = await self.label_store.get_by_user_id_and_label(
            offset=pagination.offset,
            limit=pagination.limit,
            user_id=user_claims.sub,
            label=label,
        )

        formatted_data = format_git_label_data(git_labels)

        return formatted_data


def mask_token(token: str) -> str:
    """
    Masks a token string by revealing only the first and last four characters.

    If the token is 8 characters or fewer, the entire token is replaced with asterisks.
    Returns an empty string if the input is empty.
    """
    if not token or token.replace(" ", "") == "":
        return ""

    token_len = len(token)

    if token_len <= 8:
        return "*" * token_len

    prefix = token[:4]
    suffix = token[-4:]
    middle_mask = "*" * (token_len - 8)

    return f"{prefix}{middle_mask}{suffix}"


class PostGitLabelService:

    def __init__(
        self,
        user_store: TortoiseUserStore,
        label_store: TortoiseGitLabelStore,
        crypto_store: FernetEncryptionHelper,
        git_manager: RepoFetcher,
    ):
        self.user_store = user_store
        self.label_store = label_store
        self.crypto_store = crypto_store
        self.git_manager = git_manager

    @classmethod
    def with_dependency(
        cls,
        user_store: Annotated[TortoiseUserStore, Depends()],
        label_store: Annotated[TortoiseGitLabelStore, Depends()],
        crypto_store: Annotated[FernetEncryptionHelper, Depends(get_encryption_helper)],
        git_manager: Annotated[RepoFetcher, Depends()],
    ) -> "PostGitLabelService":
        return cls(
            user_store=user_store,
            label_store=label_store,
            crypto_store=crypto_store,
            git_manager=git_manager,
        )

    async def add_git_token(self, user_claims: UserClaims, json_payload: GitLabelBase):

        token = json_payload.token_value.replace(" ", "")
        if not token:
            raise BadRequest(reason=TOKEN_MISSING)

        user = await self.user_store.get_by_user_id(user_id=user_claims.sub)

        if not user:
            raise ResourceNotFound(reason=USER_RESOURCE_NOT_FOUND)

        encrypted_token = self.crypto_store.encrypt_for_user(
            token, user.encryption_salt
        )

        fetcher, response_transformer = retrieve_git_fetcher_or_die(
            store=self.git_manager, provider=json_payload.git_hosting
        )

        retrieved_git_user = fetcher.fetch_repo_user(token=json_payload.token_value)

        if not retrieved_git_user:
            raise ResourceNotFound(reason=TOKEN_MISSING)

        transformed_data: GitUserResponse = response_transformer.from_git_user(
            retrieved_git_user
        )

        try:
            created_label = await self.label_store.create_new(
                GitLabelDBCreateDTO(
                    label=json_payload.label,
                    user_id=user_claims.sub,
                    git_hosting=json_payload.git_hosting,
                    token_value=encrypted_token,
                    masked_token=mask_token(json_payload.token_value),
                    username=transformed_data.username,
                )
            )
        except IntegrityError as e:
            raise BadRequest(reason=GENERIC_ALREADY_EXIST) from e

        return created_label


class DeleteGitLabelService:

    def __init__(
        self,
        label_store: TortoiseGitLabelStore,
    ):
        self.label_store = label_store

    @classmethod
    def with_dependency(
        cls,
        label_store: Annotated[TortoiseGitLabelStore, Depends()],
    ) -> "DeleteGitLabelService":
        return cls(
            label_store=label_store,
        )

    async def delete_by_git_label_id(
        self, user_claims: UserClaims, git_label_id: uuid.UUID
    ) -> int:
        deleted_label = await self.label_store.delete_by_id_and_user_id(
            label_id=git_label_id, user_id=user_claims.sub
        )

        if deleted_label <= 0:
            raise ResourceNotFound(reason=TOKEN_NOT_FOUND)

        return deleted_label
