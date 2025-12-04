"""
FastAPI application entry point for DevDox AI Portal API.
"""
import inspect
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from models_src import init_via_uri, build_uri, MongoConfig

from app.config import settings, TORTOISE_ORM
from app.exceptions.exception_manager import register_exception_handlers
from app.logging_config import setup_logging
from app.routes import router as api_router

logger = setup_logging()

async def init_mongo(mongo_settings:MongoConfig | None):

    if mongo_settings:
        mongo_uri = build_uri(mongo_conf=mongo_settings)
        mongo_client, mongo_db = await init_via_uri(mongo_uri)
        
        # health check to fail fast
        try:
            await mongo_db.command("ping")
        except Exception:
            # clean up before re-raising so FastAPI doesn’t keep a half-open client
            mongo_res = mongo_client.close()
            if inspect.isawaitable(mongo_res):
                await mongo_res
            raise
        
        return mongo_client, mongo_db
    return None, None


async def shutdown_mongo(mongo_settings:MongoConfig | None, mongo_client):
    if mongo_settings and mongo_client:
        res = mongo_client.close()
        if inspect.isawaitable(res):
            await res
        
        logger.info("MongoDB connections closed")

# Initialize FastAPI app
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager for startup and shutdown events."""
    # Startup
    from tortoise import Tortoise

    await Tortoise.init(config=TORTOISE_ORM)
    
    # INITIALIZE MONGODB
    mongo_client, _ = await init_mongo(mongo_settings=settings.MONGO)
    
    yield
    
    # Shutdown
    await Tortoise.close_connections()
    
    await shutdown_mongo(mongo_settings=settings.MONGO, mongo_client=mongo_client)

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
