from typing import Collection, Dict, List

from app.models import GitLabel


class TortoiseGitLabelStore:
    async def get_git_hosting_map_by_token_id(self, token_ids: Collection[str]) -> List[Dict]:
        return await GitLabel.filter(id__in=token_ids).values("id", "git_hosting")
