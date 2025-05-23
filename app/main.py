"""
FastAPI application entry point for DevDox AI Portal API.
"""

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.routes import router as api_router
from version import __version__

# Initialize FastAPI app
app = FastAPI(
    title="DevDox AI Portal API",
    description="Backend API service for the DevDox AI Portal.",
    version=__version__,
    docs_url="/docs",
    redoc_url="/redoc",
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

@app.get("/", tags=["Health"])
@app.get("/health_check", tags=["Health"])
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "message": "DevDox AI Portal API is running!", "version": __version__}

if __name__ == "__main__":
    """Run the application with uvicorn."""
    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.API_ENV == "development",
    )
