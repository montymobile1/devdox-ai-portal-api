import uuid
from types import SimpleNamespace

from github.AuthenticatedUser import AuthenticatedUser
from github.Repository import Repository
from gitlab.v4.objects import Project
from models_src.dto.repo import GitHosting
from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List
from datetime import datetime
from enum import Enum



REPO_ALIAS_NAME_FIELD_TITLE="Repository Alias Name"
REPO_ALIAS_NAME_FIELD_DESCRIPTION="A user-defined alias for this repository, used locally within this system as an alternative to the official GitHub or GitLab repository name."

REPO_USER_REFERENCE_FIELD_TITLE = "Repository User Reference Note"
REPO_USER_REFERENCE_FIELD_DESCRIPTION = "An optional free-form description or note for this repository. Use this to explain its purpose, provide internal context, or document team-specific information."

REPO_SYSTEM_REFERENCE_FIELD_TITLE= "Repository System generated Reference Note"
REPO_SYSTEM_REFERENCE_FIELD_DESCRIPTION= "An optional description or note for this repository. System generates this to explain its purpose, provide internal context, or document specific information."


class RepoBase(BaseModel):
    """Base repository schema with common fields"""

    repo_name: str = Field(..., description="Repository name", max_length=255)
    description: Optional[str] = Field(None, description="Repository description")
    html_url: str = Field(..., description="Repository URL", max_length=500)
    default_branch: str = Field(
        default="main", description="Default branch name", max_length=100
    )
    forks_count: int = Field(default=0, description="Number of forks", ge=0)
    stargazers_count: int = Field(default=0, description="Number of stars", ge=0)
    is_private: bool = Field(default=False, description="Whether repository is private")
    visibility: Optional[str] = Field(
        None, description="Repository visibility (GitLab)", max_length=50
    )
    git_hosting: Optional[GitHosting] = Field(
        None, description="Git hosting provider"
    )
    language: Optional[List[str]] = Field(
        None, description="Primary programming languages"
    )
    size: Optional[int] = Field(None, description="Repository size in KB", ge=0)
    repo_created_at: Optional[datetime] = Field(
        None, description="Repository creation date from provider"
    )
    repo_updated_at: Optional[datetime] = Field(
        None, description="Repository last update from provider"
    )

    relative_path: Optional[str] = Field(
        default=None,
        description="The path to the repository relative to its hosting platform domain",
        max_length=255,
    )

    repo_alias_name: Optional[str] = Field(
        None,
        title=REPO_ALIAS_NAME_FIELD_TITLE,
        description=REPO_ALIAS_NAME_FIELD_DESCRIPTION,
        min_length=1,
        max_length=100,
    )

    repo_user_reference: Optional[str] = Field(
        None,
        title=REPO_USER_REFERENCE_FIELD_TITLE,
        description=REPO_USER_REFERENCE_FIELD_DESCRIPTION,
        max_length=2000,
    )

    repo_system_reference: Optional[str] = Field(
        None,
        title=REPO_SYSTEM_REFERENCE_FIELD_TITLE,
        description=REPO_SYSTEM_REFERENCE_FIELD_DESCRIPTION
    )


class RepoResponse(RepoBase):
    """Schema for repository response"""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID = Field(..., description="Primary key")
    user_id: str = Field(..., description="User ID who owns this repository")
    repo_id: str = Field(..., description="Repository ID from the Git provider")
    token_id: Optional[str] = Field(None, description="Associated token ID")
    status: Optional[str] = Field(None, description="Repository status")
    created_at: datetime = Field(..., description="Record creation timestamp")
    repo_user_reference: Optional[str] = Field(
        None,
        exclude=True,
        description="User-provided reference (excluded from API response)"
    )
    repo_system_reference: Optional[str] = Field(   None,
        exclude=True,
        description="Repo_system_reference(excluded from API response)")
    updated_at: datetime = Field(..., description="Record update timestamp")


class RepoListResponse(BaseModel):
    """Schema for paginated repository list response"""

    total_count: int = Field(..., description="Total number of repositories", ge=0)
    repos: List[RepoResponse] = Field(..., description="List of repositories")


class GitRepoResponse(BaseModel):
    """Schema for Git provider repository response (unified format)"""

    id: str = Field(..., description="Repository ID from provider")
    repo_name: str = Field(..., description="Repository name")
    description: Optional[str] = Field(None, description="Repository description")
    html_url: str = Field(..., description="Repository URL")
    relative_path: str = Field(
        ..., description="The part of the repository's url excluding the domain"
    )

    default_branch: str = Field(..., description="Default branch name")
    forks_count: int = Field(..., description="Number of forks")
    stargazers_count: int = Field(..., description="Number of stars")
    size: Optional[int] = Field(None, description="Repository size in KB")
    repo_created_at: Optional[datetime] = Field(
        None, description="Repository creation date from provider"
    )

    # Platform-specific fields (one will be None depending on provider)
    private: Optional[bool] = Field(None, description="Private flag (GitHub)")
    visibility: Optional[str] = Field(None, description="Visibility setting (GitLab)")


class AnalyzeRepositoryRequest(BaseModel):
    id: str = Field(
        ...,
        title="Repository ID",
        description=("ID of repository in our database"),
    )


class AddRepositoryRequest(BaseModel):
    relative_path: str = Field(
        ...,
        title="Repository Relative Path",
        description=(
            "The path to the repository **relative to its hosting platform domain**.\n\n"
            "Use this field to specify the location of the repository **without** including the domain.\n"
            "Examples:\n"
            "- For GitHub: `owner/repo`\n"
            "- For GitLab: `group/subgroup/project`\n\n"
            "This value should match the exact path you see after the domain in the web URL."
        ),
    )

    repo_alias_name: str = Field(
        ...,
        title=REPO_ALIAS_NAME_FIELD_TITLE,
        description=REPO_ALIAS_NAME_FIELD_DESCRIPTION,
        min_length=1,
        max_length=100,
    )
    
    repo_user_reference: Optional[str] = Field(
        default=None,
        title=REPO_USER_REFERENCE_FIELD_TITLE,
        description=REPO_USER_REFERENCE_FIELD_DESCRIPTION,
        max_length=2000,
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {"relative_path": "openai/gpt-4", "repo_alias_name": "My Custom Github Repo", "repo_user_reference": "My custom description"},  # GitHub-style
                {"relative_path": "mygroup/dev/backend-api", "repo_alias_name": "My Custom Gitlab Repo", "repo_user_reference": "My custom description"},  # GitLab-style
            ]
        }
    }
