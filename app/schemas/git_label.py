from pydantic import BaseModel, Field
from typing import Optional
from app.config import GitHosting

class AddGitlabSchema(BaseModel):
    """
    Base model for an example entity.
    """
    label: str = Field(..., description="Token label")
    git_hosting: Optional[GitHosting] = Field(None, description="Git hosting provider")
    token_value: Optional[str] = Field(None, description="Token value of git hosting")
    user_id: Optional[str] = Field(None, description="User ID")

