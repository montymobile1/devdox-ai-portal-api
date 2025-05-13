"""
Tests for the Supabase client service in the DevDox AI Portal API.
"""

import unittest
from unittest.mock import patch, MagicMock
from app.services.supabase_client import SupabaseClient

class TestSupabaseClient(unittest.TestCase):
    """
    Test class for the Supabase client service.
    """
    
    def setUp(self):
        """
        Set up the test environment.
        """
        # Create a client with mock URL and key for testing
        self.client = SupabaseClient(
            url="https://example.supabase.co",
            key="mock-key"
        )
    
    def test_init(self):
        """
        Test client initialization.
        """
        self.assertEqual(self.client.url, "https://example.supabase.co")
        self.assertEqual(self.client.key, "mock-key")
        self.assertEqual(self.client.headers["apikey"], "mock-key")
        self.assertEqual(self.client.headers["Authorization"], "Bearer mock-key")
        self.assertEqual(self.client.headers["Content-Type"], "application/json")
    
    def test_build_url(self):
        """
        Test URL building.
        """
        url = self.client._build_url("test_table")
        self.assertEqual(url, "https://example.supabase.co/rest/v1/test_table")
    
    @patch('requests.get')
    def test_select(self, mock_get):
        """
        Test select method.
        """
        # Mock the response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = [
            {"id": 1, "name": "Test 1"},
            {"id": 2, "name": "Test 2"}
        ]
        mock_get.return_value = mock_response
        
        # Call the method
        result = self.client.select("test_table")
        
        # Check the result
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]["id"], 1)
        self.assertEqual(result[0]["name"], "Test 1")
        self.assertEqual(result[1]["id"], 2)
        self.assertEqual(result[1]["name"], "Test 2")
        
        # Check the call
        mock_get.assert_called_with(
            "https://example.supabase.co/rest/v1/test_table",
            headers=self.client.headers,
            params={"select": "*"}
        )
    
    @patch('requests.get')
    def test_get_by_id(self, mock_get):
        """
        Test get_by_id method.
        """
        # Mock the response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = [{"id": 1, "name": "Test 1"}]
        mock_get.return_value = mock_response
        
        # Call the method
        result = self.client.get_by_id("test_table", "1")
        
        # Check the result
        self.assertEqual(result["id"], 1)
        self.assertEqual(result["name"], "Test 1")
        
        # Check the call
        mock_get.assert_called_with(
            "https://example.supabase.co/rest/v1/test_table",
            headers=self.client.headers,
            params={"select": "*", "id": "eq.1"}
        )
    
    @patch('requests.get')
    def test_get_by_id_not_found(self, mock_get):
        """
        Test get_by_id method when record is not found.
        """
        # Mock the response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = []
        mock_get.return_value = mock_response
        
        # Call the method
        result = self.client.get_by_id("test_table", "999")
        
        # Check the result
        self.assertIsNone(result)
        
        # Check the call
        mock_get.assert_called_with(
            "https://example.supabase.co/rest/v1/test_table",
            headers=self.client.headers,
            params={"select": "*", "id": "eq.999"}
        )
    
    @patch('requests.post')
    def test_insert(self, mock_post):
        """
        Test insert method.
        """
        # Mock the response
        mock_response = MagicMock()
        mock_response.status_code = 201
        mock_response.json.return_value = [{"id": 1, "name": "Test 1"}]
        mock_post.return_value = mock_response
        
        # Call the method
        data = {"name": "Test 1"}
        result = self.client.insert("test_table", data)
        
        # Check the result
        self.assertEqual(result["id"], 1)
        self.assertEqual(result["name"], "Test 1")
        
        # Check the call
        expected_headers = {**self.client.headers, "Prefer": "return=representation"}
        mock_post.assert_called_with(
            "https://example.supabase.co/rest/v1/test_table",
            headers=expected_headers,
            json=data
        )
    
    @patch('requests.patch')
    def test_update(self, mock_patch):
        """
        Test update method.
        """
        # Mock the response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = [{"id": 1, "name": "Updated Test"}]
        mock_patch.return_value = mock_response
        
        # Call the method
        data = {"name": "Updated Test"}
        result = self.client.update("test_table", "1", data)
        
        # Check the result
        self.assertEqual(result["id"], 1)
        self.assertEqual(result["name"], "Updated Test")
        
        # Check the call
        expected_headers = {**self.client.headers, "Prefer": "return=representation"}
        mock_patch.assert_called_with(
            "https://example.supabase.co/rest/v1/test_table",
            headers=expected_headers,
            params={"id": "eq.1"},
            json=data
        )
    
    @patch('requests.delete')
    def test_delete(self, mock_delete):
        """
        Test delete method.
        """
        # Mock the response
        mock_response = MagicMock()
        mock_response.status_code = 204
        mock_delete.return_value = mock_response
        
        # Call the method
        self.client.delete("test_table", "1")
        
        # Check the call
        mock_delete.assert_called_with(
            "https://example.supabase.co/rest/v1/test_table",
            headers=self.client.headers,
            params={"id": "eq.1"}
        )

if __name__ == "__main__":
    unittest.main()
