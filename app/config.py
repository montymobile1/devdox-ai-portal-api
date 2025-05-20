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
    SECRET_KEY: str = "dev-secret-key"  # Only for local/testing

    #supbase settings
    SUPABASE_URL: str = "https://localhost"
    SUPABASE_KEY: str = "test-supabase-key"
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
    
    class Config:
        """Pydantic config class."""
        env_file = ".env"
        case_sensitive = True
        git_hosting: Optional[GitHosting] = None

# Initialize settings instance
settings = Settings()
