"""
Repository routes for the DevDox AI Portal API

This module provides endpoints for retrieving and adding Repos with their information.
"""

from typing import Any, Dict

from fastapi import APIRouter, Depends, Path, status
from starlette.responses import JSONResponse

from app.schemas.basic import RequiredPaginationParams
from app.schemas.repo import (
    AddRepositoryRequest,
    RepoListResponse,
    AnalyzeRepositoryRequest,
)
from app.services.repository import (
    RepoProviderService,
    RepoManipulationService,
    RepoQueryService,
)
from app.utils.api_response import APIResponse
from app.utils.auth import get_authenticated_user, UserClaims
from app.utils.constants import RESOURCE_RETRIEVED_SUCCESSFULLY

# Create router
router = APIRouter()


@router.get(
    "/",
    response_model=RepoListResponse,
    status_code=status.HTTP_200_OK,
    summary="Get all repos",
    description="Retrieve a paginated list of repositories for a user",
)
async def get_repos(
    user: UserClaims = Depends(get_authenticated_user),
    service: RepoQueryService = Depends(RepoQueryService),
    pagination: RequiredPaginationParams = Depends(),
) -> JSONResponse:

    total_count, repo_responses = await service.get_all_user_repositories(
        user, pagination
    )
    return APIResponse.success(
        message=RESOURCE_RETRIEVED_SUCCESSFULLY,
        data=RepoListResponse(total_count=total_count, repos=repo_responses).model_dump(
            mode="json"
        ),
    )


@router.get(
    "/git_repos/users/{token_id}",
    response_model=Dict[str, Any],
    status_code=status.HTTP_200_OK,
    summary="Get all repos from provider",
    description="Retrieve a paginated list of repositories based on provider sent for a user",
)
async def get_repos_from_git(
    token_id: str = Path(..., description="Git token ID"),
    pagination: RequiredPaginationParams = Depends(),
    user: UserClaims = Depends(get_authenticated_user),
    service: RepoProviderService = Depends(RepoProviderService),
):
    total, repos = await service.get_all_provider_repos(token_id, user, pagination)
    return APIResponse.success(
        "Repositories retrieved successfully", {"total_count": total, "repos": repos}
    )


@router.post(
    "/git_repos/users/{token_id}",
    status_code=status.HTTP_201_CREATED,
    summary="Add a repository from Git provider",
    description="Add a selected repository to the database using a Git token",
)
async def add_repo_from_git(
    token_id: str,
    payload: AddRepositoryRequest,
    user: UserClaims = Depends(get_authenticated_user),
    repo_service: RepoManipulationService = Depends(RepoManipulationService),
):
    await repo_service.add_repo_from_provider(user, token_id, payload.relative_path)
    return APIResponse.success("Repository added successfully")


@router.post(
    "/analyze",
    status_code=status.HTTP_201_CREATED,
    summary="Analyze a repository by ID",
    description="Analyze a repository by ID",
)
async def analyze_repo(
    payload: AnalyzeRepositoryRequest,
    user: UserClaims = Depends(get_authenticated_user),
    repo_service: RepoManipulationService = Depends(RepoManipulationService),
):
    await repo_service.analyze_repo(user, payload.id)
    return APIResponse.success("Start analyzing successfully")
