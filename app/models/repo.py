from tortoise.models import Model
from tortoise import fields
import uuid


class Repo(Model):
    """
    Repository model for storing repository information from various Git providers
    """

    id = fields.UUIDField(primary_key=True, default=uuid.uuid4)
    user_id = fields.CharField(
        unique=True, max_length=255, description="User ID who owns this repository"
    )

    # Repository basic information
    repo_id = fields.CharField(
        max_length=255, description="Repository ID from the Git provider"
    )
    name = fields.CharField(max_length=255, description="Repository name")
    description = fields.TextField(null=True, description="Repository description")
    html_url = fields.CharField(max_length=500, description="Repository URL")

    # Repository metadata
    default_branch = fields.CharField(
        max_length=100, default="main", description="Default branch name"
    )
    forks_count = fields.IntField(default=0, description="Number of forks")
    stargazers_count = fields.IntField(default=0, description="Number of stars")

    # Visibility/Privacy settings
    is_private = fields.BooleanField(
        default=False, description="Whether repository is private"
    )
    visibility = fields.CharField(
        max_length=50, null=True, description="Repository visibility (GitLab)"
    )

    # Git provider information
    git_hosting = fields.CharField(
        max_length=50, description="Git hosting provider (github/gitlab)"
    )
    token_id = fields.CharField(
        max_length=255, null=True, description="Associated token ID"
    )

    # Timestamps
    created_at = fields.DatetimeField(
        auto_now_add=True, description="Record creation timestamp"
    )
    updated_at = fields.DatetimeField(
        auto_now=True, description="Record update timestamp"
    )

    # Repository timestamps from provider
    repo_created_at = fields.DatetimeField(
        null=True, description="Repository creation date from provider"
    )
    repo_updated_at = fields.DatetimeField(
        null=True, description="Repository last update from provider"
    )

    # Additional metadata
    language = fields.CharField(
        max_length=100, null=True, description="Primary programming language"
    )
    size = fields.IntField(null=True, description="Repository size in KB")

    class Meta:
        table = "repo"
        table_description = "Repository information from Git providers"
        indexes = [
            ("user_id", "created_at"),
            ("user_id", "git_hosting"),
            ("repo_id", "git_hosting"),
        ]

    def __str__(self):
        return f"{self.name} ({self.git_hosting})"
