import logging
from typing import Annotated, Optional

from fastapi import Depends
from models import GitLabel
from starlette import status
from starlette.responses import JSONResponse

from app.config import GitHosting
from app.exceptions.custom_exceptions import BadRequest, ResourceNotFound
from app.exceptions.exception_constants import (
    SERVICE_UNAVAILABLE,
    TOKEN_MISSING,
    USER_RESOURCE_NOT_FOUND,
)
from app.repositories.git_label_repository import TortoiseGitLabelStore
from app.repositories.user_repository import TortoiseUserStore
from app.schemas.basic import PaginationParams, RequiredPaginationParams
from app.schemas.git_label import GitLabelBase, GitLabelCreate, GitLabelResponse
from app.utils import constants
from app.utils.api_response import APIResponse
from app.utils.auth import AuthenticatedUserDTO, UserClaims
from app.utils.encryption import EncryptionHelper
from app.utils.github_manager import GitHubManager
from app.utils.gitlab_manager import GitLabManager

logger = logging.getLogger(__name__)

def format_git_label_data(raw_git_labels):
    formatted_data = []
    for git_label in raw_git_labels:
        
        formatted_data.append(
            GitLabelResponse(
                id= git_label.id,
                user_id=git_label.user_id,
                label= git_label.label,
                git_hosting= git_label.git_hosting,
                masked_token= git_label.masked_token,
                username= git_label.username,
                created_at= git_label.created_at.isoformat(),
                updated_at= git_label.updated_at.isoformat(),
                token_value=git_label.token_value,
            ).model_dump(exclude={"token_value", "user_id"})
        )
    
    return formatted_data


class GetGitLabelService:

    def __init__(
            self,
            label_store: TortoiseGitLabelStore
    ):
        self.label_store = label_store
    
    @classmethod
    def with_dependency(cls, label_store: Annotated[TortoiseGitLabelStore, Depends()],
    ) -> "GetGitLabelService":
        return cls(label_store)
    
    async def get_git_labels_by_user(self, pagination:RequiredPaginationParams, user_claims:UserClaims, git_hosting:Optional[str]):

        # Get total count
        total = await self.label_store.count_by_user_id(
            user_id=user_claims.sub,
            git_hosting=git_hosting
        )

        if total == 0:
            return {
                "items": [],
                "total": total,
                "page": pagination.offset  + 1,
                "size": pagination.limit,
            }

        git_labels = await self.label_store.get_by_user_id(
            offset=pagination.offset,
            limit=pagination.limit,
            user_id=user_claims.sub,
            git_hosting=git_hosting
        )

        # Format response data with masked tokens
        formatted_data = format_git_label_data(git_labels)

        return {
            "items": formatted_data,
            "total": total,
            "page": pagination.offset  + 1,
            "size": pagination.limit,
        }

    async def get_git_labels_by_label(self, pagination: PaginationParams, user_claims: UserClaims, label: str):

        git_labels = await self.label_store.get_by_user_id_and_label(
            offset=pagination.offset,
            limit=pagination.limit,
            user_id=user_claims.sub,
            label=label
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


async def handle_gitlab(payload: GitLabelCreate, encrypted_token: str) -> JSONResponse:
    """Handle GitLab token validation and storage"""
    gitlab = GitLabManager(
        base_url="https://gitlab.com", access_token=payload.token_value
    )

    if not gitlab.auth_status:
        return APIResponse.error(message=constants.GITLAB_AUTH_FAILED)

    user = gitlab.get_user()
    if not user:
        return APIResponse.error(message=constants.GITLAB_USER_RETRIEVE_FAILED)

    try:
        git_label = await GitLabel.create(
            label=payload.label,
            user_id=payload.user_id,
            git_hosting=payload.git_hosting,
            token_value=encrypted_token,
            masked_token=mask_token(payload.token_value),
            username=user.get("username", ""),
        )

        return APIResponse.success(
            message=constants.TOKEN_SAVED_SUCCESSFULLY, data={"id": str(git_label.id)}
        )
    except Exception:
        logger.exception(
            "Unexpected Failure while attempting to save GitLab token on Path = '[POST] /api/v1/git_tokens' -> handle_gitlab"
        )

        return APIResponse.error(
            message=SERVICE_UNAVAILABLE,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


async def handle_github(payload: GitLabelCreate, encrypted_token: str) -> JSONResponse:
    """Handle GitHub token validation and storage"""
    github = GitHubManager(access_token=payload.token_value)
    user = github.get_user()

    if not user:
        return APIResponse.error(
            message=constants.GITHUB_AUTH_FAILED,
            status_code=status.HTTP_400_BAD_REQUEST,
        )

    try:
        git_label = await GitLabel.create(
            label=payload.label,
            user_id=payload.user_id,
            git_hosting=payload.git_hosting,
            token_value=encrypted_token,
            masked_token=mask_token(payload.token_value),
            username=user.get("login", ""),
        )

        return APIResponse.success(
            message=constants.TOKEN_SAVED_SUCCESSFULLY, data={"id": str(git_label.id)}
        )
    except Exception:
        logger.exception(
            "Unexpected Failure while attempting to save GitHub token on Path = '[POST] /api/v1/git_tokens' -> handle_github"
        )
        return APIResponse.error(message=constants.GITHUB_TOKEN_SAVE_FAILED)


class PostGitLabelService:

    def __init__(
            self, user_store: TortoiseUserStore
    ):
        self.user_store = user_store

    @classmethod
    def with_dependency(
        cls, user_store: Annotated[TortoiseUserStore, Depends()],
    ) -> "PostGitLabelService":
        return cls(user_store)

    async def add_git_token(self, user_claims:AuthenticatedUserDTO, json_payload: GitLabelBase):
        
        token = json_payload.token_value.replace(" ", "")
        if not token:
            raise BadRequest(
                reason=TOKEN_MISSING
            )
        
        user = await self.user_store.get_by_user_id(user_id=user_claims.id)
        
        if not user:
            raise ResourceNotFound(
                reason=USER_RESOURCE_NOT_FOUND
            )
        
        encrypted_token = (
            EncryptionHelper().encrypt_for_user(token, user.encryption_salt)
        )
        
        new_payload: GitLabelCreate = GitLabelCreate(
            label=json_payload.label,
            user_id=user_claims.id,
            git_hosting=json_payload.git_hosting,
            token_value=json_payload.token_value,
        )
        
        if new_payload.git_hosting == GitHosting.GITLAB.value:
            return await handle_gitlab(new_payload, encrypted_token)
        elif new_payload.git_hosting == GitHosting.GITHUB.value:
            return await handle_github(new_payload, encrypted_token)
        else:
            return APIResponse.error(
                message=constants.UNSUPPORTED_GIT_PROVIDER,
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            )
