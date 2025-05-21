from pydantic import BaseModel, Field
from typing import Optional
from app.config import GitHosting

class AddGitTokenSchema(BaseModel):
    """
    Base model for an example entity.
    """
    label: str = Field(
       ..., 
       description="Token label",
       min_length=1,
       max_length=50
   )
    git_hosting: GitHosting = Field(..., description="Git hosting provider")
    token_value: str = Field(
               ...,
               description = "Token value of git hosting",
           min_length = 5,
           max_length = 255,
                       )
    user_id: Optional[str] = Field(None, description="User ID")

