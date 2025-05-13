"""
Supabase API interaction logic for the DevDox AI Portal API.
"""

import requests
from typing import Dict, List, Any, Optional
from app.config import settings

class SupabaseClient:
    """
    A client for interacting with Supabase API.
    """
    
    def __init__(self, url: str = None, key: str = None):
        """
        Initialize the Supabase client.
        
        Args:
            url (str, optional): Supabase project URL. Defaults to settings.SUPABASE_URL.
            key (str, optional): Supabase API key. Defaults to settings.SUPABASE_KEY.
        """
        self.url = url or settings.SUPABASE_URL
        self.key = key or settings.SUPABASE_KEY
        self.headers = {
            "apikey": self.key,
            "Authorization": f"Bearer {self.key}",
            "Content-Type": "application/json"
        }
    
    def _build_url(self, endpoint: str) -> str:
        """
        Build a full URL for a Supabase API endpoint.
        
        Args:
            endpoint (str): API endpoint path.
            
        Returns:
            str: Full URL.
        """
        return f"{self.url}/rest/v1/{endpoint}"
    
    def select(self, table: str, columns: str = "*") -> List[Dict[str, Any]]:
        """
        Select data from a table.
        
        Args:
            table (str): Table name.
            columns (str, optional): Columns to select. Defaults to "*".
            
        Returns:
            List[Dict[str, Any]]: List of records.
        """
        url = self._build_url(table)
        params = {"select": columns}
        
        response = requests.get(url, headers=self.headers, params=params)
        response.raise_for_status()
        
        return response.json()
    
    def get_by_id(self, table: str, id_value: str, columns: str = "*") -> Optional[Dict[str, Any]]:
        """
        Get a record by ID.
        
        Args:
            table (str): Table name.
            id_value (str): ID value to search for.
            columns (str, optional): Columns to select. Defaults to "*".
            
        Returns:
            Optional[Dict[str, Any]]: Record if found, None otherwise.
        """
        url = self._build_url(table)
        params = {
            "select": columns,
            "id": f"eq.{id_value}"
        }
        
        response = requests.get(url, headers=self.headers, params=params)
        
        if response.status_code == 200 and response.json():
            return response.json()[0]
        return None
    
    def insert(self, table: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Insert a new record.
        
        Args:
            table (str): Table name.
            data (Dict[str, Any]): Data to insert.
            
        Returns:
            Dict[str, Any]: Inserted record.
        """
        url = self._build_url(table)
        headers = {**self.headers, "Prefer": "return=representation"}
        
        response = requests.post(url, headers=headers, json=data)
        response.raise_for_status()
        
        return response.json()[0]
    
    def update(self, table: str, id_value: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Update a record by ID.
        
        Args:
            table (str): Table name.
            id_value (str): ID value to update.
            data (Dict[str, Any]): Data to update.
            
        Returns:
            Dict[str, Any]: Updated record.
        """
        url = self._build_url(table)
        headers = {**self.headers, "Prefer": "return=representation"}
        params = {"id": f"eq.{id_value}"}
        
        response = requests.patch(url, headers=headers, params=params, json=data)
        response.raise_for_status()
        
        return response.json()[0]
    
    def delete(self, table: str, id_value: str) -> None:
        """
        Delete a record by ID.
        
        Args:
            table (str): Table name.
            id_value (str): ID value to delete.
        """
        url = self._build_url(table)
        params = {"id": f"eq.{id_value}"}
        
        response = requests.delete(url, headers=self.headers, params=params)
        response.raise_for_status()

# Create a singleton instance
supabase = SupabaseClient()
