"""
Routes module initialization.
"""

from fastapi import APIRouter

from app.routes.git_tokens import router as git_tokens

# Create main router
router = APIRouter()

# Include sub-routers
router.include_router(git_tokens, prefix="/git_tokens", tags=["GitTokens"])
