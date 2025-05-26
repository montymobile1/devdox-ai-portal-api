"""
Clerk authentication utility for the DevDox AI Portal API.
"""
from dataclasses import dataclass
from typing import ClassVar, Dict

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
	# Add other user fields as needed, and dont forget to add the mapping in _clerk_payload_mapping
	
	_clerk_payload_mapping: ClassVar[Dict[str, str]] = {
		"sub": "id",
		"email": "email",
		"name": "name"
	}
	
	@classmethod
	def from_clerk_payload(cls, payload: Dict) -> "AuthenticatedUserDTO":
		missing_fields = [
			clerk_key
			for clerk_key in cls._clerk_payload_mapping
			if clerk_key not in payload
		]
		
		if missing_fields:
			raise ValueError(f"{missing_fields}")
		
		mapped_fields = {
			cls._clerk_payload_mapping[clerk_key]: payload[clerk_key]
			for clerk_key in cls._clerk_payload_mapping
		}
		
		return cls(**mapped_fields)


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
				"debug_message": message,
			}
		)
	
	payload = auth_result.payload
	
	# Extract user information from the JWT payload
	
	try:
		user_dto = AuthenticatedUserDTO.from_clerk_payload(payload)
	except ValueError as ve:
		# TODO: Replace with real logger
		print(
			f"[ERROR] | "
			f"[Payload Validation From Clerk Failure] Reason: Missing required payload fields | "
			f"Message: Fields from clerk Payload are missing: {ve} | "
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
