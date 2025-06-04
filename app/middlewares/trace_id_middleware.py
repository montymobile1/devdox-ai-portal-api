"""
Trace ID middleware and logging integration for the DevDox AI Portal API.

This module enables full request traceability by assigning a `trace_id` to every API call.
It handles:

1. Reading an incoming `X-Trace-Id` HTTP header (if provided), or generating a new UUID.
2. Storing the trace ID in:
   - `request.state.trace_id`: used when you have access to the FastAPI `Request` object (e.g., in route handlers or exception handlers).
   - `trace_id_var` (`ContextVar`): used to automatically inject the trace ID into log records **without passing `Request` explicitly**.
3. Adding the trace ID back into the response header (`X-Trace-Id`), allowing clients to correlate responses with logs.

Why both `request.state` and `ContextVar`?

- `request.state.trace_id` is used in **places where you already have the `Request` object** (e.g., handlers, middleware, exception logic).
- `trace_id_var` is used for **deep logging contexts** where the `Request` object isn't passed (e.g., background jobs, utility functions, or anywhere logging occurs).

This separation ensures full traceability across all layers — from user-visible headers to logs — without requiring you to pass the `Request` object everywhere.

Usage:
- Add `TraceIDMiddleware` to your FastAPI app.
- Attach `TraceIDLogFilter` to all log handlers using `setup_logging()`.
"""

import logging
import uuid
from contextvars import ContextVar

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.types import ASGIApp

# The HTTP header name used to propagate the trace ID between systems
TRACE_HEADER_NAME = "X-Trace-Id"

# Global context variable holding the current trace ID.
# This allows the trace ID to be injected automatically into log records
# during the lifecycle of a single request.
trace_id_var: ContextVar[str] = ContextVar("trace_id", default="-")


class TraceIDLogFilter(logging.Filter):
    """
    Logging filter that injects the current request's trace ID into each log record.

    This filter retrieves the trace ID from the global `trace_id_var` ContextVar and
    attaches it to the `LogRecord`. Your formatter can then include it like:

        '%(asctime)s - %(name)s - %(levelname)s - [trace_id=%(trace_id)s] - %(message)s'

    This enables automatic trace ID logging across the app — even deep inside utility functions.

    Returns:
        True (to allow log record propagation)
    """

    def filter(self, record: logging.LogRecord) -> bool:
        record.trace_id = trace_id_var.get()
        return True


class TraceIDMiddleware(BaseHTTPMiddleware):
    """
    Middleware that ensures every request has a unique trace ID, and that it is
    available for logging, diagnostics, and response propagation.

    Workflow:
    1. If the client provides `X-Trace-Id`, use it. Otherwise, generate a new UUID.
    2. Store the trace ID in two locations:
       - `request.state.trace_id`: for direct use in route handlers or exception handlers.
       - `trace_id_var`: for indirect use (e.g., logging anywhere during request lifecycle).
    3. Add the trace ID to the response as the `X-Trace-Id` header.

    Benefits:
    - Your entire request lifecycle is traceable from logs to client to error reports.
    - You don’t need to manually pass the trace ID — logging will automatically include it.
    """

    def __init__(self, app: ASGIApp):
        """
        Initialize the middleware with the ASGI app instance.

        Args:
            app: The ASGI application to wrap.
        """
        super().__init__(app)

    async def dispatch(self, request: Request, call_next):
        """
        Assigns or forwards a trace ID, stores it, and appends it to the response.

        Args:
            request: The incoming request object.
            call_next: The next handler in the middleware or route chain.

        Returns:
            The response object with the `X-Trace-Id` header set.
        """
        # 1. Use incoming trace ID if provided, otherwise generate a new one
        incoming_trace_id = request.headers.get(TRACE_HEADER_NAME)
        trace_id = incoming_trace_id or str(uuid.uuid4())

        # 2. Store in request.state for explicit handler access
        request.state.trace_id = trace_id

        # 3. Store in ContextVar for global log access during the request
        trace_id_var.set(trace_id)

        # 4. Continue the request lifecycle and add trace ID to response
        response = await call_next(request)
        response.headers[TRACE_HEADER_NAME] = trace_id
        return response
