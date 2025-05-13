"""
Configuration settings for the DevDox AI Portal API.
"""

import os
from pydantic_settings import BaseSettings
from typing import List, Optional

class Settings(BaseSettings):
    """Application settings."""
    
    # API configuration
    API_ENV: str = "development"
    API_DEBUG: bool = True
    SECRET_KEY: str
    
    # Supabase configuration
    SUPABASE_URL: str
    SUPABASE_KEY: str
    
    # Clerk configuration
    CLERK_API_KEY: str
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

# Initialize settings instance
settings = Settings()
