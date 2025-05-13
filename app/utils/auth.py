"""
Clerk authentication utility for the DevDox AI Portal API.
"""

import jwt
from fastapi import Depends, HTTPException, Request, status
from typing import Dict, Optional

from app.config import settings

def get_clerk_jwt_from_headers(request: Request) -> Optional[str]:
    """
    Extract JWT token from Authorization header.
    
    Args:
        request (Request): FastAPI request object.
        
    Returns:
        Optional[str]: JWT token if present, None otherwise.
    """
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        return None
    return auth_header.replace("Bearer ", "")

def decode_clerk_jwt(token: str) -> Dict:
    """
    Decode and verify JWT token issued by Clerk.
    
    Args:
        token (str): JWT token.
        
    Returns:
        Dict: Decoded JWT payload.
        
    Raises:
        HTTPException: If token is invalid.
    """
    try:
        # In production, you would use the public key from Clerk to verify
        # For now, we'll use the SECRET_KEY for simplicity
        payload = jwt.decode(
            token,
            settings.CLERK_JWT_PUBLIC_KEY or settings.SECRET_KEY,
            algorithms=["RS256", "HS256"],
            audience="example.com",
            options={"verify_signature": settings.API_ENV == "production"}
        )
        return payload
    except jwt.PyJWTError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid authentication token: {str(e)}",
            headers={"WWW-Authenticate": "Bearer"},
        )

def get_current_user(request: Request) -> Dict:
    """
    Get the current authenticated user from JWT token.
    
    Args:
        request (Request): FastAPI request object.
        
    Returns:
        Dict: User information.
        
    Raises:
        HTTPException: If token is missing or invalid.
    """
    token = get_clerk_jwt_from_headers(request)
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authentication token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    payload = decode_clerk_jwt(token)
    
    # Extract user information from the JWT payload
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token: Missing user ID",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return {
        "id": user_id,
        "email": payload.get("email"),
        "name": payload.get("name"),
        # Add other user fields as needed
    }

# Dependency for authenticated routes
CurrentUser = Depends(get_current_user)
