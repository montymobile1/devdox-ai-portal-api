from typing import Any, Collection, Coroutine, Dict, List, Union
from uuid import UUID

from app.models import GitLabel


class TortoiseGitLabelStore:
    async def get_git_hosting_map_by_token_id(
        self, token_ids: Collection[Union[str, UUID]]
    ) -> List[Dict]:
        if not token_ids:
            return []
        return await GitLabel.filter(id__in=token_ids).values("id", "git_hosting")
    
    async def get_by_token_id_and_user(self, token_id: str, user_id: str) -> GitLabel | None:
        if not token_id or not user_id or not token_id.replace(" ", "") or not token_id.replace(" ", ""):
            return None
        
        return await GitLabel.filter(id=token_id, user_id=user_id).first()