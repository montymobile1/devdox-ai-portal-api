from typing import Dict, Optional

from starlette import status

from app.exceptions.base_exceptions import DevDoxAPIException
from app.exceptions.exception_constants import (
    AUTH_FAILED,
    GENERIC_BAD_REQUEST,
    GENERIC_RESOURCE_NOT_FOUND,
    GENERIC_VALIDATION_FAILED_USER_MESSAGE,
)


class UnauthorizedAccess(DevDoxAPIException):
    http_status = status.HTTP_401_UNAUTHORIZED

    def __init__(self, reason=None, log_message=None, log_level=None):
        
        if not reason or not reason.strip():
            reason = AUTH_FAILED
        
        super().__init__(
            user_message=reason, log_message=log_message, log_level=log_level
        )


class BadRequest(DevDoxAPIException):
    http_status = status.HTTP_400_BAD_REQUEST

    def __init__(self, reason=None, log_message: Optional[str] = None):
        
        if not reason or not reason.strip():
            reason = GENERIC_BAD_REQUEST
        
        super().__init__(user_message=reason, log_message=log_message, log_level="warning")


class ResourceNotFound(DevDoxAPIException):
    http_status = status.HTTP_404_NOT_FOUND

    def __init__(self, reason=None):
        
        if not reason or not reason.strip():
            reason = GENERIC_RESOURCE_NOT_FOUND
        
        super().__init__(user_message=reason)

class ValidationFailed(DevDoxAPIException):
    http_status = status.HTTP_400_BAD_REQUEST

    def __init__(self, field_errors: Dict[str, list]):
        super().__init__(
            user_message=GENERIC_VALIDATION_FAILED_USER_MESSAGE,
            public_context=field_errors
        )
