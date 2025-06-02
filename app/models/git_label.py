from tortoise.models import Model
from tortoise import fields
import uuid


class GitLabel(Model):
    """
    Git Label model for storing user's git hosting service credentials and labels
    """

    id = fields.UUIDField(primary_key=True, default=uuid.uuid4)
    user_id = fields.CharField(
        max_length=255, null=False, description="User identifier"
    )
    label = fields.TextField(
        null=False, description="Label/name for this git configuration"
    )
    git_hosting = fields.CharField(
        max_length=50,
        null=False,
        description="Git hosting service (e.g., 'github', 'gitlab')",
    )
    username = fields.TextField(
        null=False, description="Username for the git hosting service"
    )
    token_value = fields.TextField(
        null=False, description="Access token for the git hosting service"
    )
    
    masked_token = fields.TextField(
        null=False, description="Masked Access token for the git hosting service"
    )
    
    created_at = fields.DatetimeField(
        auto_now_add=True, description="Record creation timestamp"
    )
    updated_at = fields.DatetimeField(
        auto_now=True, description="Record last update timestamp"
    )

    class Meta:
        table = "git_label"
        table_description = (
            "Table for storing git hosting service configurations per user"
        )

    def __str__(self):
        return f"GitLabel(id={self.id}, user_id={self.user_id}, label={self.label}, git_hosting={self.git_hosting})"

    def __repr__(self):
        return self.__str__()