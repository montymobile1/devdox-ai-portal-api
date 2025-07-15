"""
Clerk authentication utility for the DevDox AI Portal API.
"""

import logging
from typing import Optional, Protocol

from clerk_backend_api import (
    authenticate_request,
    AuthenticateRequestOptions,
    Requestish,
)
from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, ConfigDict
from starlette.concurrency import run_in_threadpool

from app.config import settings
from app.exceptions.custom_exceptions import UnauthorizedAccess
from app.exceptions.exception_constants import (
    CLERK_AUTH_FAILED,
    CLERK_AUTH_FAILED_LOG_MESSAGE,
    INVALID_BEARER_TOKEN_SCHEMA,
    UNKNOWN_REASON,
)

http_bearer_security_schema = HTTPBearer(auto_error=False)

logger = logging.getLogger(__name__)


class UserClaims(BaseModel):
    sub: str
    email: Optional[str] = None
    name: Optional[str] = None

    model_config = ConfigDict(extra="ignore")


class IUserAuthenticator(Protocol):
    async def authenticate(self, request: Requestish) -> UserClaims: ...


class ClerkUserAuthenticator(IUserAuthenticator):
    async def authenticate(self, request: Requestish) -> UserClaims:
        auth_result = await run_in_threadpool(
            authenticate_request,
            request,
            AuthenticateRequestOptions(secret_key=settings.CLERK_API_KEY),
        )

        if not auth_result.is_signed_in:
            reason = auth_result.reason.name if auth_result.reason else UNKNOWN_REASON
            message = (
                auth_result.message or CLERK_AUTH_FAILED
            )

            raise UnauthorizedAccess(
                log_message=CLERK_AUTH_FAILED_LOG_MESSAGE.format(reason=reason, message=message)
            )

        payload = auth_result.payload
        user = UserClaims(**payload)
        return user


def get_user_authenticator_dependency() -> IUserAuthenticator:
    return ClerkUserAuthenticator()


async def get_authenticated_user(
    request: Request,
    auth_header: HTTPAuthorizationCredentials = Depends(http_bearer_security_schema),
    authenticator: IUserAuthenticator = Depends(get_user_authenticator_dependency),
) -> UserClaims:
    if auth_header is None or auth_header.scheme.lower() != "bearer":
        raise UnauthorizedAccess(
            reason=INVALID_BEARER_TOKEN_SCHEMA, log_message=INVALID_BEARER_TOKEN_SCHEMA
        )
    return await authenticator.authenticate(request)
