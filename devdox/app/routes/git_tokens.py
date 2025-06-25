"""
Git Label routes for the DevDox AI Portal API.

This module provides endpoints for managing Git tokens with CRUD operations.
It supports creating, reading, updating, and deleting git hosting service configurations.
"""

import logging
import uuid
from typing import Annotated, Any, Dict

from fastapi import APIRouter, Body, Depends, status
from starlette.responses import JSONResponse

import app.exceptions.exception_constants
from app.exceptions.exception_constants import SERVICE_UNAVAILABLE
from models.git_label import GitLabel
from app.schemas.git_label import (
    AddGitTokenRequest,
    GetGitLabelByLabelRequest,
    GetGitLabelsRequest,
    GitLabelBase,
)
from app.services.git_tokens_service import GetGitLabelService, PostGitLabelService
from app.utils import constants, CurrentUser
from app.utils.api_response import APIResponse
from app.utils.auth import AuthenticatedUserDTO, get_authenticated_user, UserClaims

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get(
    "/",
    response_model=Dict[str, Any],
    status_code=status.HTTP_200_OK,
    summary="Get all git labels",
    description="Retrieve a list of all git labels with masked token values",
)
async def get_git_labels(
    user_claims: Annotated[UserClaims, Depends(get_authenticated_user)],
    request: Annotated[GetGitLabelsRequest, Depends()],
	service: Annotated[GetGitLabelService, Depends(GetGitLabelService.with_dependency)],
) -> JSONResponse:
    """
    Retrieves all stored git labels with masked token values for API response.
    The Usage of Annotated[callable, Depends(callable)] is the recommended way to perform dependency injection.
    
    Args:
        request: contains all the `Json Body`, `Path Variable`, `Query Parameters` ... , required by the API
        service: represents the service layer that is responsible for performing all the calculations and return a raw result
        user_claims: represents the injected dependency for authentication of the user
    Returns:
            APIResponse with list of git labels containing metadata and masked token values.
    """
    results = await service.get_git_labels_by_user(
        pagination=request.pagination,
        user_claims=user_claims,
        git_hosting=request.git_hosting,
    )

    return APIResponse.success(
        message="Git labels retrieved successfully", data=results
    )


@router.get(
    "/{label}",
    response_model=Dict[str, Any],
    status_code=status.HTTP_200_OK,
    summary="Get git labels by label",
    description="Retrieve git labels matching the specified label with masked token values",
)
async def get_git_label_by_label(
    user_claims: Annotated[UserClaims, Depends(get_authenticated_user)],
    request: Annotated[GetGitLabelByLabelRequest, Depends()],
    service: Annotated[GetGitLabelService, Depends(GetGitLabelService.with_dependency)],
) -> JSONResponse:
    """
    Retrieves git labels matching the specified label with masked token values.
    The Usage of Annotated[callable, Depends(callable)] is the recommended way to perform dependency injection.
    
    Args:
        request: contains all the `Json Body`, `Path Variable`, `Query Parameters` ... , required by the API
        service: represents the service layer that is responsible for performing all the calculations and return a raw result
        user_claims: represents the injected dependency for authentication of the user
    
    Returns:
            APIResponse with list of matching git labels with masked token values.
    """

    results = await service.get_git_labels_by_label(
        pagination=request.pagination,
        user_claims=user_claims,
        label=request.label,
    )

    return APIResponse.success(
        message="Git labels retrieved successfully", data={"items": results}
    )


@router.post(
    "/",
    response_model=Dict[str, Any],
    status_code=status.HTTP_201_CREATED,
    summary="Add new git token",
    description="Create a new git hosting service token configuration",
)
async def add_git_token(
    service: Annotated[PostGitLabelService, Depends(PostGitLabelService.with_dependency)],
    request: Annotated[AddGitTokenRequest, Depends()],
    authenticated_user: AuthenticatedUserDTO = CurrentUser,
) -> JSONResponse:
    """
    Add a new git token configuration with validation based on hosting service.
    """
    results = await service.add_git_token(
        user_claims=authenticated_user,
        json_payload=request.payload
    )

    return APIResponse.success(
        message=constants.TOKEN_SAVED_SUCCESSFULLY, data={"id": str(results.id)}
    )


@router.delete(
    "/{git_label_id}",
    response_model=Dict[str, Any],
    status_code=status.HTTP_200_OK,
    summary="Delete git label by ID",
    description="Delete a git label configuration by ID",
)
async def delete_git_label(
    git_label_id: str,
    authenticated_user: AuthenticatedUserDTO = CurrentUser,
) -> JSONResponse:
    """
    Deletes a git label with the specified ID.

    Args:
            git_label_id: The unique identifier of the git label to delete.

    Returns:
            A success response if the git label was deleted, or an error response if not found.
    """
    try:
        git_label_uuid = uuid.UUID(git_label_id)  # Ensure it's a valid UUID

        git_label = await GitLabel.filter(
            id=git_label_uuid, user_id=authenticated_user.id
        ).first()
        if git_label:
            await git_label.delete()
        else:
            return APIResponse.error(
                message=app.exceptions.exception_constants.TOKEN_NOT_FOUND,
                status_code=status.HTTP_404_NOT_FOUND,
            )

        return APIResponse.success(message=constants.TOKEN_DELETED_SUCCESSFULLY)
    except ValueError:
        logger.exception(
            "Unexpected Failure while attempting to delete git label on Path = '[DELETE] /api/v1/git_tokens/{git_label_id}'"
        )

        return APIResponse.error(
            message="Invalid UUID format", status_code=status.HTTP_400_BAD_REQUEST
        )

    except Exception:

        logger.exception(
            "Unexpected Failure while attempting to delete git label on Path = '[DELETE] /api/v1/git_tokens/{git_label_id}'"
        )

        return APIResponse.error(
            message=SERVICE_UNAVAILABLE,
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        )
