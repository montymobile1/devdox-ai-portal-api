import uuid

from tortoise import fields, Model


class APIKEY(Model):
    """
    Git Label model for storing user's git hosting service credentials and labels
    """

    id = fields.UUIDField(primary_key=True, default=uuid.uuid4)
    user_id = fields.CharField(
        max_length=255, null=False, description="User identifier"
    )
    api_key = fields.CharField(
        required=True,
        max_length=255,
        description="API Key for the context service",
        null=False,
    )
    masked_api_key = fields.CharField(
        required=True,
        max_length=255,
        description="API Key masked",
        null=False,
    )

    is_active = fields.BooleanField(default=True)
    created_at = fields.DatetimeField(
        auto_now_add=True, description="Record creation timestamp"
    )
    updated_at = fields.DatetimeField(
        auto_now=True, description="Record last update timestamp"
    )
    last_used_at = fields.DatetimeField()

    class Meta:
        table = "api_key"
        table_description = "Table for storing api key per user"

    def __str__(self):
        return (
            f"APIKEY(id={self.id}, user_id={self.user_id}, "
            f"masked_api_key={self.masked_api_key})"
        )

    def __repr__(self):
        return self.__str__()
