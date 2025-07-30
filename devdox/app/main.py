"""
FastAPI application entry point for DevDox AI Portal API.
"""

from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings, TORTOISE_ORM
from app.exceptions.exception_manager import register_exception_handlers
from app.logging_config import setup_logging
from app.routes import router as api_router

logger = setup_logging()

# Initialize FastAPI app


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager for startup and shutdown events."""
    # Startup
    from tortoise import Tortoise

    await Tortoise.init(config=TORTOISE_ORM)
    yield

    # Shutdown
    await Tortoise.close_connections()


app = FastAPI(
    title="DevDox AI Portal API",
    description="Backend API service for the DevDox AI Portal.",
    version=settings.VERSION,
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)
# Configure CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Include API routes
app.include_router(api_router, prefix="/api/v1")

# Register all exception handlers from one place
register_exception_handlers(app)


@app.get("/", tags=["Health"])
@app.get("/health_check", tags=["Health"])
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "message": "DevDox AI Portal API is running!",
        "version": settings.VERSION,
    }


if __name__ == "__main__":
    """Run the application with uvicorn."""
    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.API_ENV == "development",
    )
