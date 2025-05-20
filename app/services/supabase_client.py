"""
Supabase API interaction logic for the DevDox AI Portal API.
"""

import requests
from typing import Dict, List, Any, Optional, Union
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
        Retrieves a single record from a table by its ID.
        
        Args:
            table: Name of the table to query.
            id_value: The ID value to match.
            columns: Comma-separated list of columns to select (default is all).
        
        Returns:
            The matching record as a dictionary if found, otherwise None.
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

    def filter(self,
               table: str,
               filters: Dict[str, Any],
               columns: str = "*",
               single: bool = False,
               order_by: str = None,
               limit: int = None) -> Union[List[Dict[str, Any]], Optional[Dict[str, Any]]]:
        """
               Retrieves records from a table that match specified filter conditions.
               
               Args:
                   table: Name of the table to query.
                   filters: Dictionary mapping column names to values for filtering results.
                   columns: Comma-separated list of columns to select. Defaults to all columns.
                   single: If True, returns only the first matching record or None if no match.
                   order_by: Optional ordering for results, e.g., "column.asc" or "column.desc".
                   limit: Optional maximum number of records to return.
               
               Returns:
                   A list of matching records, a single record if single=True, or None if no results are found and single=True.
               """
        url = self._build_url(table)
        params = {"select": columns}

        # Add filter parameters
        for column, value in filters.items():
            params[column] = f"eq.{value}"

        # Add order parameter if provided
        if order_by:
            params["order"] = order_by

        # Add limit parameter if provided
        if limit:
            params["limit"] = limit

        response = requests.get(url, headers=self.headers, params=params)

        if response.status_code == 200:
            result = response.json()

            if single:
                if result:
                    return result[0]
                return None

            return result

        response.raise_for_status()
        return [] if not single else None

    
    def insert(self, table: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Inserts a new record into the specified table and returns the inserted record.
        
        Args:
            table: Name of the table to insert into.
            data: Dictionary containing the data for the new record.
        
        Returns:
            The inserted record as a dictionary.
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
