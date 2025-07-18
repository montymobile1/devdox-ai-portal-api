import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from encryption_src.test_doubles import FakeEncryptionHelper
from fastapi import status
from svix.webhooks import WebhookVerificationError

import app.exceptions.exception_constants
from app.utils import constants


class TestWebhookEndpoint:
    @pytest.fixture
    def test_headers(self):
        return {
            "svix-id": "msg_id",
            "svix-timestamp": "timestamp",
            "svix-signature": "valid_signature",
        }

    @pytest.fixture
    def test_payload(self):
        return {
            "type": "user.created",
            "data": {
                "id": "user_123",
                "first_name": "John",
                "last_name": "Doe",
                "email_addresses": [
                    {"email_address": "john@example.com"},
                ],
                "primary_email_address_id": "john@example.com",
                "username": "johndoe",
            },
        }

    @pytest.mark.asyncio
    @patch("app.routes.webhooks.get_encryption_helper", return_value=FakeEncryptionHelper())
    @patch("app.routes.webhooks.Webhook")
    @patch("app.routes.webhooks.User")
    async def test_user_created_success(
        self,
        mock_user,
        mock_webhook_class,
        mock_get_encryption,
        client,
        test_payload,
        test_headers,
    ):
        raw_payload = json.dumps(test_payload).encode("utf-8")

        # Setup webhook.verify to return the full dict
        mock_webhook_instance = MagicMock()
        mock_webhook_instance.verify.return_value = test_payload
        mock_webhook_class.return_value = mock_webhook_instance

        # Setup User.filter().exists() → False
        mock_user.filter.return_value.exists = AsyncMock(return_value=False)
        # Setup User.create()
        mock_user.create = AsyncMock()

        # Fire request
        response = client.post(
            "/api/v1/webhooks/",
            data=raw_payload,
            headers=test_headers,
        )

        # Assertions
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["message"] == constants.USER_CREATED_SUCCESS

        mock_user.filter.assert_called_once_with(user_id="user_123")
        mock_user.create.assert_called_once()

    @pytest.mark.asyncio
    @patch("app.routes.webhooks.Webhook")
    @patch("app.routes.webhooks.User.filter")
    @patch("app.routes.webhooks.User.create")
    async def test_user_already_exists(
        self,
        mock_create,
        mock_filter,
        mock_webhook_class,
        client,
        test_payload,
        test_headers,
    ):
        mock_webhook_instance = MagicMock()
        mock_webhook_instance.verify.return_value = test_payload
        mock_webhook_class.return_value = (
            mock_webhook_instance  # Return mock instance on init
        )
        mock_filter.return_value.exists = AsyncMock(return_value=True)
        response = client.post(
            "/api/v1/webhooks/", json=test_payload, headers=test_headers
        )

        assert response.status_code == status.HTTP_200_OK
        mock_create.assert_not_called()

    @pytest.mark.asyncio
    @patch("app.routes.webhooks.Webhook")
    async def test_invalid_webhook_signature(
        self, mock_webhook_class, client, test_payload, test_headers
    ):
        mock_webhook_instance = MagicMock()

        mock_webhook_instance.verify.side_effect = WebhookVerificationError(
            "Invalid signature"
        )

        mock_webhook_class.return_value = (
            mock_webhook_instance  # Return mock instance on init
        )

        response = client.post(
            "/api/v1/webhooks/", json=test_payload, headers=test_headers
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.json()["message"] == constants.INVALID_WEBHOOK_SIGNATURE

    @pytest.mark.asyncio
    @patch("app.routes.webhooks.Webhook.verify")
    @patch("app.routes.webhooks.User.filter")
    async def test_unexpected_error(
        self, mock_filter, mock_verify, client, test_payload, test_headers
    ):
        mock_verify.return_value = test_payload
        mock_filter.side_effect = Exception("DB error")
        response = client.post(
            "/api/v1/webhooks/", json=test_payload, headers=test_headers
        )

        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert (
            response.json()["message"]
            == app.exceptions.exception_constants.SERVICE_UNAVAILABLE
        )
