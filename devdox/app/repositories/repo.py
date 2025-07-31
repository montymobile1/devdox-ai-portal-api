from abc import abstractmethod
from typing import Any, List, Protocol
from enum import Enum
from tortoise.exceptions import DoesNotExist

from app.exceptions.base_exceptions import DevDoxAPIException
from app.exceptions.exception_constants import (
    REPOSITORY_DOESNT_EXIST_TITLE,
    SERVICE_UNAVAILABLE,
)
from models import Repo


def internal_error(log_message: str, error_type: str, **kwargs):
    return DevDoxAPIException(
        user_message=SERVICE_UNAVAILABLE,
        log_message=log_message,
        error_type=error_type,
        log_level="exception",
        **kwargs
    )


class IRepoStore(Protocol):
    @abstractmethod
    async def get_all_by_user(
        self, user_id: str, offset: int, limit: int
    ) -> List[Any]: ...

    @abstractmethod
    async def count_by_user(self, user_id: str) -> int: ...

    @abstractmethod
    async def create_new_repo(self, repo_model: Any) -> Any: ...


class TortoiseRepoStore(IRepoStore):

    def __init__(self):
        """
        Have to add this as an empty __init__ to override it, because when using it with Depends(),
        FastAPI dependency mechanism will automatically assume its
        ```
        def __init__(self, *args, **kwargs):
            pass
        ```
        Causing unneeded behavior.
        """
        pass

    class InternalExceptions(Enum):
        REPOSITORY_DOESNT_EXIST = {
            "error_type": REPOSITORY_DOESNT_EXIST_TITLE,
            "log_message": REPOSITORY_DOESNT_EXIST_TITLE,
        }

    async def get_all_by_user(
        self, user_id: str, offset: int, limit: int
    ) -> List[Repo]:
        return (
            await Repo.filter(user_id=user_id)
            .order_by("-created_at")
            .offset(offset * limit)
            .limit(limit)
            .all()
        )

    async def count_by_user(self, user_id: str) -> int:
        return await Repo.filter(user_id=user_id).count()

    async def create_new_repo(self, repo_model: Repo) -> Repo:
        await repo_model.save(force_create=True)
        await repo_model.refresh_from_db()
        return repo_model

    async def get_by_id(self, repo_id: str) -> Repo:
        try:
            return await Repo.get(id=repo_id)
        except DoesNotExist as e:
            raise internal_error(
                **self.InternalExceptions.REPOSITORY_DOESNT_EXIST.value
            ) from e
