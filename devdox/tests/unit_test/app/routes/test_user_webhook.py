import json
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from encryption_src.test_doubles import FakeEncryptionHelper
from fastapi import status
from models_src import GenericFakeStore, InMemoryUserBackend, UserResponseDTO, UserStore
from svix.webhooks import Webhook, WebhookVerificationError

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
    @patch("app.routes.webhooks.get_active_user_store")
    async def test_user_created_success(
        self,
        mock_user,
        mock_webhook_class,
        mock_get_encryption,
        client,
        test_payload,
        test_headers,
    ):
        
        
        in_memo = InMemoryUserBackend()
        fake_user_store = GenericFakeStore(base_store=UserStore(storage_backend=in_memo))
        
        mock_user.return_value = fake_user_store
        
        raw_payload = json.dumps(test_payload).encode("utf-8")

        # Setup webhook.verify to return the full dict
        mock_webhook_instance = MagicMock()
        mock_webhook_instance.verify.return_value = test_payload
        mock_webhook_class.return_value = mock_webhook_instance
        
        # Fire request
        response = client.post(
            "/api/v1/webhooks/",
            data=raw_payload,
            headers=test_headers,
        )

        # Assertions
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["message"] == constants.USER_CREATED_SUCCESS


    @pytest.mark.asyncio
    @patch("app.routes.webhooks.Webhook")
    @patch("app.routes.webhooks.get_active_user_store")
    async def test_user_already_exists(
        self,
        mock_store,
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
        
        in_memo = InMemoryUserBackend()
        
        
        in_memo.set_fake_data(
            [
                UserResponseDTO(
                    id=uuid.uuid4(),
                    user_id=test_payload["data"]["id"],
                    first_name=test_payload["data"]["first_name"],
                    last_name=test_payload["data"]["last_name"],
                    email=test_payload["data"]["primary_email_address_id"],
                    username=test_payload["data"]["username"]
                )
            ]
        )
        
        fake_user_store = GenericFakeStore(base_store=UserStore(storage_backend=in_memo))

        
        mock_store.return_value = fake_user_store
        
        response = client.post(
            "/api/v1/webhooks/", json=test_payload, headers=test_headers
        )

        assert response.status_code == status.HTTP_200_OK
        assert UserStore.save.__name__ not in [x[0] for x in fake_user_store.received_calls]

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
    @patch("app.routes.webhooks.get_active_user_store")
    async def test_unexpected_error(
        self, mock_store, mock_verify, client, test_payload, test_headers
    ):
        mock_verify.return_value = test_payload
        
        in_memo = InMemoryUserBackend()
        fake_user_store = GenericFakeStore(base_store=UserStore(storage_backend=in_memo))
        fake_user_store.set_exception(UserStore.exists_by_user_id, Exception("DB error"))
        mock_store.return_value = fake_user_store
        
        response = client.post(
            "/api/v1/webhooks/", json=test_payload, headers=test_headers
        )

        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert (
            response.json()["message"]
            == app.exceptions.exception_constants.SERVICE_UNAVAILABLE
        )
