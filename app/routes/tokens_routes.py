"""
Token routes for the DevDox AI Portal API.
"""
from fastapi import Body
from fastapi import Request
from fastapi import APIRouter, Depends, HTTPException, status
from typing import List, Dict, Any
from app.services.supabase_client import SupabaseClient
from app.utils.gitlab_manager import GitLabManager
from app.utils.github_manager import GitHubManager
from app.utils.encryption import EncryptionHelper
from app.utils.api_response import APIResponse
from app.config import GitHosting
from app.models.git_label import AddGitlab


def mask_token(token: str) -> str:
    """
    Mask a token value for security purposes.
    Shows first 4 and last 4 characters, masks the middle with asterisks.
    Maintains the same total length as the original token.

    Args:
        token (str): The token to mask

    Returns:
        str: Masked token string
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
    Format token data for API response.

    Args:
        token_data (Dict[str, Any]): Raw token data from database

    Returns:
        Dict[str, Any]: Formatted token data for response
    """

    if (token_data.get("token_value")):
        return {
            "id": token_data.get("id"),
            "label": token_data.get("label"),
            "git_hosting": token_data.get("git_hosting"),
            "token_value": mask_token(EncryptionHelper.decrypt(token_data.get("token_value", ""))),
            "created_at": token_data.get("created_at"),
            "updated_at": token_data.get("updated_at")
        }
    else:
        return False
# Create router
router = APIRouter()


@router.get("/",  response_model=List[Dict[str, Any]],
            status_code=status.HTTP_200_OK,
            summary="Get all tokens",
            description="Retrieve a list of all tokens with masked values")
async def get_tokens() -> List[Dict[str, Any]]:
    """
    Get a list of all tokens.

    Returns:
        List[Dict[str, Any]]: A list of token items with masked values

    Raises:
        HTTPException: 500 if database error occurs
    """
    client = SupabaseClient()
    res = client.select(table="git_label", columns="label, id, git_hosting,token_value, created_at")
    formatted_tokens = [format_token_response(token) for token in res]
    return formatted_tokens

@router.post("/", response_model=Dict[str, Any])
async def add_token(request:Request, payload: AddGitlab= Body(...)):
    """
    Get a specific example by ID.
    
    Args:
        example_id (int): The ID of the example to retrieve.
        
    Returns:
        Dict[str, Any]: The example details.
        
    Raises:
        HTTPException: If the example is not found.
    """
    encrypt_token = EncryptionHelper.encrypt(payload.token_value) if payload.token_value else ""
    if payload.git_hosting == GitHosting.GITLAB:
        gitlab_info = GitLabManager(base_url="https://gitlab.com", access_token=payload.token_value)
        if gitlab_info.auth_status:
            gitlab_user = gitlab_info.get_user()
            if gitlab_user:

                client = SupabaseClient()
                res = client.insert("git_label", {"label": payload.label, "user_id": payload.user_id,
                                                  "git_hosting": payload.git_hosting, "token_value": encrypt_token,
                                                  "username": gitlab_user.get("username","")})
                if res:
                    return APIResponse.success(message="", data={"id": str(res['id'])})
        else:
            return APIResponse.error(message="Failed to authenticate with Gitlab")
    elif payload.git_hosting == GitHosting.GITHUB:
        github_info = GitHubManager(access_token=payload.token_value)
        github_user = github_info.get_user()
        if github_user:

            # Successfully validated GitHub credentials

            client = SupabaseClient()
            res = client.insert("git_label", {"label": payload.label, "user_id":payload.user_id,"git_hosting": payload.git_hosting, "token_value": encrypt_token, "username": github_user.get("login", "")})


            if res:
                return APIResponse.success(message="", data={"id": str(res['id'])})
            return APIResponse.success(message="GitHub credentials saved successfully")
        else:
            return APIResponse.error(message="Failed to authenticate with GitHub")

    else:
        return APIResponse.error(message="Unsupported git hosting provider")


