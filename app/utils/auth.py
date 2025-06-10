"""
Clerk authentication utility for the DevDox AI Portal API.
"""

import logging
from dataclasses import dataclass, fields
from typing import Any, ClassVar, Dict, Optional, Protocol

from clerk_backend_api import (
    authenticate_request,
    AuthenticateRequestOptions,
    Requestish,
)
from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel

from app.config import settings
from app.exceptions.custom_exceptions import UnauthorizedAccess
from app.exceptions.exception_constants import INVALID_BEARER_TOKEN_SCHEMA

http_bearer_security_schema = HTTPBearer(auto_error=False)

logger = logging.getLogger(__name__)

# ===================================================================================
# TODO: THIS SECTION WILL BE DEPRECATED SLOWLY AS WE GO IN FAVOR OF THE OTHER NEW PART
# ===================================================================================

@dataclass
class AuthenticatedUserDTO:
    id: str
    email: str
    name: str

    # Maps specific Clerk JWT payload keys to this DTO's field names.
    #
    # By default, each field in this dataclass is expected to match a key in the Clerk payload exactly.
    # However, if a Clerk key and the field name differ (e.g., "sub" → "id"), define the mapping here.
    #
    # This is **not** an exhaustive map, only override fields where the names differ.
    # Fields not listed here are assumed to have the same name in both Clerk's payload and the DTO.
    #
    # Example:
    #     Clerk:  { "sub": "user_123", "email": "user@example.com" }
    #     DTO:    AuthenticatedUserDTO(id="user_123", email="user@example.com")
    #     Mapping: { "sub": "id" }
    _clerk_key_to_field: ClassVar[Dict[str, str]] = {"sub": "id"}

    @classmethod
    def from_clerk_payload(
        cls, payload: Dict[str, Any]
    ) -> tuple[list[str], "AuthenticatedUserDTO"]:
        # Maps each DTO field to its corresponding Clerk payload key (uses alias if defined, else assumes same name)
        dto_field_to_clerk_key = {
            f.name: next(
                (k for k, v in cls._clerk_key_to_field.items() if v == f.name), f.name
            )
            for f in fields(cls)
            if f.init
        }

        # Extract values from the payload using resolved Clerk keys → DTO fields
        dto_field_values = {
            field_name: payload.get(clerk_key)
            for field_name, clerk_key in dto_field_to_clerk_key.items()
        }

        # Track any required Clerk keys that were missing from the payload
        missing_clerk_keys_in_payload = [
            clerk_key
            for field_name, clerk_key in dto_field_to_clerk_key.items()
            if clerk_key not in payload
        ]

        return missing_clerk_keys_in_payload, cls(**dto_field_values)


async def get_current_user(
    request_from_context: Request,
    auth_header: HTTPAuthorizationCredentials = Depends(http_bearer_security_schema),
) -> AuthenticatedUserDTO:
    """
    Get the current authenticated user from JWT token.

    Args:
            request (Request): FastAPI request object.

    Returns:
            Dict: User information.

    Raises:
            HTTPException: If token is missing or invalid.
    """
    if auth_header is None or auth_header.scheme.lower() != "bearer":
        raise UnauthorizedAccess(reason=INVALID_BEARER_TOKEN_SCHEMA)

    auth_result = authenticate_request(
        request_from_context,
        AuthenticateRequestOptions(secret_key=settings.CLERK_API_KEY),
    )

    if not auth_result.is_signed_in:
        reason = auth_result.reason.name if auth_result.reason else "UNKNOWN"
        message = auth_result.message or "Authentication failed for unknown reasons."

        raise UnauthorizedAccess(
            log_message=f"Clerk failed to authenticate for | Reason: {reason} | Message: {message} | "
        )

    payload = auth_result.payload

    # Extract user information from the JWT payload

    missing_payload_fields, user_dto = AuthenticatedUserDTO.from_clerk_payload(payload)

    if missing_payload_fields:
        raise UnauthorizedAccess(
            reason=INVALID_BEARER_TOKEN_SCHEMA,
            log_message=f"Fields from clerk Payload are missing: {missing_payload_fields}",
            log_level="exception",
        )

    return user_dto


# Dependency for authenticated routes
CurrentUser = Depends(get_current_user)

# ===================================================================================
# TODO: This is the new easily testable, less complicated Auth system
# ===================================================================================

class UserClaims(BaseModel):
    sub: str
    email: Optional[str] = None
    name: Optional[str] = None

class IUserAuthenticator(Protocol):
    async def authenticate(self, request: Requestish) -> UserClaims:
        ...

class ClerkUserAuthenticator(IUserAuthenticator):
    async def authenticate(self, request: Requestish) -> UserClaims:
        auth_result = authenticate_request(
            request,
            AuthenticateRequestOptions(secret_key=settings.CLERK_API_KEY),
        )

        if not auth_result.is_signed_in:
            reason = auth_result.reason.name if auth_result.reason else "UNKNOWN"
            message = auth_result.message or "Authentication failed for unknown reasons."

            raise UnauthorizedAccess(
                log_message=f"Clerk failed to authenticate | Reason: {reason} | Message: {message}"
            )

        payload = auth_result.payload
        user = UserClaims(**payload)
        user_id_var.set(user.sub)
        return user

def get_user_authenticator_dependency() -> IUserAuthenticator:
    return ClerkUserAuthenticator()

async def get_authenticated_user(
    request: Request,
    auth_header: HTTPAuthorizationCredentials = Depends(http_bearer_security_schema),
    authenticator: IUserAuthenticator = Depends(get_user_authenticator_dependency)
) -> UserClaims:
    if auth_header is None or auth_header.scheme.lower() != "bearer":
        raise UnauthorizedAccess(reason=INVALID_BEARER_TOKEN_SCHEMA)
    return await authenticator.authenticate(request)
