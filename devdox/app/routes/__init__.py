"""
Routes module initialization.
"""

from fastapi import APIRouter

from app.routes.git_tokens import router as git_tokens
from app.routes.repos import router as repos
from app.routes.webhooks import router as webhook_router
from app.routes.api_keys import router as api_keys_router

# Create main router
router = APIRouter()

# Include sub-routers
router.include_router(git_tokens, prefix="/git_tokens", tags=["GitTokens"])
router.include_router(repos, prefix="/repos", tags=["Repos"])
router.include_router(webhook_router, prefix="/webhooks", tags=["Webhooks"])

router.include_router(api_keys_router, prefix="/api-keys", tags=["API-Key"])
