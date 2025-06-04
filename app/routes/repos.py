"""
Repository routes for the DevDox AI Portal API

This module provides endpoints for retrieving and adding Repos with their information.
"""

from typing import Any, Callable, Dict, List, Optional, Tuple

from fastapi import APIRouter, Depends, HTTPException, Path, status

from app.config import GitHosting
from app.exceptions.exception_constants import SERVICE_UNAVAILABLE
from app.models.git_label import GitLabel
from app.models.repo import Repo
from app.schemas.basic import PaginationParams
from app.schemas.repo import RepoListResponse, RepoResponse
from app.utils import constants
from app.utils.api_response import APIResponse
from app.utils.encryption import EncryptionHelper
from app.utils.github_manager import GitHubManager
from app.utils.gitlab_manager import GitLabManager

# Create router
router = APIRouter()


def build_repo_dict(repo_info: Dict[str, Any], platform: str) -> Dict[str, Any]:
    """Builds a unified repository dictionary for GitHub or GitLab."""
    common_fields = {
        "id": str(repo_info.get("id")),
        "repo_name": repo_info.get("name"),
        "description": repo_info.get("description"),
        "default_branch": repo_info.get("default_branch", "main"),
        "forks_count": repo_info.get("forks_count", 0),
        "stargazers_count": repo_info.get("stargazers_count")
        or repo_info.get("star_count", 0),
    }

    if platform == GitHosting.GITLAB:
        common_fields.update(
            {
                "visibility": repo_info.get("visibility"),
                "html_url": repo_info.get("http_url_to_repo"),
                "private": None,  # GitLab uses visibility instead
            }
        )
    elif platform == GitHosting.GITHUB:
        common_fields.update(
            {
                "private": repo_info.get("private"),
                "html_url": repo_info.get("html_url"),
                "visibility": None,  # GitHub uses private flag instead
            }
        )

    return common_fields


def fetch_gitlab_repos(
    access_token: str, pagination: PaginationParams
) -> Tuple[List[Dict[str, Any]], int]:
    """Fetch repositories from GitLab."""
    gitlab = GitLabManager(base_url="https://gitlab.com", access_token=access_token)
    raw_repos = gitlab.get_repos(page=pagination.offset + 1, per_page=pagination.limit)

    return [
        build_repo_dict(repo, GitHosting.GITLAB)
        for repo in raw_repos.get("repositories", [])
    ], raw_repos.get("pagination_info", {}).get(
        "total_count", len(raw_repos.get("repositories", []))
    )


def fetch_github_repos(
    access_token: str, pagination: PaginationParams
) -> Tuple[List[Dict[str, Any]], int]:
    """Fetch repositories from GitHub."""
    github = GitHubManager(access_token=access_token)
    result = github.get_user_repositories(
        page=pagination.offset + 1, per_page=pagination.limit
    )

    repos = [
        build_repo_dict(repo, GitHosting.GITHUB)
        for repo in result.get("repositories", [])
    ]
    total_count = result.get("pagination_info", {}).get("total_count", 0)

    return repos, total_count


def get_git_repo_fetcher(
    hosting: str,
) -> Optional[Callable[[str, PaginationParams], Tuple[List[Dict[str, Any]], int]]]:
    """Maps git_hosting to the appropriate repo fetcher function."""
    provider_map = {
        GitHosting.GITLAB: fetch_gitlab_repos,
        GitHosting.GITHUB: fetch_github_repos,
    }

    return provider_map.get(hosting)


@router.get(
    "/{user_id}",
    response_model=RepoListResponse,
    status_code=status.HTTP_200_OK,
    summary="Get all repos",
    description="Retrieve a paginated list of repositories for a user",
)
async def get_repos(
    user_id: str = Path(
        ..., description="The ID of the user to retrieve repositories for"
    ),
    pagination: PaginationParams = Depends(),
) -> RepoListResponse:
    """
    Retrieves all repos based on user_id for API response.

    Returns:
        A paginated list of repositories with total count.
    """
    try:
        query = Repo.filter(user_id=user_id)

        total_count = await query.count()
        repos = (
            await query.order_by("-created_at")
            .offset(pagination.offset)
            .limit(pagination.limit)
            .all()
        )

        # Convert to response format
        repo_responses = [RepoResponse.model_validate(repo) for repo in repos]

        return RepoListResponse(total_count=total_count, repos=repo_responses)

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=SERVICE_UNAVAILABLE,
        ) from e


@router.get(
    "/git_repos/{user_id}/{token_id}",
    response_model=Dict[str, Any],
    status_code=status.HTTP_200_OK,
    summary="Get all repos from provider",
    description="Retrieve a paginated list of repositories based on provider sent for a user",
)
async def get_repos_from_git(
    token_id: str = Path(..., description="Git token ID"),
    user_id: str = Path(..., description="User ID"),
    pagination: PaginationParams = Depends(),
) -> Dict[str, Any]:
    """
    Retrieves paginated repositories from any Git provider using a strategy map.
    """
    try:
        # Get token using Tortoise ORM
        token = await GitLabel.filter(id=token_id, user_id=user_id).first()
        if token:
            # Decrypt token
            decrypted_token = EncryptionHelper().decrypt(token.token_value)
            try:
                hosting = token.git_hosting
                repos_fetcher = get_git_repo_fetcher(hosting)

                if repos_fetcher:
                    repos, total_count = repos_fetcher(decrypted_token, pagination)
                    return APIResponse.success(
                        message="Repositories retrieved successfully",
                        data={"total_count": total_count, "repos": repos},
                    )
                else:
                    return APIResponse.error(
                        message=f"Unsupported Git hosting provider: {hosting}",
                        status_code=status.HTTP_400_BAD_REQUEST,
                    )
            except Exception:
                return APIResponse.error(
                    message=f"Failed to fetch repositories: {str(e)}",
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                )
        return APIResponse.error(
            message=constants.TOKEN_NOT_FOUND, status_code=status.HTTP_404_NOT_FOUND
        )

    except Exception:
        return APIResponse.error(
            message=SERVICE_UNAVAILABLE,
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        )
