from typing import Optional

from pydantic import BaseModel, Field


class PaginationParams(BaseModel):
    limit: Optional[int] = Field(
        20, ge=1, description="Limit must be greater than zero"
    )
    offset: Optional[int] = Field(0, ge=0, description="Offset must be zero or greater")
