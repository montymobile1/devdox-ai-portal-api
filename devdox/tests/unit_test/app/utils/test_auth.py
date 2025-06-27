import pytest
from clerk_backend_api import Requestish
from clerk_backend_api.jwks_helpers import AuthStatus
from fastapi.security import HTTPAuthorizationCredentials
from starlette.requests import Request

from app.exceptions.custom_exceptions import UnauthorizedAccess
from app.exceptions.exception_constants import INVALID_BEARER_TOKEN_SCHEMA
from app.utils.auth import (
    ClerkUserAuthenticator,
    get_authenticated_user,
    IUserAuthenticator,
    UserClaims,
)


class FakeSuccessAuthenticator(IUserAuthenticator):
    async def authenticate(self, request: Requestish) -> UserClaims:
        return UserClaims(sub="user-123", email="test@example.com", name="Test User")


class FakeFailureAuthenticator(IUserAuthenticator):

    exception_msg = "Forced failure during authentication"

    async def authenticate(self, request: Requestish) -> UserClaims:
        raise Exception(self.exception_msg)


class FakeInvalidTokenAuthenticator(IUserAuthenticator):

    reason = "token-invalid"
    log_message = "Simulated Clerk token verification failure"

    async def authenticate(self, request: Requestish):
        raise UnauthorizedAccess(reason=self.reason, log_message=self.log_message)


class FakeRequest:
    def __init__(self, headers):
        self.headers = headers


class FakeAuthResult:
    def __init__(self, signed_in: bool, payload=None, reason=None, message=None):
        self.status = (
            AuthStatus.SIGNED_IN.value if signed_in else AuthStatus.SIGNED_OUT.value
        )
        self.payload = payload or {}
        self.reason = reason
        self._message = message

    @property
    def is_signed_in(self):
        return self.status == AuthStatus.SIGNED_IN.value

    @property
    def message(self):
        return self._message


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


class TestGetAuthenticationUser:

    @pytest.mark.asyncio
    async def test_success(self):
        request = Request({"type": "http"})
        header = valid_bearer_token()

        user = await get_authenticated_user(
            request, header, authenticator=FakeSuccessAuthenticator()
        )
        assert isinstance(user, UserClaims)
        assert user.sub == "user-123"

    @pytest.mark.parametrize(
        "header", MalformedSchemeTokensStub.malformed_scheme_tokens()
    )
    @pytest.mark.asyncio
    async def test_invalid_or_missing_scheme_raises(self, header):
        request = Request({"type": "http"})

        with pytest.raises(UnauthorizedAccess) as exc:
            await get_authenticated_user(
                request, header, authenticator=FakeSuccessAuthenticator()
            )

        assert MalformedSchemeTokensStub.error_msg in exc.value.log_message

    @pytest.mark.asyncio
    async def test_authenticator_fails(self):
        request = Request({"type": "http"})
        header = valid_bearer_token()

        with pytest.raises(Exception) as exc:
            await get_authenticated_user(
                request, header, authenticator=FakeFailureAuthenticator()
            )

        assert FakeFailureAuthenticator.exception_msg in str(exc.value)

    @pytest.mark.asyncio
    async def test_clerk_token_invalid(self):
        request = Request({"type": "http"})
        header = valid_bearer_token()

        with pytest.raises(UnauthorizedAccess) as exc:
            await get_authenticated_user(
                request, header, authenticator=FakeInvalidTokenAuthenticator()
            )

        assert FakeInvalidTokenAuthenticator.log_message in exc.value.log_message
        assert FakeInvalidTokenAuthenticator.reason in exc.value.user_message


class TestClerkUserAuthenticator:

    @staticmethod
    def __patch_clerk_authentication_result(
        monkeypatch, *, signed_in, payload=None, reason_name=None, message=None
    ):
        reason = type("Reason", (), {"name": reason_name})() if reason_name else None
        result = FakeAuthResult(
            signed_in, payload=payload, reason=reason, message=message
        )
        monkeypatch.setattr("app.utils.auth.authenticate_request", lambda *_: result)

    @pytest.mark.asyncio
    async def test_successful_authentication(self, monkeypatch):
        fake_payload = {"sub": "user-1", "email": "a@b.com", "name": "Test"}
        self.__patch_clerk_authentication_result(
            monkeypatch, signed_in=True, payload=fake_payload
        )

        request = FakeRequest(headers={"authorization": "Bearer token"})
        user = await ClerkUserAuthenticator().authenticate(request)

        assert isinstance(user, UserClaims)
        assert user.sub == fake_payload["sub"]

    @pytest.mark.asyncio
    async def test_signed_out_with_reason(self, monkeypatch):
        self.__patch_clerk_authentication_result(
            monkeypatch,
            signed_in=False,
            reason_name="TOKEN_EXPIRED",
            message="Token expired",
        )

        request = FakeRequest(headers={"authorization": "Bearer token"})
        with pytest.raises(UnauthorizedAccess) as exc:
            await ClerkUserAuthenticator().authenticate(request)

        assert "TOKEN_EXPIRED" in exc.value.log_message
        assert "Token expired" in exc.value.log_message

    @pytest.mark.asyncio
    async def test_signed_out_without_reason(self, monkeypatch):
        self.__patch_clerk_authentication_result(monkeypatch, signed_in=False)

        request = FakeRequest(headers={"authorization": "Bearer token"})
        with pytest.raises(UnauthorizedAccess) as exc:
            await ClerkUserAuthenticator().authenticate(request)

        assert "UNKNOWN" in exc.value.log_message
