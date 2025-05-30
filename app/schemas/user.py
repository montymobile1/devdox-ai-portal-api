from pydantic import BaseModel, field_validator, computed_field, ConfigDict
from typing import Dict, Optional, Any, List


class ClerkEmailAddress(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
        extra="ignore",
    )

    email_address: str
    primary: bool = False


class WebhookUserData(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    first_name: Optional[str] = ""
    last_name: Optional[str] = ""
    username: Optional[str] = ""
    email_addresses: List[ClerkEmailAddress] = []

    @field_validator("username", mode="before")
    @classmethod
    def clean_username(cls, v):
        result = v if v is not None else ""
        return result

    @field_validator("first_name", mode="before")
    @classmethod
    def clean_first_name(cls, v):
        return v if v is not None else ""

    @field_validator("last_name", mode="before")
    @classmethod
    def clean_last_name(cls, v):
        return v if v is not None else ""

    @computed_field
    @property
    def primary_email(self) -> Optional[str]:
        """Get the primary email address."""
        for email in self.email_addresses:
            if email.primary:
                return email.email_address

        # If no primary email, return the first one
        if self.email_addresses:
            return self.email_addresses[0].email_address

        return None
