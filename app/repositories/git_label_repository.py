from typing import Optional, Protocol

from app.models import GitLabel


class IGitLabelStore(Protocol):
    async def get_by_id_and_user(self, token_id: str, user_id: str) -> Optional[GitLabel]: ...

class TortoiseGitLabelStore(IGitLabelStore):
    async def get_by_id_and_user(self, token_id: str, user_id: str):
        return await GitLabel.filter(id=token_id, user_id=user_id).first()