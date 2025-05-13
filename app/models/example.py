"""
Example models for the DevDox AI Portal API.
"""

from pydantic import BaseModel, Field
from typing import Optional

class ExampleBase(BaseModel):
    """
    Base model for an example entity.
    """
    name: str = Field(..., description="Name of the example")
    description: Optional[str] = Field(None, description="Description of the example")

class ExampleCreate(ExampleBase):
    """
    Model for creating a new example entity.
    """
    pass

class ExampleUpdate(BaseModel):
    """
    Model for updating an example entity.
    """
    name: Optional[str] = Field(None, description="Name of the example")
    description: Optional[str] = Field(None, description="Description of the example")

class ExampleInDB(ExampleBase):
    """
    Model for an example entity as stored in the database.
    """
    id: int = Field(..., description="Unique identifier for the example")
    
    class Config:
        """
        Pydantic config class.
        """
        orm_mode = True

class Example(ExampleInDB):
    """
    Model for an example entity returned to clients.
    """
    pass
