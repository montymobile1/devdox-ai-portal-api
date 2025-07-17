"""
Exception handling module for the DevDox AI Portal API.

This module contains all application-wide exception handlers, including custom handlers
(e.g. for domain-specific exceptions) and the fallback handler for unhandled errors.

To keep the main application setup clean, all exception handlers defined here are registered
via the centralized `register.py` module. That module exposes a `register_exception_handlers(app)`
function which imports this file and binds each handler to the FastAPI app instance.

If you are adding a new custom exception and want it globally handled:
1. Define its handler function here.
2. Import and register it inside `register_exception_handlers()` in `register.py`.

This ensures a clean separation of concerns:
- `handlers.py` = defines the logic of how to respond to errors
- `register.py` = plugs that logic into the FastAPI lifecycle
"""

import logging
from typing import Dict

from fastapi.exceptions import RequestValidationError
from starlette import status
from starlette.requests import Request

from app.exceptions import exception_constants
from app.exceptions.custom_exceptions import (
    DevDoxAPIException,
    ErrorPayload,
    ValidationFailed,
)

logger = logging.getLogger(__name__)

generic_exception_handler_status_code = status.HTTP_503_SERVICE_UNAVAILABLE


def generic_exception_handler(request: Request, exc: Exception) -> ErrorPayload:
    """
    Handle all uncaught exceptions with standardized error response.

    Args:
        request: The incoming request that triggered the exception
        exc: The uncaught exception

    Returns:
        Standardized error response dictionary
    """
    
    path = request.url.path
    method = getattr(request, "method", None) or request.scope.get("method") or "HTTP"
    exc_type = type(exc).__name__
    status_code = generic_exception_handler_status_code

    logger.exception(
        "[UNHANDLED_EXCEPTION] %s occurred | Path: %s | Method: %s | Status: %s",
        exc_type,
        path,
        method,
        status_code,
    )
    
    error_report = ErrorPayload(
        message=exception_constants.SERVICE_UNAVAILABLE,
        status_code=status_code,
        error_type=exc_type,
    )

    return error_report

def devdox_base_exception_handler(
    request: Request, exc: DevDoxAPIException
) -> ErrorPayload:
    """
    Handle DevDoxAPIException with structured logging and response.

    Args:
        request: The incoming request that triggered the exception
        exc: The DevDoxAPIException instance

    Returns:
        Standardized error response dictionary with optional debug info
    """
    path = request.url.path
    method = getattr(request, "method", None) or request.scope.get("method") or "HTTP"
    exc_error_type = exc.error_type
    
    log_extra = {}
    
    log_parts = [
        f"[{exc_error_type}] {exc.log_message}",
        f"Path: {path}",
        f"Method: {method}",
        f"Http Status: {exc.http_status}",
    ]

    if exc.internal_context:
        log_extra["internal_context"]= exc.internal_context

    # Combine all parts into the final message
    log_message = " | ".join(log_parts)

    # Log with traceback if `from e` __context__ present
    extra_for_logs = log_extra if log_extra else None
    
    if exc.log_level == "error":
        logger.error(log_message, exc_info=exc.__cause__ or exc, extra=extra_for_logs)
    elif exc.log_level == "exception":
        logger.exception(log_message, exc_info=exc.__cause__ or exc, extra=extra_for_logs)
    else:
        logger.warning(log_message, extra=extra_for_logs)
    
    return ErrorPayload(
        message=exc.user_message,
        status_code=exc.http_status,
        details=exc.public_context,
        error_type=exc_error_type,
    )

def validation_exception_handler(request: Request, exc: RequestValidationError) -> ErrorPayload:
    """
    Catch FastAPI/Pydantic validation errors and return structured per-field feedback.
    """
    # Group errors by field
    field_errors: Dict[str, list] = {}

    for err in exc.errors():
        # Remove "body"/"query"/"path"/etc. from loc and turn it into a dotted field name
        loc_parts = [str(part) for part in err["loc"] if part not in {"body", "query", "path", "header"}]
        field = ".".join(loc_parts) or "general"
        field_errors.setdefault(field, []).append(err["msg"])

    exception = ValidationFailed(field_errors)

    error_report = ErrorPayload(
        message=exception.user_message,
        status_code=exception.http_status,
        details=exception.public_context,
        error_type=exception.error_type
    )

    return error_report
