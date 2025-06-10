# to simulate `HTTPAuthorizationCredentials`

import pytest
from fastapi.security import HTTPAuthorizationCredentials

from app.exceptions.exception_constants import INVALID_BEARER_TOKEN_SCHEMA
from tests.test_doubles.utils.auth.fake_authenticator import FakeAuthResult


def valid_bearer_token():
    return HTTPAuthorizationCredentials(scheme="Bearer", credentials="valid-token")


class MalformedSchemeTokensStub:

    error_msg = INVALID_BEARER_TOKEN_SCHEMA

    @staticmethod
    def malformed_scheme_tokens():
        return [
            pytest.param(
                HTTPAuthorizationCredentials(
                    scheme="Invalid", credentials="some-token"
                ),
                id="invalid_scheme",
            ),
            pytest.param(
                HTTPAuthorizationCredentials(scheme="", credentials="some-token"),
                id="empty_scheme",
            ),
            pytest.param(None, id="missing_header"),
        ]


def auth_stub_factory(signed_in, payload=None, reason_name=None, message=None):
    reason = type("Reason", (), {"name": reason_name})() if reason_name else None
    return lambda req, options: FakeAuthResult(
        signed_in, payload=payload, reason=reason, message=message
    )
