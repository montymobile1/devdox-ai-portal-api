"""
Configuration settings for the DevDox AI Portal API.
"""

import os
from pydantic_settings import BaseSettings
from enum import Enum
from typing import List, Optional, Dict, Any


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

    # SUPABASE settings
    SUPABASE_URL: str = "https://localhost"
    SUPABASE_SECRET_KEY: str = "test-supabase-key"

    SUPABASE_REST_API: bool = True

    SUPABASE_HOST: str = "https://locahost"
    SUPABASE_USER: str = "admin"
    SUPABASE_PASSWORD: str = "test"
    SUPABASE_PORT: int = 5432
    SUPABASE_DB_NAME: str = "postgres"

    DB_MIN_CONNECTIONS: int = 1
    DB_MAX_CONNECTIONS: int = 10

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


def get_database_config() -> Dict[str, Any]:
    """
    Returns the appropriate database configuration based on available credentials.
    Prioritizes direct PostgreSQL connection over API-based connection.
    """
    # Check if developer wants to use RESTAPI
    if settings.SUPABASE_REST_API:

        # Extract database connection info from Supabase URL
        # Supabase URL format: https://your-project.supabase.co
        project_id = settings.SUPABASE_URL.replace("https://", "").replace(
            ".supabase.co", ""
        )

        # Use service role key if available
        password = settings.SUPABASE_SECRET_KEY
        return {
            "engine": "tortoise.backends.asyncpg",
            "credentials": {
                "host": f"db.{project_id}.supabase.co",
                "port": 5432,
                "user": "postgres",
                "password": password,
                "database": "postgres",
                "minsize": settings.DB_MIN_CONNECTIONS,
                "maxsize": settings.DB_MAX_CONNECTIONS,
                "ssl": "require",
            },
        }

    # Method 2: Supabase postgress sql
    else:
        return {
            "engine": "tortoise.backends.asyncpg",
            "credentials": {
                "host": settings.SUPABASE_HOST,
                "port": settings.SUPABASE_PORT,
                "user": settings.SUPABASE_USER,
                "password": settings.SUPABASE_PASSWORD,
                "database": settings.SUPABASE_DB_NAME,
                "minsize": settings.DB_MIN_CONNECTIONS,
                "maxsize": settings.DB_MAX_CONNECTIONS,
                "ssl": "require",  # Supabase requires SSL
            },
        }


TORTOISE_ORM = get_database_config()
