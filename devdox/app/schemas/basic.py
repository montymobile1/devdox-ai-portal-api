from pydantic import BaseModel, Field
from typing import Optional


class PaginationParams(BaseModel):
    limit: Optional[int] = Field(
        20, ge=1, description="Limit must be greater than zero"
    )
    offset: Optional[int] = Field(0, ge=0, description="Offset must be zero or greater")

class RequiredPaginationParams(BaseModel):
    limit: int = Field(
        20, ge=1, description="Limit is required and must be greater than zero"
    )
    offset: int = Field(0, ge=0, description="Offset is required and must be zero or greater")