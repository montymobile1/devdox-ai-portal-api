"""
Token routes for the DevDox AI Portal API.

This module provides endpoints for retrieving Git tokens with their values masked
for security. It supports retrieving all tokens or filtering by a specific label.
"""

from fastapi import APIRouter, status, HTTPException, Body, Request
from typing import List, Dict, Any
from app.services.supabase_client import SupabaseClient
from app.utils.gitlab_manager import GitLabManager
from app.utils.github_manager import GitHubManager
from app.utils.encryption import EncryptionHelper
from app.utils.api_response import APIResponse
from app.config import GitHosting
from app.schemas.git_label import AddGitTokenSchema


async def handle_gitlab(payload: AddGitTokenSchema, encrypted_token: str):
    gitlab = GitLabManager(base_url="https://gitlab.com", access_token=payload.token_value)

    if not gitlab.auth_status:
        return APIResponse.error(message="Failed to authenticate with GitLab")

    user = gitlab.get_user()
    if not user:
        return APIResponse.error(message="Could not retrieve GitLab user")

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
        return APIResponse.success(message="Token saved successfully", data={"id": str(res["id"])})
    return APIResponse.error(message="Failed to save GitLab token")


async def handle_github(payload: AddGitTokenSchema, encrypted_token: str):
    github = GitHubManager(access_token=payload.token_value)
    user = github.get_user()

    if not user:
        return APIResponse.error(message="Failed to authenticate with GitHub", status_code=status.HTTP_400_BAD_REQUEST)

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
        return APIResponse.success(message="Token saved successfully",data={"id": str(res["id"])})
    return APIResponse.error(message="Failed to save GitHub token")


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


def format_token_response(token_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Formats raw token data by decrypting and masking the token value for API responses.
    
    If the token value is present, returns a dictionary containing the token's metadata and a masked version of the decrypted token value. Returns False if the token value is missing.
    """

    if token_data and token_data.get("token_value"):
        try:
            decrypt_data = EncryptionHelper.decrypt(token_data.get("token_value", ""))
        except Exception as e:
            print(f"Error decrypting token value: {e}")
            return False
        return {
            "id": token_data.get("id"),
            "label": token_data.get("label"),
            "git_hosting": token_data.get("git_hosting"),
            "token_value": mask_token(decrypt_data),
            "created_at": token_data.get("created_at"),
            "updated_at": token_data.get("updated_at")
        }
    else:
        return None
# Create router
router = APIRouter()


@router.get("/",  response_model=List[Dict[str, Any]],
            status_code=status.HTTP_200_OK,
            summary="Get all tokens",
            description="Retrieve a list of all tokens with masked values")
async def get_tokens() -> List[Dict[str, Any]]:
    """
    Retrieves all stored tokens with masked values for API response.
    
    Returns:
        A list of dictionaries containing token metadata and masked token values.
    """
    try:
        client = SupabaseClient()
        res = client.select(table="git_label", columns="label, id, git_hosting,token_value, created_at")

        formatted_tokens = [t for t in (format_token_response(token) for token in res) if t]
        return formatted_tokens


    except Exception as e:

        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Service temporarily unavailable. Please try again later."
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
        res = client.filter(table="git_label",filters={"label": label}, limit=1)
        formatted_tokens = [t for t in (format_token_response(token) for token in res) if t]

        return formatted_tokens
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

    return APIResponse.error(message="Unsupported git hosting provider", status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,)