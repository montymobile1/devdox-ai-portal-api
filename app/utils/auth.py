"""
Clerk authentication utility for the DevDox AI Portal API.
"""
from dataclasses import dataclass, fields
from typing import Any, ClassVar, Dict

from clerk_backend_api import authenticate_request, AuthenticateRequestOptions
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.config import settings
from app.utils.system_messages import INVALID_BEARER_TOKEN_SCHEMA

http_bearer_security_schema = HTTPBearer(auto_error=False)


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
	_clerk_key_to_field: ClassVar[Dict[str, str]] = {
		"sub": "id"
	}
	
	@classmethod
	def from_clerk_payload(cls, payload: Dict[str, Any]) -> tuple[list[str], "AuthenticatedUserDTO"]:
		# Maps each DTO field to its corresponding Clerk payload key (uses alias if defined, else assumes same name)
		dto_field_to_clerk_key = {
			f.name: next((k for k, v in cls._clerk_key_to_field.items() if v == f.name), f.name)
			for f in fields(cls) if f.init
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


def get_current_user(
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
		raise HTTPException(
			status_code=status.HTTP_401_UNAUTHORIZED,
			detail=INVALID_BEARER_TOKEN_SCHEMA,
			headers={"WWW-Authenticate": "Bearer"},
		)
	
	auth_result = authenticate_request(
		request_from_context,
		AuthenticateRequestOptions(secret_key=settings.CLERK_API_KEY)
	)
	
	if not auth_result.is_signed_in:
		reason = auth_result.reason.name if auth_result.reason else "UNKNOWN"
		message = auth_result.message or "Authentication failed for unknown reasons."
		
		# TODO: WILL BE REPLACED BY A LOGGER IN THE FUTURE
		print(
			f"[MAYBE Debug or Error]"
			f"[Clerk Auth Failure] Reason: {auth_result.reason.name if auth_result.reason else 'UNKNOWN'} | "
			f"Message: {auth_result.message or 'Authentication failed.'} | "
			f"Path: {request_from_context.url.path}"
		)
		
		raise HTTPException(
			status_code=status.HTTP_401_UNAUTHORIZED,
			detail={
				"error": "not_authenticated",
				"summary": "Access denied. Authentication failed.",
				"reason": reason,
			}
		)
	
	payload = auth_result.payload
	
	# Extract user information from the JWT payload
	
	missing_payload_fields, user_dto = AuthenticatedUserDTO.from_clerk_payload(payload)
	
	if missing_payload_fields:
		# TODO: Replace with real logger
		print(
			f"[ERROR] | "
			f"[Payload Validation From Clerk Failure] Reason: Missing required payload fields | "
			f"Message: Fields from clerk Payload are missing: {missing_payload_fields} | "
			f"Path: {request_from_context.url.path}"
		)
		
		raise HTTPException(
			status_code=status.HTTP_401_UNAUTHORIZED,
			detail=INVALID_BEARER_TOKEN_SCHEMA,
			headers={"WWW-Authenticate": "Bearer"},
		)
	
	return user_dto


# Dependency for authenticated routes
CurrentUser = Depends(get_current_user)
