from typing import Annotated, Any, Dict

from fastapi import APIRouter, Depends
from starlette import status
from starlette.responses import JSONResponse

from app.schemas.api_key_schema import APIKeyRevokeRequest
from app.services.api_keys_service import PostApiKeyService, RevokeApiKeyService
from app.utils import constants
from app.utils.api_response import APIResponse
from app.utils.auth import get_authenticated_user, UserClaims

router = APIRouter()


@router.post(
    "/",
    response_model=Dict[str, Any],
    status_code=status.HTTP_201_CREATED,
    summary="Create a new API key",
    description="Create a new API key for the authenticated user",
)
async def add_new_api_key(
    user_claims: Annotated[UserClaims, Depends(get_authenticated_user)],
    service: Annotated[PostApiKeyService, Depends(PostApiKeyService.with_dependency)],
) -> JSONResponse:
    """
    Generate a new API key
    """
    db_id, plain_key = await service.generate_api_key(user_claims=user_claims)

    return APIResponse.success(
        message=constants.API_KEY_GENERATED_SUCCESSFULLY,
        data={"id": db_id, "api_key": plain_key},
    )


@router.delete(
    "/{api_key_id}",
    response_model=Dict[str, Any],
    status_code=status.HTTP_201_CREATED,
    summary="Revokes an api key",
    description="Revokes the API Key via the database api key id, applying a soft delete",
)
async def revoke_api_key(
    user_claims: Annotated[UserClaims, Depends(get_authenticated_user)],
    request: Annotated[APIKeyRevokeRequest, Depends()],
    service: Annotated[
        RevokeApiKeyService, Depends(RevokeApiKeyService.with_dependency)
    ],
) -> JSONResponse:
    """
    Generate a new API key
    """
    await service.revoke_api_key(
        user_claims=user_claims, api_key_id=request.api_key_id
    )

    return APIResponse.success(
        message=constants.API_KEY_REVOKED_SUCCESSFULLY
    )
