from clerk_backend_api import Clerk
from devdox.app import settings
import logging


def generate_clerk_token(user_id: str, expires_in_seconds: int | None = None) -> str:
    """
    Generate a Clerk JWT token for the given user ID.

    Args:
        user_id (str): The Clerk user ID.
        expires_in_seconds (int | None): Optional expiration time in seconds.

    Returns:
        str: The generated JWT token.

    Raises:
        Exception: If token generation fails.
    """
    try:
        with Clerk(bearer_auth=settings.CLERK_API_KEY) as clerk:
            session = clerk.sessions.create(request={"user_id": user_id})
            token = clerk.sessions.create_token(
                session_id=session.id, expires_in_seconds=expires_in_seconds
            )

            if not token or not token.jwt:
                raise ValueError("Token generation failed: No JWT returned.")

            return token.jwt

    except ValueError:

        logging.exception("Token generation failed: no JWT returned.")

        raise

    except (ConnectionError, TimeoutError) as e:

        logging.exception("Failed to generate Clerk token due to network error.")

        raise


if __name__ == "__main__":
    try:
        jwt_token = generate_clerk_token(settings.CLERK_USER_ID)
        print("Generated Clerk JWT token:", jwt_token)
    except Exception:
        print("Token generation failed.")
