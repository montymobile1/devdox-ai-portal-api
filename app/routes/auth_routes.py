"""
Protected routes requiring authentication for the DevDox AI Portal API.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from typing import Dict, Any

from app.utils import CurrentUser

router = APIRouter()

@router.get("/me", response_model=Dict[str, Any])
async def get_current_user_profile(current_user: Dict[str, Any] = CurrentUser):
    """
    Get the current user's profile.
    
    Args:
        current_user (Dict[str, Any]): Current authenticated user.
        
    Returns:
        Dict[str, Any]: User profile data.
    """
    return {
        "id": current_user["id"],
        "email": current_user.get("email"),
        "name": current_user.get("name"),
        "profile": {
            "isAuthenticated": True,
            "role": "user"
        }
    }

@router.get("/repositories", response_model=Dict[str, Any])
async def get_user_repositories(current_user: Dict[str, Any] = CurrentUser):
    """
    Get the repositories for the current user.
    
    Args:
        current_user (Dict[str, Any]): Current authenticated user.
        
    Returns:
        Dict[str, Any]: User repositories.
    """
    # This would typically fetch repositories from Supabase or other storage
    return {
        "repositories": [
            {"id": 1, "name": "repo1", "url": "https://github.com/user/repo1"},
            {"id": 2, "name": "repo2", "url": "https://github.com/user/repo2"}
        ]
    }
