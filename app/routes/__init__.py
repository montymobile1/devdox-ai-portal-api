"""
Routes module initialization.
"""

from fastapi import APIRouter

from app.routes.tokens_routes import router as tokens_routes

# Create main router
router = APIRouter()

# Include sub-routers
router.include_router(tokens_routes, prefix="/tokens", tags=[""])
