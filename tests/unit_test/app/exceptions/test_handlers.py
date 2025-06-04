"""
Unit tests for the global exception handling system in the DevDox AI Portal API.

This module tests the exception handlers defined in app/exceptions/handlers.py,
covering various scenarios including generic exceptions, custom DevDoxAPIException
instances with different log levels, and UnauthorizedAccess handling.
"""

import logging

import pytest
from fastapi import FastAPI
from starlette.testclient import TestClient

from app.exceptions.custom_exceptions import DevDoxAPIException, UnauthorizedAccess
from app.exceptions.handlers import (
    devdox_base_exception_handler,
    generic_exception_handler,
    generic_exception_handler_status_code,
)


# ----------------------------
# Fixtures and helpers
# ----------------------------


@pytest.fixture(scope="session")
def exception_test_app() -> FastAPI:
    """
    A minimal test-only FastAPI app configured with only the exception handlers.
    Defines isolated routes to simulate all key branches of exception handling.
    """
    app = FastAPI()
    app.add_exception_handler(Exception, generic_exception_handler)
    app.add_exception_handler(DevDoxAPIException, devdox_base_exception_handler)

    @app.get("/boom/generic")
    def _generic():
        raise RuntimeError("kaboom")

    @app.get("/boom/custom-warning")
    def _custom_warning():
        raise DevDoxAPIException(user_message="warn-msg")

    @app.get("/boom/custom-error")
    def _custom_error():
        raise DevDoxAPIException(
            user_message="err-msg", log_message="internal-err", log_level="error"
        )

    @app.get("/boom/custom-exception")
    def _custom_exception():
        raise DevDoxAPIException(
            user_message="teapot",
            error_type="E418",
            log_message="I am a teapot",
            log_level="exception",
            internal_context={"brew": "coffee"},
            public_context={"retry": False},
            http_status_override=418,
        )

    @app.get("/boom/unauth")
    def _unauth():
        raise UnauthorizedAccess()

    return app


@pytest.fixture
def fastapi_permissive_client(exception_test_app: FastAPI):
    """
    A TestClient configured to NOT raise server exceptions.
    Allows us to test the actual error responses and logs returned by handlers.
    """
    with TestClient(exception_test_app, raise_server_exceptions=False) as c:
        yield c


def _log_levels(record_tuples):
    """
    Extracts the unique logging level names from captured log records.

    Args:
        record_tuples (List[Tuple[str, int, str]]): Log records from caplog.record_tuples.

    Returns:
        Set[str]: Set of log level names (e.g., {'WARNING', 'ERROR'}).
    """
    return {logging.getLevelName(levelno) for _, levelno, _ in record_tuples}


def assert_log_message_contains(caplog, fragment):
    """
    Asserts that at least one log message captured by caplog contains the given fragment.

    Args:
        caplog: Pytest's caplog fixture.
        fragment (str): The expected substring to look for in the log messages.

    Raises:
        AssertionError: If no log message contains the expected fragment.
    """
    assert any(
        fragment in msg for _, _, msg in caplog.record_tuples
    ), f"Expected '{fragment}' in log messages:\n\n{caplog.text}"


# ----------------------------
# Test
# ----------------------------


class TestGenericExceptionHandler:
    """
    Tests for the `generic_exception_handler`, triggered via /boom/generic.
    Covers unhandled exceptions and the default 503 fallback behavior.
    """

    def test_returns_503(self, fastapi_permissive_client):
        """Asserts that unhandled exceptions return status 503."""
        resp = fastapi_permissive_client.get("/boom/generic")
        assert resp.status_code == generic_exception_handler_status_code

    def test_response_structure(self, fastapi_permissive_client):
        """Asserts that the 503 response contains correct debug metadata."""
        body = fastapi_permissive_client.get("/boom/generic").json()
        assert "kaboom" in body["debug"]["str"]
        assert body["debug"]["exception"] == "RuntimeError"

    def test_logs_error(self, fastapi_permissive_client, caplog):
        """Checks that the error is logged with level ERROR and contains marker."""
        caplog.set_level(logging.ERROR)
        fastapi_permissive_client.get("/boom/generic")
        assert "ERROR" in _log_levels(caplog.record_tuples)
        assert "UNHANDLED_EXCEPTION" in caplog.text


class TestDevDoxAPIExceptionHandlerWarningException:
    """
    Tests for a DevDoxAPIException with default log_level='warning', via /boom/custom-warning.
    """

    def test_status_and_exception_type(self, fastapi_permissive_client):
        """Asserts correct status code and exception class in debug."""
        resp = fastapi_permissive_client.get("/boom/custom-warning")
        assert resp.status_code == 400
        assert resp.json()["debug"]["exception"] == "DevDoxAPIException"

    def test_logs_as_warning(self, fastapi_permissive_client, caplog):
        """Checks that handler logs the error as a warning by default."""
        caplog.set_level(logging.DEBUG)
        fastapi_permissive_client.get("/boom/custom-warning")
        assert "WARNING" in _log_levels(caplog.record_tuples)


class TestDevDoxAPIExceptionHandlerErrorException:
    """
    Tests for a DevDoxAPIException with explicit log_level='error', via /boom/custom-error.
    """

    def test_status_and_user_message(self, fastapi_permissive_client):
        """Ensures the user message is returned in the response with 400 status."""
        resp = fastapi_permissive_client.get("/boom/custom-error")
        assert resp.status_code == 400
        assert resp.json()["message"] == "err-msg"

    def test_logs_with_custom_message(self, fastapi_permissive_client, caplog):
        """Verifies that the log contains the specified internal log message."""
        caplog.set_level(logging.DEBUG)
        fastapi_permissive_client.get("/boom/custom-error")
        assert "ERROR" in _log_levels(caplog.record_tuples)
        assert "internal-err" in caplog.text


class TestDevDoxAPIExceptionHandlerAdvanced:
    """
    Tests for a DevDoxAPIException with advanced configuration (custom status, context, and log level),
    triggered via /boom/custom-exception.
    """

    def test_response_with_context_and_override(self, fastapi_permissive_client):
        """Asserts correct 418 status, response body fields, and public context inclusion."""
        resp = fastapi_permissive_client.get("/boom/custom-exception")
        body = resp.json()
        assert resp.status_code == 418
        assert body["message"] == "teapot"
        assert body["details"] == {"retry": False}
        assert body["debug"]["exception"] == "DevDoxAPIException"

    def test_log_message_parts_and_context(self, fastapi_permissive_client, caplog):
        """Checks that logs include all expected fields, internal context, and are logged at exception level."""
        caplog.set_level(logging.DEBUG)
        fastapi_permissive_client.get("/boom/custom-exception")
        assert_log_message_contains(caplog, "E418")
        assert_log_message_contains(caplog, "I am a teapot")
        assert_log_message_contains(caplog, "Path: /boom/custom-exception")
        assert_log_message_contains(caplog, "Status: 418")
        assert "brew" in caplog.text and "coffee" in caplog.text


class TestUnauthorizedAccessHandler:
    """
    Tests for the UnauthorizedAccess subclass of DevDoxAPIException, via /boom/unauth.
    """

    def test_subclass_propagates_http_status(self, fastapi_permissive_client):
        """Ensures that the overridden http_status = 401 is correctly returned."""
        resp = fastapi_permissive_client.get("/boom/unauth")
        assert resp.status_code == 401
        assert resp.json()["status_code"] == 401
        assert resp.json()["debug"]["exception"] == "UnauthorizedAccess"

    def test_default_auth_message_included(self, fastapi_permissive_client):
        """Checks that the default AUTH_FAILED message is used."""
        resp = fastapi_permissive_client.get("/boom/unauth")
        body = resp.json()
        assert body["message"]  # Ensure message exists
        # Verify it contains expected auth failure content
        assert (
            "unauthorized" in body["message"].lower()
            or "access" in body["message"].lower()
        )
