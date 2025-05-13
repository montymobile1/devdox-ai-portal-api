"""
Tests for the example routes in the DevDox AI Portal API.
"""

import unittest
from fastapi.testclient import TestClient
from app.main import app

class TestExampleRoutes(unittest.TestCase):
    """
    Test class for the example routes.
    """
    
    def setUp(self):
        """
        Set up the test client.
        """
        self.client = TestClient(app)
    
    def test_get_examples(self):
        """
        Test getting a list of examples.
        """
        response = self.client.get("/api/v1/examples/")
        
        # Check the response status code
        self.assertEqual(response.status_code, 200)
        
        # Check the response data
        data = response.json()
        self.assertIsInstance(data, list)
        self.assertEqual(len(data), 2)
        
        # Check the first example
        example_1 = data[0]
        self.assertEqual(example_1["id"], 1)
        self.assertEqual(example_1["name"], "Example 1")
        self.assertEqual(example_1["description"], "First example")
        
        # Check the second example
        example_2 = data[1]
        self.assertEqual(example_2["id"], 2)
        self.assertEqual(example_2["name"], "Example 2")
        self.assertEqual(example_2["description"], "Second example")
    
    def test_get_example_by_id(self):
        """
        Test getting a specific example by ID.
        """
        response = self.client.get("/api/v1/examples/1")
        
        # Check the response status code
        self.assertEqual(response.status_code, 200)
        
        # Check the response data
        data = response.json()
        self.assertEqual(data["id"], 1)
        self.assertEqual(data["name"], "Example 1")
        self.assertEqual(data["description"], "First example")
    
    def test_get_example_by_id_not_found(self):
        """
        Test getting a non-existent example.
        """
        response = self.client.get("/api/v1/examples/999")
        
        # Check the response status code
        self.assertEqual(response.status_code, 404)
        
        # Check the response data
        data = response.json()
        self.assertEqual(data["detail"], "Example with ID 999 not found")

if __name__ == "__main__":
    unittest.main()
