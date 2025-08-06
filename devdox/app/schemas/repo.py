import uuid
from types import SimpleNamespace

from app.config import GitHosting
from github.AuthenticatedUser import AuthenticatedUser
from github.Repository import Repository
from gitlab.v4.objects import Project
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


class GitUserResponse(BaseModel):
    username: Optional[str] = Field(None, description="Git Username")
    id: Optional[int] = Field(None, description="Git user Id")
    name: Optional[str] = Field(None, description="Git user display name")
    email: Optional[str] = Field(None, description="Git user email")
    avatar_url: Optional[str] = Field(None, description="Git user avatar url")
    html_url: Optional[str] = Field(None, description="Git user html url")


class GitLabRepoResponseTransformer:

    @classmethod
    def derive_storage_size(cls, statistics: dict):
        if not statistics:
            return None

        return statistics.get("repository_size", 0)

    @classmethod
    def derived_private_field(cls, visibility: str):
        if not visibility:
            return None

        if visibility.lower() in ("private", "internal"):
            derived_private = True
        else:
            derived_private = False

        return derived_private

    @classmethod
    def transform_project_to_dict(cls, project: Project | SimpleNamespace) -> dict:
        extracted_visibility = getattr(project, "visibility", None)
        extracted_statistics = getattr(project, "statistics", None)

        return {
            "id": str(project.id),
            "name": project.name,
            "description": project.description,
            "default_branch": project.default_branch,
            "forks_count": project.forks_count,
            "visibility": extracted_visibility,
            "created_at": project.created_at,
            "star_count": project.star_count,
            "http_url_to_repo": project.http_url_to_repo,
            "path_with_namespace": project.path_with_namespace,
            "statistics": extracted_statistics,
        }

    @classmethod
    def from_git(cls, data: Project | SimpleNamespace | dict) -> GitRepoResponse | None:
        if not data:
            return None
        elif isinstance(data, Project) or isinstance(data, SimpleNamespace):
            dict_data = cls.transform_project_to_dict(data)
        elif isinstance(data, dict):
            dict_data = data
        else:
            raise TypeError(
                f"Unsupported type for `data`: {type(data)}. Expected Project, SimpleNamespace, or dict."
            )

        return GitRepoResponse(
            id=str(dict_data.get("id", "")),
            repo_name=dict_data.get("name"),
            description=dict_data.get("description"),
            default_branch=dict_data.get("default_branch", "main"),
            forks_count=dict_data.get("forks_count", 0),
            stargazers_count=dict_data.get("star_count", 0),
            html_url=dict_data.get("http_url_to_repo"),
            relative_path=dict_data.get("path_with_namespace"),
            visibility=dict_data.get("visibility"),
            repo_created_at=dict_data.get("created_at"),
            size=cls.derive_storage_size(dict_data.get("statistics")) or 0,
            private=cls.derived_private_field(dict_data.get("visibility")),
        )

    @classmethod
    def from_git_user(cls, data: dict) -> GitUserResponse | None:
        if not data:
            return None
        elif isinstance(data, dict):
            dict_data = data
        else:
            raise TypeError(
                f"Unsupported type for `data`: {type(data)}. Expected dict."
            )

        return GitUserResponse(
            username=dict_data.get("username"),
            id=dict_data.get("id"),
            name=dict_data.get("name"),
            email=dict_data.get("email"),
            avatar_url=dict_data.get("avatar_url"),
            html_url=dict_data.get("html_url"),
        )


class GitHubRepoResponseTransformer:

    @classmethod
    def resolve_git_size_from_kb_to_byte(cls, size: int):
        if not size:
            return 0

        return size * 1024

    @classmethod
    def transform_repository_to_dict(
        cls, repository: Repository | SimpleNamespace
    ) -> dict:
        return {
            "id": str(repository.id),
            "name": repository.name,
            "description": repository.description,
            "default_branch": repository.default_branch or "main",
            "forks_count": repository.forks_count or 0,
            "size": repository.size or 0,
            "stargazers_count": repository.stargazers_count or 0,
            "full_name": repository.full_name,
            "html_url": repository.html_url,
            "private": repository.private,
            "visibility": getattr(repository, "visibility", None),
            "repo_created_at": repository.created_at,
        }

    @classmethod
    def transform_authenticated_user_to_dict(
        cls, authenticated_user: AuthenticatedUser | SimpleNamespace
    ) -> dict:
        return {
            "login": authenticated_user.login,
            "id": authenticated_user.id,
            "name": authenticated_user.name,
            "email": authenticated_user.email,
            "avatar_url": authenticated_user.avatar_url,
            "html_url": authenticated_user.html_url,
        }

    @classmethod
    def from_git(
        cls, data: Repository | SimpleNamespace | dict
    ) -> GitRepoResponse | None:

        if not data:
            return None
        elif isinstance(data, Repository) or isinstance(data, SimpleNamespace):
            dict_data = cls.transform_repository_to_dict(data)
        elif isinstance(data, dict):
            dict_data = data
        else:
            raise TypeError(
                f"Unsupported type for `data`: {type(data)}. Expected Repository, SimpleNamespace, or dict."
            )

        return GitRepoResponse(
            id=str(dict_data.get("id", "")),
            repo_name=dict_data.get("name"),
            description=dict_data.get("description"),
            default_branch=dict_data.get("default_branch", "main"),
            forks_count=dict_data.get("forks_count", 0),
            stargazers_count=dict_data.get("stargazers_count", 0),
            relative_path=dict_data.get("full_name"),
            html_url=dict_data.get("html_url"),
            private=dict_data.get("private"),
            visibility=dict_data.get("visibility"),
            size=cls.resolve_git_size_from_kb_to_byte(dict_data.get("size", 0)),
            repo_created_at=dict_data.get("repo_created_at"),
        )

    @classmethod
    def from_git_user(
        cls, data: AuthenticatedUser | SimpleNamespace | dict
    ) -> GitUserResponse | None:
        if not data:
            return None
        elif isinstance(data, AuthenticatedUser) or isinstance(data, SimpleNamespace):
            dict_data = cls.transform_authenticated_user_to_dict(data)
        elif isinstance(data, dict):
            dict_data = data
        else:
            raise TypeError(
                f"Unsupported type for `data`: {type(data)}. Expected AuthenticatedUser or SimpleNamespace or dict."
            )

        return GitUserResponse(
            username=dict_data.get("login"),
            id=dict_data.get("id"),
            name=dict_data.get("name"),
            email=dict_data.get("email"),
            avatar_url=dict_data.get("avatar_url"),
            html_url=dict_data.get("html_url"),
        )


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
