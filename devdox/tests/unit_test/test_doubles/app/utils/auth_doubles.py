from app.exceptions.custom_exceptions import UnauthorizedAccess
from app.utils.auth import IUserAuthenticator, UserClaims


class FakeUserAuthenticator(IUserAuthenticator):
    def __init__(self, user: UserClaims = None, raise_unauthorized=False):
        self.user = user or UserClaims(
            sub="fake-user", email="fake@example.com", name="Fake User"
        )
        self.raise_unauthorized = raise_unauthorized
        self.received_calls = []

    async def authenticate(self, request):
        self.received_calls.append(("authenticate", request))
        if self.raise_unauthorized:
            raise UnauthorizedAccess("Simulated unauthorized access")
        return self.user


def override_authenticator_with_fake(user: UserClaims = None, raise_error=False):
    """
    example:
        ```
            app.dependency_overrides[get_user_authenticator_dependency] = override_authenticator_with_fake()
        ```
        or simulate unauthorized access:
        ```
            app.dependency_overrides[get_user_authenticator_dependency] = override_authenticator_with_fake(raise_error=True)
        ```
    """

    def _override():
        return FakeUserAuthenticator(user=user, raise_unauthorized=raise_error)

    return _override
