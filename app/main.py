"""
FastAPI application entry point for DevDox AI Portal API.
"""

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.logging_config import setup_logging
from contextlib import asynccontextmanager
from app.services import connect_db, disconnect_db
from app.config import settings, TORTOISE_ORM
from app.routes import router as api_router
from version import __version__

logger = setup_logging()

# Initialize FastAPI app
app = FastAPI(
    title="DevDox AI Portal API",
    description="Backend API service for the DevDox AI Portal.",
    version=__version__,
    docs_url="/docs",
    redoc_url="/redoc",
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager for startup and shutdown events."""
    # Startup
    from tortoise import Tortoise

    await Tortoise.init(config=TORTOISE_ORM)

    # Generate schemas only in development
    if settings.API_ENV == "dev":
        await Tortoise.generate_schemas()

    yield

    # Shutdown
    await Tortoise.close_connections()


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

# Register lifecycle events
app.add_event_handler("startup", connect_db)
app.add_event_handler("shutdown", disconnect_db)


@app.get("/", tags=["Health"])
@app.get("/health_check", tags=["Health"])
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "message": "DevDox AI Portal API is running!",
        "version": __version__,
    }


if __name__ == "__main__":
    """Run the application with uvicorn."""
    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.API_ENV == "development",
    )
