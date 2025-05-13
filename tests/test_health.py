"""
Tests for the health check endpoint in the DevDox AI Portal API.
"""

import unittest
from fastapi.testclient import TestClient
from app.main import app

class TestHealthCheck(unittest.TestCase):
    """
    Test class for the health check endpoint.
    """
    
    def setUp(self):
        """
        Set up the test client.
        """
        self.client = TestClient(app)
    
    def test_health_check(self):
        """
        Test the health check endpoint.
        """
        response = self.client.get("/")
        
        # Check the response status code
        self.assertEqual(response.status_code, 200)
        
        # Check the response data
        data = response.json()
        self.assertEqual(data["status"], "healthy")
        self.assertEqual(data["message"], "DevDox AI Portal API is running!")

if __name__ == "__main__":
    unittest.main()
