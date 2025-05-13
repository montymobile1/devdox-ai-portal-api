"""
Tests for the authentication utilities in the DevDox AI Portal API.
"""

import unittest
from unittest.mock import patch, MagicMock
from fastapi import HTTPException
from app.utils.auth import get_clerk_jwt_from_headers, decode_clerk_jwt, get_current_user

class TestAuth(unittest.TestCase):
    """
    Test class for authentication utilities.
    """
    
    def test_get_clerk_jwt_from_headers_with_token(self):
        """
        Test extracting JWT token from headers when present.
        """
        # Create a mock request with Authorization header
        mock_request = MagicMock()
        mock_request.headers = {"Authorization": "Bearer test-token"}
        
        # Call the function
        token = get_clerk_jwt_from_headers(mock_request)
        
        # Check the result
        self.assertEqual(token, "test-token")
    
    def test_get_clerk_jwt_from_headers_without_token(self):
        """
        Test extracting JWT token from headers when not present.
        """
        # Create a mock request without Authorization header
        mock_request = MagicMock()
        mock_request.headers = {}
        
        # Call the function
        token = get_clerk_jwt_from_headers(mock_request)
        
        # Check the result
        self.assertIsNone(token)
    
    def test_get_clerk_jwt_from_headers_invalid_format(self):
        """
        Test extracting JWT token from headers with invalid format.
        """
        # Create a mock request with invalid Authorization header
        mock_request = MagicMock()
        mock_request.headers = {"Authorization": "Invalid test-token"}
        
        # Call the function
        token = get_clerk_jwt_from_headers(mock_request)
        
        # Check the result
        self.assertIsNone(token)
    
    @patch('app.utils.auth.jwt.decode')
    def test_decode_clerk_jwt_valid(self, mock_decode):
        """
        Test decoding a valid JWT token.
        """
        # Mock the jwt.decode function
        mock_decode.return_value = {
            "sub": "user-123",
            "email": "test@example.com",
            "name": "Test User"
        }
        
        # Call the function
        payload = decode_clerk_jwt("test-token")
        
        # Check the result
        self.assertEqual(payload["sub"], "user-123")
        self.assertEqual(payload["email"], "test@example.com")
        self.assertEqual(payload["name"], "Test User")
    
    @patch('app.utils.auth.jwt.decode')
    def test_decode_clerk_jwt_invalid(self, mock_decode):
        """
        Test decoding an invalid JWT token.
        """
        # Mock the jwt.decode function to raise an exception
        from jwt import PyJWTError
        mock_decode.side_effect = PyJWTError("Invalid token")
        
        # Call the function and expect an exception
        with self.assertRaises(HTTPException) as context:
            decode_clerk_jwt("invalid-token")
        
        # Check the exception
        self.assertEqual(context.exception.status_code, 401)
        self.assertIn("Invalid authentication token", context.exception.detail)
    
    @patch('app.utils.auth.get_clerk_jwt_from_headers')
    @patch('app.utils.auth.decode_clerk_jwt')
    def test_get_current_user_valid(self, mock_decode_jwt, mock_get_jwt):
        """
        Test getting current user with valid token.
        """
        # Mock the functions
        mock_get_jwt.return_value = "test-token"
        mock_decode_jwt.return_value = {
            "sub": "user-123",
            "email": "test@example.com",
            "name": "Test User"
        }
        
        # Create a mock request
        mock_request = MagicMock()
        
        # Call the function
        user = get_current_user(mock_request)
        
        # Check the result
        self.assertEqual(user["id"], "user-123")
        self.assertEqual(user["email"], "test@example.com")
        self.assertEqual(user["name"], "Test User")
    
    @patch('app.utils.auth.get_clerk_jwt_from_headers')
    def test_get_current_user_no_token(self, mock_get_jwt):
        """
        Test getting current user with no token.
        """
        # Mock the function to return None
        mock_get_jwt.return_value = None
        
        # Create a mock request
        mock_request = MagicMock()
        
        # Call the function and expect an exception
        with self.assertRaises(HTTPException) as context:
            get_current_user(mock_request)
        
        # Check the exception
        self.assertEqual(context.exception.status_code, 401)
        self.assertEqual(context.exception.detail, "Missing authentication token")
    
    @patch('app.utils.auth.get_clerk_jwt_from_headers')
    @patch('app.utils.auth.decode_clerk_jwt')
    def test_get_current_user_no_sub(self, mock_decode_jwt, mock_get_jwt):
        """
        Test getting current user with token missing subject.
        """
        # Mock the functions
        mock_get_jwt.return_value = "test-token"
        mock_decode_jwt.return_value = {
            "email": "test@example.com",
            "name": "Test User"
            # Missing "sub" field
        }
        
        # Create a mock request
        mock_request = MagicMock()
        
        # Call the function and expect an exception
        with self.assertRaises(HTTPException) as context:
            get_current_user(mock_request)
        
        # Check the exception
        self.assertEqual(context.exception.status_code, 401)
        self.assertEqual(context.exception.detail, "Invalid authentication token: Missing user ID")

if __name__ == "__main__":
    unittest.main()
