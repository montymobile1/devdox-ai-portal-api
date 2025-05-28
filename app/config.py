"""
Configuration settings for the DevDox AI Portal API.
"""

import os
from pydantic_settings import BaseSettings
from enum import Enum
from typing import List, Optional


class GitHosting(str, Enum):
    GITLAB = "gitlab"
    GITHUB = "github"


class Settings(BaseSettings):
    """Application settings."""

    # API configuration
    API_ENV: str = "development"
    API_DEBUG: bool = True
    SECRET_KEY: str = (
        "f2hCPmuCDiBpAmuZD00ZX4fEXFb-H0WoReklDhJD3bA="  # Only for local/testing
    )

    # supbase settings
    SUPABASE_URL: str = "https://localhost"
    SUPABASE_SECRET_KEY: str = "test-supabase-key"
    SUPABASE_HOST: str = "supabase_user"
    SUPABASE_USER: str = "admin"
    SUPABASE_PASSWORD: str = "test"
    SUPABASE_PORT: int = 5432
    SUPABASE_DB_NAME: str = "postgres"

    CLERK_API_KEY: str = "test-clerk-key"

    CLERK_JWT_PUBLIC_KEY: Optional[str] = None

    # CORS settings
    CORS_ORIGINS: List[str] = ["http://localhost:3000"]

    # Server settings
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    # SonarQube configuration
    SONARQUBE_URL: Optional[str] = None
    SONARQUBE_TOKEN: Optional[str] = None

    LAUNCHDARKLY_SDK_KEY: Optional[str] = None

    # Version
    VERSION: str = "0.1.0"

    class Config:
        """Pydantic config class."""

        env_file = ".env"
        case_sensitive = True
        git_hosting: Optional[GitHosting] = None



# Initialize settings instance
settings = Settings()

# Tortoise ORM configuration
TORTOISE_ORM = {
    "connections": {
        "default": {
            "engine": "tortoise.backends.asyncpg",
            "credentials": {
                "host": settings.SUPABASE_HOST,
                "port": settings.SUPABASE_PORT,
                "user": settings.SUPABASE_USER,
                "password": settings.SUPABASE_PASSWORD,
                "database": settings.SUPABASE_DB_NAME,
                "minsize": 1,  # Minimum number of connections in the pool
                "maxsize": 10,  # Maximum number of connections in the pool
            }
        }
    },
    "apps": {
        "models": {
            "models": ["app.models.git_label", "aerich.models"],
            "default_connection": "default",
        }
    },
    "use_tz": True,
    "timezone": "UTC"
}

# Alternative connection URL format (you can use either approach)
def get_database_url():
    """Get the database URL for Tortoise ORM."""
    return f"postgresql://{settings.SUPABASE_USER}:{settings.SUPABASE_PASSWORD}@{settings.SUPABASE_HOST}:{settings.SUPABASE_PORT}/{settings.SUPABASE_DB_NAME}"
