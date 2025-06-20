from models import User


class TortoiseUserStore:

    async def get_by_user_id(self, user_id: str) -> User | None:
        if not user_id or not user_id.strip():
            return None

        return await User.filter(user_id=user_id).first()
