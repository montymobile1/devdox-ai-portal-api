import uuid

from github.Repository import Repository
from gitlab.v4.objects import Project
from pydantic import BaseModel, Field, ConfigDict
from typing import Any, Optional, List
from datetime import datetime
from enum import Enum


class GitHostingProvider(str, Enum):
    """Supported Git hosting providers"""

    GITHUB = "github"
    GITLAB = "gitlab"


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
    git_hosting: Optional[GitHostingProvider] = Field(None, description="Git hosting provider")
    language: Optional[str] = Field(
        None, description="Primary programming language", max_length=100
    )
    size: Optional[int] = Field(None, description="Repository size in KB", ge=0)
    repo_created_at: Optional[datetime] = Field(
        None, description="Repository creation date from provider"
    )
    repo_updated_at: Optional[datetime] = Field(
        None, description="Repository last update from provider"
    )


class RepoResponse(RepoBase):
    """Schema for repository response"""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID = Field(..., description="Primary key")
    user_id: str = Field(..., description="User ID who owns this repository")
    repo_id: str = Field(..., description="Repository ID from the Git provider")
    token_id: Optional[str] = Field(None, description="Associated token ID")
    created_at: datetime = Field(..., description="Record creation timestamp")
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


class GitRepoResponseTransformer:

    @staticmethod
    def from_gitlab(data: Project | dict) -> GitRepoResponse:

        if isinstance(data, Project):
            derived_private = None
            if hasattr(data, "visibility"):
                if data.visibility.lower() in ("private", "internal"):
                    derived_private = True
                else:
                    derived_private = False

            storage_size = 0
            if hasattr(data, "statistics") and data.statistics:
                storage_size = data.statistics.get("storage_size", 0)

        elif isinstance(data, dict):
            derived_private = None
            visibility = data.get("visibility")
            if visibility:
                if visibility.lower() in ("private", "internal"):
                    derived_private = True
                else:
                    derived_private = False
            storage_size = data.get("statistics", {}).get("storage_size", 0)
        else:
            raise Exception("Unsupported from_gitlab `data` type")

        return GitRepoResponseTransformer._build_common_fields(
            data,
            size=storage_size,
            stargazers_count=data.get("star_count", 0),
            html_url=data.get("http_url_to_repo"),
            private=derived_private,
        )

    @staticmethod
    def from_github(data: Repository | dict) -> GitRepoResponse:

        if isinstance(data, dict):
            return GitRepoResponseTransformer._build_common_fields(
                data,
                size=data.get("size"),
                stargazers_count=data.get("stargazers_count", 0),
                html_url=data.get("html_url"),
                private=data.get("private"),
            )
        elif isinstance(data, Repository):
            return GitRepoResponseTransformer._build_common_fields(
                data,
                size=data.size,
                stargazers_count=data.stargazers_count or 0,
                html_url=data.html_url,
                private=data.private,
            )
        else:
            raise Exception("Unsupported from_github `data` type")

    @staticmethod
    def _build_common_fields(
        data: Project | Repository | dict,
        stargazers_count: int,
        html_url: str,
        private: Any,
        size: Optional[int] = None,
    ) -> GitRepoResponse:

        if isinstance(data, Project) or isinstance(data, Repository):
            return GitRepoResponse(
                id=str(data.id),
                repo_name=data.name,
                description=data.description,
                default_branch=data.default_branch or "main",
                forks_count=data.forks_count or 0,
                stargazers_count=stargazers_count,
                html_url=html_url,
                private=private,
                visibility=data.visibility if hasattr(data, "visibility") else None,
                size=size or 0,
                repo_created_at=data.created_at,
            )

        elif isinstance(data, dict):
            return GitRepoResponse(
                id=str(data.get("id", "")),
                repo_name=data.get("name"),
                description=data.get("description"),
                default_branch=data.get("default_branch", "main"),
                forks_count=data.get("forks_count", 0),
                stargazers_count=stargazers_count,
                html_url=html_url,
                private=private,
                visibility=data.visibility if hasattr(data, "visibility") else None,
                size=size or 0,
                repo_created_at=data.get("created_at"),
            )

        else:
            raise Exception("Unsupported _build_common_fields `data` type")
