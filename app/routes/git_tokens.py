"""
Token routes for the DevDox AI Portal API.

This module provides endpoints for retrieving Git tokens with their values masked
for security. It supports retrieving all tokens or filtering by a specific label.
"""

from fastapi import APIRouter, status, HTTPException, Body, Request
from typing import List, Dict, Any
from app.services.supabase_client import SupabaseClient
from app.utils.auth import AuthenticatedUserDTO
from app.utils.gitlab_manager import GitLabManager
from app.utils.github_manager import GitHubManager
from app.utils.encryption import EncryptionHelper
from app.utils.api_response import APIResponse
from app.utils import constants, CurrentUser
from app.config import GitHosting
from app.schemas.git_label import AddGitTokenSchema


async def handle_gitlab(payload: AddGitTokenSchema, encrypted_token: str):
    gitlab = GitLabManager(base_url="https://gitlab.com", access_token=payload.token_value)

    if not gitlab.auth_status:
        return APIResponse.error(message=constants.GITLAB_AUTH_FAILED)

    user = gitlab.get_user()
    if not user:
        return APIResponse.error(message=constants.GITLAB_USER_RETRIEVE_FAILED)

    client = SupabaseClient()
    res = client.insert(
        "git_label",
        {
            "label": payload.label,
            "user_id": payload.user_id,
            "git_hosting": payload.git_hosting,
            "token_value": encrypted_token,
            "masked_token": mask_token(payload.token_value),
            "username": user.get("username", "")
        }
    )

    if res:
        return APIResponse.success(message=constants.TOKEN_SAVED_SUCCESSFULLY, data={"id": str(res["id"])})
    return APIResponse.error(message=constants.GITLAB_TOKEN_SAVE_FAILED)


async def handle_github(payload: AddGitTokenSchema, encrypted_token: str):
    github = GitHubManager(access_token=payload.token_value)
    user = github.get_user()

    if not user:
        return APIResponse.error(message=constants.GITHUB_AUTH_FAILED, status_code=status.HTTP_400_BAD_REQUEST)

    client = SupabaseClient()
    res = client.insert(
        "git_label",
        {
            "label": payload.label,
            "user_id": payload.user_id,
            "git_hosting": payload.git_hosting,
            "token_value": encrypted_token,
            "masked_token": mask_token(payload.token_value),
            "username": user.get("login", "")
        }
    )

    if res:
        return APIResponse.success(message=constants.TOKEN_SAVED_SUCCESSFULLY,data={"id": str(res["id"])})
    return APIResponse.error(message=constants.GITHUB_TOKEN_SAVE_FAILED)


def mask_token(token: str) -> str:
    """
    Masks a token string by revealing only the first and last four characters.
    
    If the token is 8 characters or fewer, the entire token is replaced with asterisks. Returns an empty string if the input is empty.
    """
    if not token:
        return ""

    token_len = len(token)

    if token_len <= 8:
        return "*" * token_len

    prefix = token[:4]
    suffix = token[-4:]
    middle_mask = "*" * (token_len - 8)

    return f"{prefix}{middle_mask}{suffix}"


# Create router
router = APIRouter()


@router.get("/",  response_model=List[Dict[str, Any]],
            status_code=status.HTTP_200_OK,
            summary="Get all tokens for specific users",
            description="Retrieve a list of all tokens with masked values for specific users",
            )
async def get_tokens(user: AuthenticatedUserDTO = CurrentUser) -> List[Dict[str, Any]]:
    """
    Retrieves all stored tokens with masked values for API response.
    
    Returns:
        A list of dictionaries containing token metadata and masked token values.
    """
    try:
        client = SupabaseClient()
        res = client.filter(
            table="git_label",
            columns="label, id, git_hosting,masked_token, created_at",
            filters={ "user_id": user.id },
            order_by="created_at.desc"
        )

        return res


    except Exception as e:

        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=constants.SERVICE_UNAVAILABLE
        ) from e


@router.get("/{label}",  response_model=List[Dict[str, Any]],
            status_code=status.HTTP_200_OK,
            summary="Get tokens by label",
            description="Retrieve a list of all tokens with masked values")
async def get_token_by_label(label:str) ->List[Dict[str, Any]]:
    """
    Retrieves a token matching the specified label with its value masked.
    
    Args:
        label: The label identifying the token to retrieve.
    
    Returns:
        A list containing the formatted token dictionary with masked token value. The list is empty if no matching token is found.
    """
    try:
        client = SupabaseClient()
        res = client.filter(table="git_label",filters={"label": label}, columns="label, id, git_hosting, masked_token, created_at")
        return res
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Service temporarily unavailable. Please try again later."
        ) from e



@router.post("/", response_model=Dict[str, Any])
async def add_token(request: Request, payload: AddGitTokenSchema = Body(...)):
    token = payload.token_value.replace(" ", "")
    encrypted_token = EncryptionHelper.encrypt(token.replace(" ", "")) if token else ""
    if payload.git_hosting == GitHosting.GITLAB:
        return await handle_gitlab(payload, encrypted_token)

    if payload.git_hosting == GitHosting.GITHUB:
        return await handle_github(payload, encrypted_token)

    return APIResponse.error(message=constants.UNSUPPORTED_GIT_PROVIDER, status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,)


@router.delete("/{id}", response_model=Dict[str, Any],
            status_code=status.HTTP_200_OK,
            summary="Delete token by id",
            description="Delete token by id")
async def delete_token(id: str) -> Dict[str, Any]:
    """
     Deletes a token with the specified ID.

    Args:
         id: The unique identifier of the token to delete.

    Returns:
       A success response if the token was deleted, or an error response if the token was not found.
    """
    try:
        client = SupabaseClient()
        res = client.get_by_id(table="git_label",id_value=id )
        if res :
            client.delete(table="git_label",id_value=id )
            return APIResponse.success(
                message=constants.TOKEN_DELETED_SUCCESSFULLY
            )
        else:
            return APIResponse.error(
                message=constants.TOKEN_NOT_FOUND,
                status_code=status.HTTP_404_NOT_FOUND
            )


    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=constants.SERVICE_UNAVAILABLE
        ) from e