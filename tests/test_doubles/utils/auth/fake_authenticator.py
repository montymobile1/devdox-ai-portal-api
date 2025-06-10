# to simulate `IUserAuthenticator` behavior
from clerk_backend_api import Requestish
from clerk_backend_api.jwks_helpers import AuthStatus

from app.exceptions.custom_exceptions import UnauthorizedAccess
from app.utils.auth import IUserAuthenticator, UserClaims


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
