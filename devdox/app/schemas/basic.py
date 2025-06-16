from pydantic import BaseModel
from typing import Optional


class PaginationParams(BaseModel):
    limit: Optional[int] = 20
    offset: Optional[int] = 0
