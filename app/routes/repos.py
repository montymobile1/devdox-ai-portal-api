"""
Token routes for the DevDox AI Portal API.

This module provides endpoints for retrieving and adding Repos with their information.
"""

from fastapi import APIRouter, status, HTTPException
from typing import List, Dict, Any
from app.services.supabase_client import SupabaseClient
from app.utils import constants


# Create router
router = APIRouter()


@router.get(
    "/{user_id}",
    response_model=List[Dict[str, Any]],
    status_code=status.HTTP_200_OK,
    summary="Get all repos",
    description="Retrieve a list of all repos",
)
async def get_repos(user_id) -> List[Dict[str, Any]]:
    """
    Retrieves all repos based on user_id for API response.

    Returns:
        A list of dictionaries containing repo info.
    """
    try:
        client = SupabaseClient()
        res = client.filter(table="repo", filters={"user_id": user_id})

        return res

    except Exception as e:

        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=constants.SERVICE_UNAVAILABLE,
        ) from e
