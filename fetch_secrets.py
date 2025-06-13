import os
import asyncio
from tortoise import Tortoise
from app.config import settings, TORTOISE_ORM


SUPABASE_URL = settings.SUPABASE_URL
SUPABASE_SERVICE_ROLE_KEY = settings.SUPABASE_SECRET_KEY
SECRET_KEYS = settings.VAULT_KEYS.split(",")


async def fetch_and_append_secrets():
    await Tortoise.init(config=TORTOISE_ORM)
    from tortoise import connections

    try:
        conn = connections.get("default")
        columns, rows = await conn.execute_query(
            "SELECT * FROM vault.decrypted_secrets"
        )
        with open(".env", "a") as env_file:
            for result in rows:
                env_file.write(f"{result['name']}={result['decrypted_secret']}\n")
    finally:
        await Tortoise.close_connections()


if __name__ == "__main__":
    asyncio.run(fetch_and_append_secrets())
