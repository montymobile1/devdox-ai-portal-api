from tortoise.models import Model
from tortoise import fields


class User(Model):
    """
    User model for storing user information from clerk
    """

    id = fields.IntField(pk=True, description="Primary key")
    user_id = fields.CharField(max_length=255, description="User ID")

    first_name = fields.CharField(max_length=255, description="First name of user")
    last_name = fields.CharField(max_length=255, description="Last name of user")
    email = fields.CharField(max_length=255, description="Email of user")
    username = fields.CharField(max_length=255, description="Username of user")
    role = fields.CharField(max_length=255, description="Last name of user")
    active = fields.BooleanField(default=True)

    memembrship_level = fields.CharField(
        max_length=100, default="main", description="Default branch name"
    )
    token_limit = fields.IntField(
        default=0, description="Number of token of each month"
    )
    token_used = fields.IntField(default=0, description="Number of tokens used")

    # Timestamps
    created_at = fields.DatetimeField(
        auto_now_add=True, description="Record creation timestamp"
    )

    class Meta:
        table = "user"
        table_description = "User information from Clerk"
        indexes = [
            ("user_id", "created_at"),
        ]

    def __str__(self):
        return f"{self.name} ({self.email})"
