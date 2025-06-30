from typing import Optional

from pydantic import BaseModel, Field

API_KEY_FIELD_DESCRIPTION = "Hashed API key"
USER_ID_FIELD_DESCRIPTION = "User identifier (owner of the API key)"
MASKED_API_KEY_FIELD_DESCRIPTION = "Masked version of the API key"
IS_ACTIVE_FIELD_DESCRIPTION = "Whether this API key is active or soft deleted"

class APIKeyCreate(BaseModel):
    user_id: str = Field(..., description=USER_ID_FIELD_DESCRIPTION)
    api_key: str = Field(..., description=API_KEY_FIELD_DESCRIPTION)
    masked_api_key: str = Field(..., description=MASKED_API_KEY_FIELD_DESCRIPTION)
    is_active: Optional[bool] = Field(default=True, description=IS_ACTIVE_FIELD_DESCRIPTION)

    class Config:
        title = "API Key Create Schema"
        description = "Used when creating a new API key. Includes the full hashed key along with base fields."
        from_attributes = True