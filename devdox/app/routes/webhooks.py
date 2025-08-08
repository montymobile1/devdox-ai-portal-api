import base64
import logging
import os

from fastapi import APIRouter, Request, Response, status
from svix.webhooks import Webhook, WebhookVerificationError

import app.exceptions.exception_constants
from app.config import settings
from models_src.models import User
from app.schemas.user import WebhookUserData
from app.utils import constants
from app.utils.api_response import APIResponse

from app.utils.encryption import (
    FernetEncryptionHelper,
    get_encryption_helper,
)


router = APIRouter()

logger = logging.getLogger(__name__)


@router.post("/", status_code=status.HTTP_200_OK, include_in_schema=False)
async def webhook_handler(request: Request, response: Response):
    """
    Handle Clerk webhook events for user management.

    Currently supports:
    - user.created: Creates a new user in the database
    """
    headers = request.headers
    payload = await request.body()

    try:
        # Verify webhook signature
        wh = Webhook(settings.CLERK_WEBHOOK_SECRET)
        msg = wh.verify(payload, headers)
        
        encryptor:FernetEncryptionHelper = get_encryption_helper()
        
        event_type = msg.get("type")
        data = msg.get("data", {})
        logger.info(f"Processing webhook event: {event_type}")

        if event_type == "user.created":
            res = await _handle_user_created(encryptor, data)
            if not res:
                APIResponse.success(message=constants.USER_EXIST)
        else:
            logger.info(f"Unhandled webhook event type: {event_type}")

        return APIResponse.success(message=constants.USER_CREATED_SUCCESS)

    except WebhookVerificationError as e:
        logger.error(f"Webhook verification failed: {str(e)}")
        return APIResponse.error(
            status_code=status.HTTP_400_BAD_REQUEST,
            message=constants.INVALID_WEBHOOK_SIGNATURE,
        )

    except Exception as e:
        logger.error(f"Unexpected error processing webhook: {str(e)}")
        return APIResponse.error(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            message=app.exceptions.exception_constants.SERVICE_UNAVAILABLE,
        )


async def _handle_user_created(encryptor:FernetEncryptionHelper, data: dict) -> None:
    """Handle user.created webhook event."""
    try:
        # Validate and clean the webhook data using Pydantic
        user_data = WebhookUserData(**(data))

        # Check if user already exists
        existing_user = await User.filter(user_id=user_data.id).exists()
        logger.info(f"User exists check for {user_data.id}: {existing_user}")

        if existing_user:
            logger.info(f"User {user_data.id} already exists, skipping creation")
            return

        salt_bytes = os.urandom(32)  # 32 bytes for extra security
        salt_b64 = base64.urlsafe_b64encode(salt_bytes).decode()

        # Create user using the validated Pydantic model data
        await User.create(
            user_id=user_data.id,
            first_name=user_data.first_name,
            last_name=user_data.last_name,
            email=user_data.primary_email,
            username=user_data.username,  # This is now cleaned by Pydantic
            encryption_salt=encryptor.encrypt(salt_b64),
            role="user",
            active=True,
        )
        logger.info(f"Successfully created user: {user_data.id}")

    except Exception as e:
        logger.error(f"Failed to create user: {str(e)}")
        raise
