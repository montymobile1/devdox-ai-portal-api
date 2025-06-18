from app.models import User


class TortoiseUserStore:

    async def get_by_user_id(self, user_id: str) -> User | None:
        return await User.filter(user_id=user_id).first()
