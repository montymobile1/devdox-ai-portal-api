"""
Tests for the authentication routes in the DevDox AI Portal API.
"""

import unittest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from app.main import app

class TestAuthRoutes(unittest.TestCase):
    """
    Test class for the authentication routes.
    """
    
    def setUp(self):
        """
        Set up the test client.
        """
        self.client = TestClient(app)
    
    @patch('app.utils.auth.get_current_user')
    def test_get_current_user_profile(self, mock_get_current_user):
        """
        Test getting the current user's profile.
        """
        # Mock the current user
        mock_get_current_user.return_value = {
            "id": "user-123",
            "email": "test@example.com",
            "name": "Test User"
        }
        
        # Call the API
        response = self.client.get("/api/v1/auth/me")
        
        # Check the response status code
        self.assertEqual(response.status_code, 200)
        
        # Check the response data
        data = response.json()
        self.assertEqual(data["id"], "user-123")
        self.assertEqual(data["email"], "test@example.com")
        self.assertEqual(data["name"], "Test User")
        self.assertTrue(data["profile"]["isAuthenticated"])
        self.assertEqual(data["profile"]["role"], "user")
    
    @patch('app.utils.auth.get_current_user')
    def test_get_user_repositories(self, mock_get_current_user):
        """
        Test getting the user's repositories.
        """
        # Mock the current user
        mock_get_current_user.return_value = {
            "id": "user-123",
            "email": "test@example.com",
            "name": "Test User"
        }
        
        # Call the API
        response = self.client.get("/api/v1/auth/repositories")
        
        # Check the response status code
        self.assertEqual(response.status_code, 200)
        
        # Check the response data
        data = response.json()
        self.assertIn("repositories", data)
        self.assertEqual(len(data["repositories"]), 2)
        
        # Check the first repository
        repo_1 = data["repositories"][0]
        self.assertEqual(repo_1["id"], 1)
        self.assertEqual(repo_1["name"], "repo1")
        self.assertEqual(repo_1["url"], "https://github.com/user/repo1")
        
        # Check the second repository
        repo_2 = data["repositories"][1]
        self.assertEqual(repo_2["id"], 2)
        self.assertEqual(repo_2["name"], "repo2")
        self.assertEqual(repo_2["url"], "https://github.com/user/repo2")
    
    def test_get_current_user_profile_unauthorized(self):
        """
        Test getting the current user's profile without authentication.
        """
        # Call the API without authentication
        response = self.client.get("/api/v1/auth/me")
        
        # Check the response status code
        self.assertEqual(response.status_code, 401)
    
    def test_get_user_repositories_unauthorized(self):
        """
        Test getting the user's repositories without authentication.
        """
        # Call the API without authentication
        response = self.client.get("/api/v1/auth/repositories")
        
        # Check the response status code
        self.assertEqual(response.status_code, 401)

if __name__ == "__main__":
    unittest.main()
