import uuid

from models import User

from app.repositories.user import IUserStore


class FakeUserStore(IUserStore):
    def __init__(self):
        self.users = {}
        self.exceptions = {}

    def set_fake_user(self, user, user_id: str = "user123"):
        if user is None:
            # Explicitly simulate "not found" by omitting the key
            self.users.pop(user_id, None)
        else:
            self.users[user.user_id] = user

    def set_exception(self, method_name: str, exception: Exception):
        self.exceptions[method_name] = exception

    async def get_by_user_id(self, user_id: str):
        if "get_by_user_id" in self.exceptions:
            raise self.exceptions["get_by_user_id"]
        return self.users.get(user_id)


def make_fake_user(user_id="user123", email="test@example.com", encryption_salt="xyz"):
    return User(
        id=uuid.UUID("dd0551f4-2164-4739-bf3f-9ccd1644ca75"),
        user_id=user_id,
        email=email,
        encryption_salt=encryption_salt,
    )
