"""
Git Label routes for the DevDox AI Portal API.

This module provides endpoints for managing Git tokens with CRUD operations.
It supports creating, reading, updating, and deleting git hosting service configurations.
"""
import logging
import uuid
from typing import Any, Dict, Optional

from fastapi import APIRouter, Body, Depends, Query, Request, status

from app.config import GitHosting
from app.models.git_label import GitLabel
from app.schemas.basic import PaginationParams
from app.schemas.git_label import (
	GitLabelCreate,
)
from app.utils import constants, CurrentUser
from app.utils.api_response import APIResponse
from app.utils.auth import AuthenticatedUserDTO
from app.utils.encryption import EncryptionHelper
from app.utils.github_manager import GitHubManager
from app.utils.gitlab_manager import GitLabManager

logger = logging.getLogger(__name__)

router = APIRouter()


def mask_token(token: str) -> str:
	"""
	Masks a token string by revealing only the first and last four characters.

	If the token is 8 characters or fewer, the entire token is replaced with asterisks.
	Returns an empty string if the input is empty.
	"""
	if not token or token.replace(" ", "") == "":
		return ""
	
	token_len = len(token)
	
	if token_len <= 8:
		return "*" * token_len
	
	prefix = token[:4]
	suffix = token[-4:]
	middle_mask = "*" * (token_len - 8)
	
	return f"{prefix}{middle_mask}{suffix}"


async def get_current_user_id() -> str:
	"""
	Dependency to get current user ID.
	In a real application, this would extract user ID from JWT token or session.
	For now, this is a placeholder that you should implement based on your auth system.
	"""
	# Will be changed
	# This could be from JWT token, session, or other auth mechanism
	return "user_2sw6NOnSajM1kpsLPA1ZnxCW3uZ"


async def handle_gitlab(
		payload: GitLabelCreate, encrypted_token: str
) -> Dict[str, Any]:
	"""Handle GitLab token validation and storage"""
	gitlab = GitLabManager(
		base_url="https://gitlab.com", access_token=payload.token_value
	)
	
	if not gitlab.auth_status:
		return APIResponse.error(message=constants.GITLAB_AUTH_FAILED)
	
	user = gitlab.get_user()
	if not user:
		return APIResponse.error(message=constants.GITLAB_USER_RETRIEVE_FAILED)
	
	try:
		git_label = await GitLabel.create(
			label=payload.label,
			user_id=payload.user_id,
			git_hosting=payload.git_hosting,
			token_value=encrypted_token,
			username=user.get("username", ""),
			masked_token=mask_token(payload.token_value),
		)
		
		return APIResponse.success(
			message=constants.TOKEN_SAVED_SUCCESSFULLY, data={"id": str(git_label.id)}
		)
	except Exception:
		logger.exception(
			"Unexpected Failure while attempting to save GitLab token on Path = '[POST] /api/v1/git_tokens' -> handle_gitlab")
		
		return APIResponse.error(
			message=constants.SERVICE_UNAVAILABLE,
			status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
		)


async def handle_github(
		payload: GitLabelCreate, encrypted_token: str
) -> Dict[str, Any]:
	"""Handle GitHub token validation and storage"""
	github = GitHubManager(access_token=payload.token_value)
	user = github.get_user()
	
	if not user:
		return APIResponse.error(
			message=constants.GITHUB_AUTH_FAILED,
			status_code=status.HTTP_400_BAD_REQUEST,
		)
	
	try:
		git_label = await GitLabel.create(
			label=payload.label,
			user_id=payload.user_id,
			git_hosting=payload.git_hosting,
			token_value=encrypted_token,
			username=user.get("login", ""),
			masked_token=mask_token(payload.token_value),
		)
		
		return APIResponse.success(
			message=constants.TOKEN_SAVED_SUCCESSFULLY, data={"id": str(git_label.id)}
		)
	except Exception:
		logger.exception(
			"Unexpected Failure while attempting to save GitHub token on Path = '[POST] /api/v1/git_tokens' -> handle_github")
		return APIResponse.error(message=constants.GITHUB_TOKEN_SAVE_FAILED)


@router.get(
	"/",
	response_model=Dict[str, Any],
	status_code=status.HTTP_200_OK,
	summary="Get all git labels",
	description="Retrieve a list of all git labels with masked token values",
)
async def get_git_labels(
		current_user_id: AuthenticatedUserDTO = CurrentUser,
		pagination: PaginationParams = Depends(),
		git_hosting: Optional[str] = Query(
			None, description="Filter by git hosting service"
		),
) -> Dict[str, Any]:
	"""
	Retrieves all stored git labels with masked token values for API response.

	Returns:
		APIResponse with list of git labels containing metadata and masked token values.
	"""
	try:
		# Build query for user's git labels
		query = GitLabel.filter(user_id=current_user_id.id)
		# Apply git_hosting filter if provided
		if git_hosting:
			query = query.filter(git_hosting=git_hosting)
		
		# Get total count
		total = await query.count()
		
		# Apply pagination and ordering
		git_labels = (
			await query.order_by("-created_at")
			.offset(pagination.offset)
			.limit(pagination.limit)
			.all()
		)
		
		# Format response data with masked tokens
		formatted_data = []
		for gl in git_labels:
			formatted_data.append(
				{
					"id": str(gl.id),
					"label": gl.label,
					"git_hosting": gl.git_hosting,
					"masked_token": mask_token(
						EncryptionHelper.decrypt(gl.token_value)
						if gl.token_value
						else ""
					),
					"username": gl.username,
					"created_at": gl.created_at.isoformat(),
					"updated_at": gl.updated_at.isoformat(),
				}
			)
		
		return APIResponse.success(
			message="Git labels retrieved successfully",
			data={
				"items": formatted_data,
				"total": total,
				"page": (pagination.offset // pagination.limit) + 1,
				"size": pagination.limit,
			},
		)
	except Exception:
		logger.exception("Failed to retrieve git labels")
		
		return APIResponse.error(
			message=constants.SERVICE_UNAVAILABLE,
			status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
		)


@router.get(
	"/{label}",
	response_model=Dict[str, Any],
	status_code=status.HTTP_200_OK,
	summary="Get git labels by label",
	description="Retrieve git labels matching the specified label with masked token values",
)
async def get_git_label_by_label(
		label: str,
		authenticated_user: AuthenticatedUserDTO = CurrentUser,
		pagination: PaginationParams = Depends(),
) -> Dict[str, Any]:
	"""
	Retrieves git labels matching the specified label with masked token values.

	Args:
		label: The label identifying the git labels to retrieve.

	Returns:
		APIResponse with list of matching git labels with masked token values.
	"""
	try:
		git_labels = (
			await GitLabel.filter(user_id=authenticated_user.id, label=label)
			.order_by("-created_at")
			.offset(pagination.offset)
			.limit(pagination.limit)
			.all()
		)
		
		# Format response data with masked tokens
		formatted_data = []
		for gl in git_labels:
			formatted_data.append(
				{
					"id": str(gl.id),
					"label": gl.label,
					"git_hosting": gl.git_hosting,
					"masked_token": gl.masked_token,
					"username": gl.username,
					"created_at": gl.created_at.isoformat(),
					"updated_at": gl.updated_at.isoformat(),
				}
			)
		
		return APIResponse.success(
			message="Git labels retrieved successfully", data={"items": formatted_data}
		)
	except Exception:
		logger.exception(
			"Unexpected Failure while attempting to retrieve git labels on Path = '[GET] /api/v1/git_tokens/{label}'")
		return APIResponse.error(
			message=constants.SERVICE_UNAVAILABLE,
			status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
		)


@router.post(
	"/",
	response_model=Dict[str, Any],
	status_code=status.HTTP_201_CREATED,
	summary="Add new git token",
	description="Create a new git hosting service token configuration",
)
async def add_git_token(
		request: Request,
		payload: GitLabelCreate = Body(...),
		authenticated_user: AuthenticatedUserDTO = CurrentUser,
) -> Dict[str, Any]:
	"""
	Add a new git token configuration with validation based on hosting service.
	"""
	try:
		# Override user_id with authenticated user ID for security
		payload.user_id = authenticated_user.id
		
		token = payload.token_value.replace(" ", "")
		if not token:
			return APIResponse.error(
				message=constants.TOKEN_MISSED,
				status_code=status.HTTP_400_BAD_REQUEST,
			)
		encrypted_token = EncryptionHelper.encrypt(token) if token else ""
		
		if payload.git_hosting == GitHosting.GITLAB.value:
			return await handle_gitlab(payload, encrypted_token)
		elif payload.git_hosting == GitHosting.GITHUB.value:
			return await handle_github(payload, encrypted_token)
		else:
			return APIResponse.error(
				message=constants.UNSUPPORTED_GIT_PROVIDER,
				status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
			)
	except Exception:
		
		logger.exception("Unexpected Failure while attempting to add git token on Path = '[POST] /api/v1/git_tokens'")
		
		return APIResponse.error(
			message=constants.SERVICE_UNAVAILABLE,
			status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
		)


@router.delete(
	"/{git_label_id}",
	response_model=Dict[str, Any],
	status_code=status.HTTP_200_OK,
	summary="Delete git label by ID",
	description="Delete a git label configuration by ID",
)
async def delete_git_label(
		git_label_id: str, current_user_id: str = Depends(get_current_user_id)
) -> Dict[str, Any]:
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
			id=git_label_uuid, user_id=current_user_id
		).first()
		if git_label:
			await git_label.delete()
		else:
			return APIResponse.error(
				message=constants.TOKEN_NOT_FOUND,
				status_code=status.HTTP_404_NOT_FOUND,
			)
		
		return APIResponse.success(message=constants.TOKEN_DELETED_SUCCESSFULLY)
	except ValueError as e:
		return APIResponse.error(
			message="Invalid UUID format", status_code=status.HTTP_400_BAD_REQUEST
		)
	
	except Exception:
		return APIResponse.error(
			message=constants.SERVICE_UNAVAILABLE,
			status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
		)
