"""
Repository routes for the DevDox AI Portal API

This module provides endpoints for retrieving and adding Repos with their information.
"""

from fastapi import APIRouter, status, HTTPException, Depends, Path
from typing import Callable, Tuple, List, Dict, Any, Optional
from app.schemas.basic import PaginationParams
from app.utils.encryption import EncryptionHelper
from app.utils.api_response import APIResponse
from app.utils.gitlab_manager import GitLabManager
from app.utils.github_manager import GitHubManager
from app.utils import constants
from app.config import GitHosting
from app.services import db_client

# Create router
router = APIRouter()


def build_repo_dict(repo_info: Dict[str, Any], platform: str) -> Dict[str, Any]:
    """Builds a unified repository dictionary for GitHub or GitLab."""
    common_fields = {
        "id": repo_info.get("id"),
        "name": repo_info.get("name"),
        "description": repo_info.get("description"),
        "default_branch": repo_info.get("default_branch"),
        "forks_count": repo_info.get("forks_count"),
        "stargazers_count": repo_info.get("stargazers_count"),
    }

    if platform == GitHosting.GITLAB:
        common_fields.update(
            {
                "visibility": repo_info.get("visibility"),
                "html_url": repo_info.get("http_url_to_repo"),
            }
        )
    elif platform == GitHosting.GITHUB:
        common_fields.update(
            {
                "private": repo_info.get("private"),
                "html_url": repo_info.get("html_url"),
            }
        )
    return common_fields


def fetch_gitlab_repos(
    access_token: str, pagination: PaginationParams
) -> Tuple[List[Dict[str, Any]], int]:
    gitlab = GitLabManager(base_url="https://gitlab.com", access_token=access_token)
    raw_repos = gitlab.get_repos(page=pagination.offset + 1, per_page=pagination.limit)

    return [
        build_repo_dict(repo, GitHosting.GITLAB)
        for repo in raw_repos.get("repositories", [])
    ], raw_repos.get("pagination_info", {}).get("total_pages", 0)


def fetch_github_repos(
    access_token: str, pagination: PaginationParams
) -> Tuple[List[Dict[str, Any]], int]:
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

    return provider_map.get(hosting)  # returns None if unsupported


@router.get(
    "/{user_id}",
    response_model=List[Dict[str, Any]],
    status_code=status.HTTP_200_OK,
    summary="Get all repos",
    description="Retrieve a paginated list of repositories for a user",
)
async def get_repos(
    user_id: str = Path(
        ..., description="The ID of the user to retrieve repositories for"
    ),
    pagination: PaginationParams = Depends(),
) -> List[Dict[str, Any]]:
    """
    Retrieves all repos based on user_id for API response.

    Returns:
        A list of dictionaries containing repo info.
    """
    try:

        query = f"SELECT * FROM repo WHERE user_id =  '{str(user_id)}' ORDER BY created_at DESC LIMIT {pagination.limit} OFFSET {pagination.offset}"

        repos = await db_client.execute_query(query)

        return repos

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=constants.SERVICE_UNAVAILABLE,
        ) from e


@router.get(
    "/git_repos/{user_id}/{token_id}",
    response_model=List[Dict[str, Any]],
    status_code=status.HTTP_200_OK,
    summary="Get all repos from provider",
    description="Retrieve a paginated list of repositories based on provider sent for a user",
)
async def get_repos_from_git(
    token_id: str = Path(...),
    user_id: str = Path(...),
    pagination: PaginationParams = Depends(),
) -> dict[str, Any]:
    """
    Retrieves paginated repositories from any Git provider using a strategy map.
    """
    try:
        query = f"SELECT * FROM git_label WHERE id = '{str(token_id)}' AND user_id = '{str(user_id)}'"
        token = await db_client.execute_query_one(query)
        if not token:
            raise HTTPException(status_code=404, detail="Token not found")

        decrypted_token = EncryptionHelper().decrypt(token["token_value"])
        try:
            hosting = token["git_hosting"]
            repos_fetcher = get_git_repo_fetcher(hosting)

            if repos_fetcher:
                repos, total_count = repos_fetcher(decrypted_token, pagination)

                return APIResponse.success(
                    message="",
                    data=[{"total_count": total_count, "repos": repos}],
                )
            else:
                return APIResponse.error(
                    message=f"Unsupported Git hosting provider: {hosting}",
                    status_code=status.HTTP_400_BAD_REQUEST,
                )
        except Exception as e:
            print("Exception in get_repos_from_git:", e)
            return APIResponse.error(
                message=constants.SERVICE_UNAVAILABLE,
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

    except Exception as e:
        return APIResponse.error(
            message=constants.SERVICE_UNAVAILABLE,
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        )
