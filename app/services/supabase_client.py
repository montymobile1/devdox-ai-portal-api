from tortoise import Tortoise, connections

from typing import Dict, List, Any, Optional, Union
import logging
from app.config import settings

logger = logging.getLogger(__name__)


class SupabaseClient:
    """
    Tortoise ORM client that replaces direct psycopg2 connections.
    Uses the same configuration structure as your existing setup.
    """

    def __init__(self):
        self.is_connected = False
        self.connection = None

    async def connect(self) -> bool:
        """
        Establish connection using Tortoise ORM.
        Replaces: connection = psycopg2.connect(...)
        """
        try:
            # Build Tortoise configuration using your existing settings
            config = {
                "connections": {
                    "default": {
                        "engine": "tortoise.backends.asyncpg",
                        "credentials": {
                            "host": settings.SUPABASE_HOST,
                            "port": settings.SUPABASE_PORT,
                            "user": settings.SUPABASE_USER,
                            "password": settings.SUPABASE_PASSWORD,
                            "database": settings.SUPABASE_DB_NAME,
                            "ssl": "require",  # Supabase requires SSL
                            "minsize": 1,
                            "maxsize": 10,
                        },
                    }
                },
                "apps": {
                    "models": {
                        "models": [
                            "__main__",
                            "app.models",
                        ],  # Update with your models path
                        "default_connection": "default",
                    }
                },
                "timezone": "UTC",
            }

            # Initialize Tortoise
            await Tortoise.init(config=config)

            # Test connection
            self.connection = connections.get("default")
            await self.connection.execute_query("SELECT 1")

            self.is_connected = True
            logger.info("✓ Tortoise ORM connected to Supabase successfully")
            return True

        except Exception as e:
            logger.error(f"✗ Connection failed: {e}")
            return False

    async def disconnect(self):
        """
        Close the database connection.
        Replaces: connection.close()
        """
        if self.is_connected:
            await Tortoise.close_connections()
            self.is_connected = False
            self.connection = None
            logger.info("Database connection closed")

    async def execute_query(self, query: str, params: tuple = None) -> List[Dict]:
        """
        Execute a raw SQL query.
        Replaces: cursor.execute(query, params)

        Args:
            query: SQL query string
            params: Query parameters as tuple

        Returns:
            List of dictionaries representing query results
        """
        if not self.is_connected:
            raise RuntimeError("Database not connected. Call connect() first.")

        try:
            # Convert tuple params to list if provided
            param_list = list(params) if params else []

            # Execute query and return results
            results = await self.connection.execute_query(query, param_list)

            # results is a tuple: (query, rows)
            # rows is a list of Record objects that can be converted to dicts
            if len(results) > 1:
                rows = results[1]
                return [dict(row) for row in rows] if rows else []
            return []

        except Exception as e:
            logger.error(f"Query execution failed: {e}")
            raise

    async def execute_query_one(
        self, query: str, params: tuple = None
    ) -> Optional[Dict]:
        """
        Execute a query and return only the first result.
        Replaces: cursor.fetchone()
        """
        results = await self.execute_query(query, params)
        return results[0] if results else None

    async def execute_query_many(self, query: str, params: tuple = None) -> List[Dict]:
        """
        Execute a query and return all results.
        Replaces: cursor.fetchall()
        """
        return await self.execute_query(query, params)

    async def insert_row(self, table: str, values: Dict[str, Any]) -> Optional[Any]:
        """
        Insert a new row into the given table.

        Args:
            table: Name of the table to insert into.
            values: Dictionary of column names and values to insert.

        Returns:
            The ID of the inserted row if successful, None otherwise.
        """
        try:
            if not values:
                raise ValueError("No values provided for insertion.")

            columns = ", ".join(values.keys())
            placeholders = ", ".join([f"${i+1}" for i in range(len(values))])
            params = tuple(values.values())

            query = (
                f"INSERT INTO {table} ({columns}) VALUES ({placeholders}) RETURNING id"
            )
            result = await self.execute_query_one(query, params)
            return result["id"] if result else None
        except Exception as e:
            logger.error(f"Insert failed: {e}")
            raise

    async def execute_update(self, query: str, params: tuple = None) -> int:
        """
        Execute an UPDATE/DELETE query and return affected row count.
        """
        try:
            param_list = list(params) if params else []
            result = await self.connection.execute_query(query, param_list)
            # For UPDATE/DELETE, the result typically contains the row count
            return result[0] if isinstance(result, tuple) and result else 0
        except Exception as e:
            logger.error(f"Update/Delete execution failed: {e}")
            raise

    async def execute_delete(self, query: str, params: tuple = None) -> int:
        """
        Execute a DELETE query and return affected row count.
        Alias to: execute_update()

        Args:
            query: DELETE SQL query
            params: Query parameters as tuple

        Returns:
            Number of rows deleted
        """
        return await self.execute_update(query, params)

    async def delete_rows(
        self, table: str, where_clause: str, params: tuple = None
    ) -> int:
        """
        Convenience method to delete rows from a given table.

        Example:
            await client.delete_rows("users", "email = $1", ("user@example.com",))

        Args:
            table: Table name
            where_clause: WHERE condition as a string, e.g., "id = $1"
            params: Parameters for the WHERE clause

        Returns:
            Number of rows deleted
        """
        query = f"DELETE FROM {table} WHERE {where_clause}"
        return await self.execute_delete(query, params)

    # Context manager support for automatic connection handling
    async def __aenter__(self):
        """Async context manager entry."""
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.disconnect()
