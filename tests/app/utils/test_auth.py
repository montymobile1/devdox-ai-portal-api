# --------------------------
# Tests: from_clerk_payload
# --------------------------
import copy
from dataclasses import asdict

import pytest
from clerk_backend_api.jwks_helpers import AuthErrorReason
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials
from starlette import status
from starlette.datastructures import Headers
from starlette.requests import Request

from app.utils.auth import AuthenticatedUserDTO, get_current_user
from app.utils.system_messages import INVALID_BEARER_TOKEN_SCHEMA

base_clerk_payload_schema = {
	"sub": "user_abc",
	"email": "abc@example.com",
	"name": "Abc"
}


def test_valid_payload_is_correctly_mapped_when_all_values_present():
	# Arrange
	payload = copy.deepcopy(base_clerk_payload_schema)
	expected_results_dict = {AuthenticatedUserDTO._clerk_key_to_field.get(k, k): v for k, v in payload.items()}
	
	# Act
	missing, dto = AuthenticatedUserDTO.from_clerk_payload(payload)
	dto_dict = asdict(dto)
	
	# Assert
	assert missing == []
	assert dto_dict == expected_results_dict


def test_valid_payload_is_correctly_mapped_when_key_values_are_none():
	# Arrange
	payload = copy.deepcopy(base_clerk_payload_schema)
	payload = dict.fromkeys(payload, None)
	
	expected_results_dict = {AuthenticatedUserDTO._clerk_key_to_field.get(k, k): v for k, v in payload.items()}
	
	# Act
	missing, dto = AuthenticatedUserDTO.from_clerk_payload(payload)
	dto_dict = asdict(dto)
	
	# Assert
	assert missing == []
	assert dto_dict == expected_results_dict


def test_invalid_payload_missing_required_fields():
	# Arrange
	payload = {}
	missing_values_set = set(key for key in base_clerk_payload_schema.keys())
	
	# Act
	missing, _ = AuthenticatedUserDTO.from_clerk_payload(payload)
	
	# Assert
	assert set(missing) == missing_values_set


# --------------------------
# Tests: get_current_user
# --------------------------

def fake_request(headers: dict = None, path="/fake") -> Request:
	scope = {
		"type": "http",
		"method": "GET",
		"path": path,
		"headers": Headers(headers or {}).raw,
	}
	return Request(scope)


def make_auth_header(token="fake-token", scheme="Bearer"):
	"""Simulate HTTPAuthorizationCredentials"""
	return HTTPAuthorizationCredentials(scheme=scheme, credentials=token)


def test_missing_auth_header_raises_401():
	with pytest.raises(HTTPException) as exc_info:
		get_current_user(
			request_from_context=fake_request(),
			auth_header=None
		)
	
	assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED
	assert INVALID_BEARER_TOKEN_SCHEMA in str(exc_info.value.detail)


def test_malformed_scheme_raises_401():
	with pytest.raises(HTTPException) as exc_info:
		
		generated_auth_header = make_auth_header(scheme="Basic")
		
		get_current_user(
			request_from_context=fake_request(headers={"Authorization": f"{generated_auth_header.scheme} {generated_auth_header.credentials}"}),
			auth_header=generated_auth_header
		)
	
	assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED
	assert INVALID_BEARER_TOKEN_SCHEMA in str(exc_info.value.detail)


def test_clerk_returns_signed_out(monkeypatch, mock_clerk_signed_out):
	mock_clerk_signed_out(AuthErrorReason.SESSION_TOKEN_MISSING)
	generated_auth_header = make_auth_header()
	
	
	with pytest.raises(HTTPException) as exc_info:
		get_current_user(
			request_from_context=fake_request(headers={"Authorization": f"{generated_auth_header.scheme} {generated_auth_header.credentials}"}, path="/git_tokens/"),
			auth_header=generated_auth_header
		)
	
	assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED
	assert exc_info.value.detail["error"] == "not_authenticated"


def test_payload_missing_required_keys_raises(monkeypatch, mock_clerk_signed_in):
	# Missing 'name' on purpose
	payload = {}
	
	mock_clerk_signed_in(payload, token="test-token")
	
	with pytest.raises(HTTPException) as exc_info:
		get_current_user(
			request_from_context=fake_request(path="/git_tokens/"),
			auth_header=make_auth_header("test-token")
		)
	
	assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED
	assert INVALID_BEARER_TOKEN_SCHEMA in str(exc_info.value.detail)


def test_successful_user_parsing(monkeypatch, mock_clerk_signed_in):
	payload = copy.deepcopy(base_clerk_payload_schema)
	expected_results_dict = {AuthenticatedUserDTO._clerk_key_to_field.get(k, k): v for k, v in payload.items()}
	
	mock_clerk_signed_in(payload, token="valid-token")
	
	user = get_current_user(
		request_from_context=fake_request(path="/git_tokens/"),
		auth_header=make_auth_header("valid-token")
	)
	
	assert isinstance(user, AuthenticatedUserDTO)
	assert asdict(user) == expected_results_dict
