import copy
from dataclasses import asdict
from unittest.mock import MagicMock, patch

import pytest
from clerk_backend_api import models
from clerk_backend_api.jwks_helpers import AuthErrorReason
from fastapi import status
from fastapi.security import HTTPAuthorizationCredentials
from starlette.datastructures import Headers
from starlette.requests import Request

import app.exceptions.exception_constants
from app.exceptions.custom_exceptions import UnauthorizedAccess
from app.exceptions.exception_constants import INVALID_BEARER_TOKEN_SCHEMA
from app.utils import get_authenticated_user
from app.utils.auth import (
    AuthenticatedUserDTO,
    ClerkUserAuthenticator,
    get_current_user,
    UserClaims,
)
from tests.test_doubles.utils.auth.fake_authenticator import (
    FakeAuthResult,
    FakeFailureAuthenticator,
    FakeInvalidTokenAuthenticator,
    FakeRequest,
    FakeSuccessAuthenticator,
)
from tests.test_doubles.utils.auth.stub_http_header import (
    MalformedSchemeTokensStub,
    valid_bearer_token,
)

# ===================================================================================
# TODO: THIS SECTION WILL BE DEPRECATED SLOWLY AS WE GO IN FAVOR OF THE OTHER NEW PART
# ===================================================================================

base_clerk_payload_schema = {
    "sub": "user_abc",
    "email": "abc@example.com",
    "name": "Abc",
}


def fake_request(headers: dict = None, path="/fake") -> Request:
    scope = {
        "type": "http",
        "method": "GET",
        "path": path,
        "headers": Headers(headers or {}).raw,
    }
    return Request(scope)


def make_auth_header(token="fake-token", scheme="Bearer"):
    return HTTPAuthorizationCredentials(scheme=scheme, credentials=token)


class TestFromClerkPayload:
    def test_valid_payload_is_correctly_mapped_when_all_values_present(self):
        payload = copy.deepcopy(base_clerk_payload_schema)
        expected = {
            AuthenticatedUserDTO._clerk_key_to_field.get(k, k): v
            for k, v in payload.items()
        }
        missing, dto = AuthenticatedUserDTO.from_clerk_payload(payload)
        assert missing == []
        assert asdict(dto) == expected

    def test_payload_with_all_keys_but_none_values(self):
        payload = {k: None for k in base_clerk_payload_schema.keys()}
        expected = {
            AuthenticatedUserDTO._clerk_key_to_field.get(k, k): None for k in payload
        }
        missing, dto = AuthenticatedUserDTO.from_clerk_payload(payload)
        assert missing == []
        assert asdict(dto) == expected

    def test_invalid_payload_missing_required_fields(self):
        payload = {}
        expected_missing = set(base_clerk_payload_schema.keys())
        missing, dto = AuthenticatedUserDTO.from_clerk_payload(payload)
        assert set(missing) == expected_missing

    def test_extra_fields_in_payload_are_ignored(self):
        """Extra fields in payload that aren't in DTO should be ignored silently."""
        payload = {**base_clerk_payload_schema, "extra_key": "should not be mapped"}
        missing, dto = AuthenticatedUserDTO.from_clerk_payload(payload)
        dto_dict = asdict(dto)
        assert "extra_key" not in dto_dict


class TestGetCurrentUserNormal:
    @pytest.mark.asyncio
    async def test_successful_user_parsing(self):
        payload = copy.deepcopy(base_clerk_payload_schema)
        expected = {
            AuthenticatedUserDTO._clerk_key_to_field.get(k, k): v
            for k, v in payload.items()
        }
        mock_result = MagicMock()
        mock_result.is_signed_in = True
        mock_result.payload = payload

        with patch("app.utils.auth.authenticate_request", return_value=mock_result):
            user = await get_current_user(
                request_from_context=fake_request(),
                auth_header=make_auth_header("valid-token"),
            )
            assert isinstance(user, AuthenticatedUserDTO)
            assert asdict(user) == expected


class TestGetCurrentUserEdgeCases:
    @pytest.mark.asyncio
    async def test_missing_auth_header_raises_401(self):
        with pytest.raises(UnauthorizedAccess) as exc:
            await get_current_user(fake_request(), None)
        assert exc.value.http_status == status.HTTP_401_UNAUTHORIZED
        assert INVALID_BEARER_TOKEN_SCHEMA in exc.value.user_message

    @pytest.mark.asyncio
    async def test_invalid_scheme_raises_401(self):
        bad_auth = make_auth_header(scheme="Basic")
        with pytest.raises(UnauthorizedAccess) as exc:
            await get_current_user(
                fake_request(
                    headers={
                        "Authorization": f"{bad_auth.scheme} {bad_auth.credentials}"
                    }
                ),
                bad_auth,
            )
        assert exc.value.http_status == status.HTTP_401_UNAUTHORIZED
        assert INVALID_BEARER_TOKEN_SCHEMA in exc.value.user_message

    @pytest.mark.asyncio
    async def test_clerk_signed_out_raises_auth_failed(self):
        mock_result = MagicMock()
        mock_result.is_signed_in = False
        mock_result.reason.name = AuthErrorReason.SESSION_TOKEN_MISSING.name
        mock_result.message = "No token"
        with patch("app.utils.auth.authenticate_request", return_value=mock_result):
            with pytest.raises(UnauthorizedAccess) as exc:
                await get_current_user(fake_request(), make_auth_header())
            assert exc.value.http_status == status.HTTP_401_UNAUTHORIZED
            assert (
                app.exceptions.exception_constants.AUTH_FAILED in exc.value.user_message
            )

    @pytest.mark.asyncio
    async def test_payload_missing_required_fields_raises(self):
        payload = {"sub": "user_abc", "email": "abc@example.com"}  # missing 'name'
        mock_result = MagicMock()
        mock_result.is_signed_in = True
        mock_result.payload = payload
        with patch("app.utils.auth.authenticate_request", return_value=mock_result):
            with pytest.raises(UnauthorizedAccess) as exc:
                await get_current_user(fake_request(), make_auth_header("valid-token"))
            assert exc.value.http_status == status.HTTP_401_UNAUTHORIZED
            assert INVALID_BEARER_TOKEN_SCHEMA in exc.value.user_message

    @pytest.mark.asyncio
    async def test_sdk_error_is_raised(self):
        with patch(
            "app.utils.auth.authenticate_request",
            side_effect=models.SDKError(
                status_code=500, message="Boom", raw_response=None, body="Error"
            ),
        ):
            with pytest.raises(models.SDKError):
                await get_current_user(fake_request(), make_auth_header())

    @pytest.mark.asyncio
    async def test_clerk_errors_is_raised(self):
        mock_error = models.ClerkError(
            message="Bad token",
            long_message="The token provided is invalid",
            code="invalid_token",
        )
        mock_data = models.ClerkErrorsData(errors=[mock_error])

        with patch(
            "app.utils.auth.authenticate_request",
            side_effect=models.ClerkErrors(mock_data),
        ):
            with pytest.raises(models.ClerkErrors) as exc_info:
                await get_current_user(fake_request(), make_auth_header())

            # Optional: Validate the exception contains your mocked message
            assert "Bad token" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_generic_exception_is_raised(self):
        with patch(
            "app.utils.auth.authenticate_request", side_effect=Exception("generic boom")
        ):
            with pytest.raises(Exception) as exc:
                await get_current_user(fake_request(), make_auth_header())
            assert "generic boom" in str(exc.value)

    @pytest.mark.asyncio
    async def test_signed_out_with_no_reason_or_message(self):
        """If Clerk returns signed_out with no reason or message, it should log and raise cleanly."""
        mock_result = MagicMock()
        mock_result.is_signed_in = False
        mock_result.reason = None
        mock_result.message = None

        with patch("app.utils.auth.authenticate_request", return_value=mock_result):
            with pytest.raises(UnauthorizedAccess) as exc:
                await get_current_user(fake_request(), make_auth_header())
            assert exc.value.http_status == 401
            assert (
                app.exceptions.exception_constants.AUTH_FAILED in exc.value.user_message
            )

# ===================================================================================
# TODO: This is the new easily testable, less complicated Auth system
# ===================================================================================

class TestGetAuthenticationUser:

    @pytest.mark.asyncio
    async def test_success(self):
        request = Request({"type": "http"})
        header = valid_bearer_token()

        user = await get_authenticated_user(request, header, authenticator=FakeSuccessAuthenticator())
        assert isinstance(user, UserClaims)
        assert user.sub == "user-123"

    @pytest.mark.parametrize("header", MalformedSchemeTokensStub.malformed_scheme_tokens())
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
            await get_authenticated_user(request, header, authenticator=FakeFailureAuthenticator())

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
    def __patch_clerk_authentication_result(monkeypatch, *, signed_in, payload=None, reason_name=None, message=None):
        reason = type("Reason", (), {"name": reason_name})() if reason_name else None
        result = FakeAuthResult(signed_in, payload=payload, reason=reason, message=message)
        monkeypatch.setattr("app.utils.auth.authenticate_request", lambda *_: result)

    @pytest.mark.asyncio
    async def test_successful_authentication(self, monkeypatch):
        fake_payload = {"sub": "user-1", "email": "a@b.com", "name": "Test"}
        self.__patch_clerk_authentication_result(monkeypatch, signed_in=True, payload=fake_payload)

        request = FakeRequest(headers={"authorization": "Bearer token"})
        user = await ClerkUserAuthenticator().authenticate(request)

        assert isinstance(user, UserClaims)
        assert user.sub == fake_payload["sub"]

    @pytest.mark.asyncio
    async def test_signed_out_with_reason(self, monkeypatch):
        self.__patch_clerk_authentication_result(monkeypatch, signed_in=False, reason_name="TOKEN_EXPIRED", message="Token expired")

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
