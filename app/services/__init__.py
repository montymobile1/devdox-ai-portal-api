"""
Services package initializer.
"""

from .supabase_client import SupabaseClient


db_client = SupabaseClient()


async def connect_db():
    await db_client.connect()


async def disconnect_db():
    await db_client.disconnect()
