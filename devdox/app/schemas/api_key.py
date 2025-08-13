import uuid
import datetime
from typing import Annotated, Optional

from fastapi.params import Depends, Path
from pydantic import BaseModel, Field

from app.schemas.basic import RequiredPaginationParams

API_KEY_FIELD_DESCRIPTION = "Hashed API key"
USER_ID_FIELD_DESCRIPTION = "User identifier (owner of the API key)"
MASKED_API_KEY_FIELD_DESCRIPTION = "Masked version of the API key"
IS_ACTIVE_FIELD_DESCRIPTION = "Whether this API key is active or soft deleted"
CREATED_AT_FIELD_DESCRIPTION = "The date and time the API Key was created"
LAST_USED_AT_FIELD_DESCRIPTION = "The date and time the API Key was last used"


class APIKeyCreate(BaseModel):
    user_id: str = Field(..., description=USER_ID_FIELD_DESCRIPTION)
    api_key: str = Field(..., description=API_KEY_FIELD_DESCRIPTION)
    masked_api_key: str = Field(..., description=MASKED_API_KEY_FIELD_DESCRIPTION)
    is_active: Optional[bool] = Field(
        default=True, description=IS_ACTIVE_FIELD_DESCRIPTION
    )

    class Config:
        title = "API Key Create Schema"
        description = "Used when creating a new API key. Includes the full hashed key along with base fields."
        from_attributes = True


class APIKeyRevokeRequest:
    def __init__(
        self,
        api_key_id: uuid.UUID = Path(
            description="The id of the API key to revoke retrieved from the database",
        ),
    ):
        self.api_key_id = api_key_id

class APIKeyGetAllRequest:
    def __init__(
        self,
        pagination: Annotated[RequiredPaginationParams, Depends()],
    ):
        self.pagination = pagination

class APIKeyPublicResponse(BaseModel):
    user_id: str = Field(..., description=USER_ID_FIELD_DESCRIPTION)
    masked_api_key: str = Field(..., description=MASKED_API_KEY_FIELD_DESCRIPTION)
    created_at: datetime.datetime = Field(..., description=CREATED_AT_FIELD_DESCRIPTION)
    last_used_at: Optional[datetime.datetime] = Field(
        default=None, description=LAST_USED_AT_FIELD_DESCRIPTION
    )

    class Config:
        title = "API Key Public Schema"
        description = "Used when returning API Key records to the user"
        from_attributes = True
