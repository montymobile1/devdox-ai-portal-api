"""
Token routes for the DevDox AI Portal API.

This module provides endpoints for retrieving Git tokens with their values masked
for security. It supports retrieving all tokens or filtering by a specific label.
"""

from fastapi import APIRouter, status, HTTPException
from typing import List, Dict, Any
from app.services.supabase_client import SupabaseClient
from app.utils.encryption import EncryptionHelper


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
        return None
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
    try:
        client = SupabaseClient()
        res = client.select(table="git_label", columns="label, id, git_hosting,token_value, created_at")

        formatted_tokens = [t for t in (format_token_response(token) for token in res) if t]
        return formatted_tokens

    except Exception as e:
        raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail = "Service temporarily unavailable. Please try again later." )


@router.get("/{label}",  response_model=List[Dict[str, Any]],
            status_code=status.HTTP_200_OK,
            summary="Get tokens by label",
            description="Retrieve a list of all tokens with masked values")
async def get_token_by_label(label:str) ->List[Dict[str, Any]]:
    """
    Get a token by label

    Returns:
        List[Dict[str, Any]]: A list of token items with masked values

    Raises:
        HTTPException: 500 if database error occurs
    """
    client = SupabaseClient()
    res = client.filter(table="git_label",filters={"label": label}, limit=1)
    formatted_tokens = [format_token_response(token) for token in res]
    return formatted_tokens

