from abc import abstractmethod
from enum import Enum
from typing import Any, Collection, Dict, List, Optional, Protocol, Union
from uuid import UUID

from models import GitLabel

from app.exceptions.custom_exceptions import DevDoxAPIException
from app.exceptions.exception_constants import (
    MISSING_LABEL_ID_TITLE,
    MISSING_LABEL_LOG_MESSAGE,
    MISSING_USER_ID_LOG_MESSAGE,
    MISSING_USER_ID_TITLE,
    SERVICE_UNAVAILABLE,
)
from app.schemas.git_label import GitLabelDBCreateDTO


class ILabelStore(Protocol):
    @abstractmethod
    async def get_git_hosting_map_by_token_id(self, token_ids: Collection[Union[str, UUID]])-> List[Dict]: ...
    
    @abstractmethod
    async def get_by_token_id_and_user(self, token_id: str, user_id: str) -> Any | None: ...
    
    @abstractmethod
    async def get_by_user_id(self, offset, limit, user_id, git_hosting: Optional[str] = None) -> list[Any]: ...
    
    @abstractmethod
    async def count_by_user_id(self, user_id, git_hosting: Optional[str] = None) -> int: ...
    
    @abstractmethod
    async def get_by_user_id_and_label(self, offset, limit, user_id, label: str) -> list[Any]: ...
    
    @abstractmethod
    async def create_new(self, label_model: GitLabelDBCreateDTO) -> Any: ...


def internal_error(log_message:str, error_type:str, **kwargs):
    return DevDoxAPIException(
                user_message=SERVICE_UNAVAILABLE,
                log_message=log_message,
                error_type=error_type,
                log_level="exception",
                **kwargs
            )

class TortoiseGitLabelStore(ILabelStore):

    class InternalExceptions(Enum):
        MISSING_USER_ID = {
            "error_type": MISSING_USER_ID_TITLE,
            "log_message": MISSING_USER_ID_LOG_MESSAGE
        }
        
        MISSING_LABEL = {
            "error_type": MISSING_LABEL_ID_TITLE,
            "log_message": MISSING_LABEL_LOG_MESSAGE
        }

    async def get_git_hosting_map_by_token_id(self, token_ids: Collection[Union[str, UUID]]) -> List[Dict]:
        if not token_ids:
            return []
        return await GitLabel.filter(id__in=token_ids).values("id", "git_hosting")

    async def get_by_token_id_and_user(self, token_id: str, user_id: str) -> GitLabel | None:
        if not token_id or not token_id.strip() or not user_id or not user_id.strip():
            return None

        return await GitLabel.filter(id=token_id, user_id=user_id).first()

    def __get_by_user_id_query(self, user_id, git_hosting: Optional[str] = None):
        if not user_id:
            raise internal_error(
                **self.InternalExceptions.MISSING_USER_ID.value
            )

        query = GitLabel.filter(user_id=user_id)

        if git_hosting:
            query = query.filter(git_hosting=git_hosting)

        return query

    async def get_by_user_id(self, offset, limit, user_id, git_hosting: Optional[str] = None) -> list[GitLabel]:
        query = self.__get_by_user_id_query(user_id, git_hosting)

        git_labels = (
            await query.order_by("-created_at")
            .offset(offset)
            .limit(limit)
            .all()
        )

        return git_labels

    async def count_by_user_id(self, user_id, git_hosting: Optional[str] = None) -> int:
        query = self.__get_by_user_id_query(user_id, git_hosting)

        return await query.count()

    async def get_by_user_id_and_label(self, offset, limit, user_id, label: str) -> list[GitLabel]:

        if not user_id:
            raise internal_error(**self.InternalExceptions.MISSING_USER_ID.value)
        
        if not label or not label.strip():
            raise internal_error(**self.InternalExceptions.MISSING_LABEL.value)
        
        query = GitLabel.filter(user_id=user_id, label=label)
        
        git_labels = (
            await query
            .order_by("-created_at")
            .offset(offset).limit(limit)
            .all()
        )
        
        return git_labels

    async def create_new(self, label_model: GitLabelDBCreateDTO) -> GitLabel:
        return await GitLabel.create(**label_model.model_dump())
