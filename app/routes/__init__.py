"""
Routes module initialization.
"""

from fastapi import APIRouter

from app.routes.example_routes import router as example_router
from app.routes.auth_routes import router as auth_router

# Create main router
router = APIRouter()

# Include sub-routers
router.include_router(example_router, prefix="/examples", tags=["Examples"])
router.include_router(auth_router, prefix="/auth", tags=["Authentication"])
