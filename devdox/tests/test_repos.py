"""
Updated test cases for repository API endpoints using Tortoise ORM.
Tests cover all CRUD operations and new functionality.
"""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest
from fastapi import status
from tortoise.exceptions import DoesNotExist

from app.config import GitHosting
from app.exceptions.exception_constants import SERVICE_UNAVAILABLE
from app.utils import constants


@pytest.fixture
def sample_github_repos():
    """Sample GitHub API response"""
    return {
        "repositories": [
            {
                "id": 123,
                "name": "test-repo",
                "description": "A test repository",
                "default_branch": "main",
                "forks_count": 5,
                "stargazers_count": 10,
                "private": False,
                "html_url": "https://github.com/user/test-repo",
            }
        ],
        "pagination_info": {"total_count": 1},
    }


@pytest.fixture
def mock_git_label():
    """Mock GitLabel model"""
    return Mock(
        id="token-123",
        user_id="user-1",
        token_value="encrypted_token",
        git_hosting=GitHosting.GITHUB,
    )


mock_git_label_class = MagicMock(
    name="GitLabel",
    spec=None,
)
