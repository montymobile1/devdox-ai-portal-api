"""
Exception registration module for the DevDox AI Portal API.

This module is responsible for binding all exception handlers defined in `handlers.py`
to the FastAPI application instance.

Use the `register_exception_handlers(app)` function during app initialization
to ensure that global and custom exception handlers are properly wired in.

This centralizes error handling configuration, keeping the main app setup clean
and ensuring that all exceptions are processed through the defined logic in `handlers.py`.
"""
from dataclasses import asdict

from fastapi.exceptions import RequestValidationError
from starlette.requests import Request

from app.config import settings
from fastapi import FastAPI

from app.exceptions.custom_exceptions import DevDoxAPIException
from app.exceptions.exception_handlers import (
    devdox_base_exception_handler,
    generic_exception_handler,
    validation_exception_handler,
)
from app.utils.api_response import APIResponse


def handle_exception_debug_payload(exc):
    debug_payload = None
    if settings.API_ENV in {"development", "test"}:
        debug_payload = {"exception": type(exc).__name__, "str": str(exc)}

    return debug_payload


def handle_validation_debug_payload(exc):
    debug_payload = None
    if settings.API_ENV in {"development", "test"}:
        debug_payload = {"raw": exc.errors()}

    return debug_payload


def manage_generic_exception(request: Request, exc: Exception):
    payload = generic_exception_handler(request, exc)
    payload.debug = handle_exception_debug_payload(exc)

    return APIResponse.error(**asdict(payload))

def manage_dev_dox_base_exception(request: Request, exc: DevDoxAPIException):
    payload = devdox_base_exception_handler(request, exc)
    payload.debug = handle_exception_debug_payload(exc)

    return APIResponse.error(**asdict(payload))


def manage_validation_exception(request: Request, exc: RequestValidationError):
    """
    example return:
    ```
            {
          "success": false,
          "message": "Your request contains validation errors",
          "status_code": 400,
          "error_type": "VALIDATIONFAILED",
          "details": {
            "label": [
              "String should have at most 100 characters"
            ],
            "token_value": [
              "String should have at most 100 characters"
            ]
          }
        }
    ```
    """
    payload = validation_exception_handler(request, exc)
    payload.debug = handle_validation_debug_payload(exc)

    return APIResponse.error(**asdict(payload))


def register_exception_handlers(app: FastAPI):
    """
    Register all exception handlers with the FastAPI application.

    Args:
        app: The FastAPI application instance to register handlers with.
    """
    app.add_exception_handler(Exception, manage_generic_exception)
    app.add_exception_handler(DevDoxAPIException, manage_dev_dox_base_exception)
    app.add_exception_handler(RequestValidationError, manage_validation_exception)
