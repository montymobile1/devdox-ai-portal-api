from pydantic import BaseModel, Field, ConfigDict
from typing import Optional
from datetime import datetime
import uuid


class GitLabelBase(BaseModel):
    """Base schema for GitLabel"""

    label: str = Field(
        ..., description="Label/name for this git configuration", max_length=100
    )
    # username: str = Field(
    #     ..., description="Username for the git hosting service", max_length=100
    # )
    git_hosting: str = Field(
        ..., description="Git hosting service (e.g., 'github', 'gitlab')"
    )
    token_value: str = Field(
        ..., description="Access token for the git hosting service"
    )


class GitLabelCreate(GitLabelBase):
    user_id: str = Field(
        None, description="User identifier (will be overridden by auth)"
    )


class GitLabelUpdate(BaseModel):
    label: Optional[str] = Field(
        None, description="Label/name for this git configuration"
    )
    git_hosting: Optional[str] = Field(
        None, description="Git hosting service (e.g., 'github', 'gitlab')"
    )
    username: Optional[str] = Field(
        None, description="Username for the git hosting service"
    )
    token_value: Optional[str] = Field(
        None, description="Access token for the git hosting service"
    )


class GitLabelResponse(GitLabelBase):
    id: uuid.UUID = Field(..., description="Unique identifier")
    user_id: str = Field(..., description="User identifier")
    created_at: datetime = Field(..., description="Record creation timestamp")
    updated_at: datetime = Field(..., description="Record last update timestamp")
    model_config = ConfigDict(from_attributes=True)


class GitLabelListResponse(BaseModel):
    items: list[GitLabelResponse]
    total: int
    page: int
    size: int


class ErrorResponse(BaseModel):
    """Schema for error responses"""

    detail: str = Field(..., description="Error message")
    error_code: Optional[str] = Field(None, description="Error code")
