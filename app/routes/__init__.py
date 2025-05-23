"""
Routes module initialization.
"""

from fastapi import APIRouter

from app.routes.git_tokens import router as git_tokens
from app.routes.repos import router as repos

# Create main router
router = APIRouter()

# Include sub-routers
router.include_router(git_tokens, prefix="/git_tokens", tags=["GitTokens"])
router.include_router(repos, prefix="/repos", tags=["Repos"])
