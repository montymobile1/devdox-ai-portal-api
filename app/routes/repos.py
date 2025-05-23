"""
Token routes for the DevDox AI Portal API.

This module provides endpoints for retrieving and adding Repos with their information.
"""

from fastapi import APIRouter, status, HTTPException, Depends
from typing import List, Dict, Any, Optional
from app.services.supabase_client import SupabaseClient
from app.schemas.basic import PaginationParams
from app.utils import constants


# Create router
router = APIRouter()


@router.get(
    "/{user_id}",
    response_model=List[Dict[str, Any]],
    status_code=status.HTTP_200_OK,
    summary="Get all repos",
    description="Retrieve a paginated list of repositories for a user",
)
async def get_repos(
    user_id: str, pagination: PaginationParams = Depends()
) -> List[Dict[str, Any]]:
    """
    Retrieves all repos based on user_id for API response.

    Returns:
        A list of dictionaries containing repo info.
    """
    try:
        client = SupabaseClient()
        res = client.filter(
            table="repo",
            filters={"user_id": user_id},
            limit=pagination.limit,
            order_by="created_at.desc",
        )

        return res

    except Exception as e:

        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=constants.SERVICE_UNAVAILABLE,
        ) from e
