import os
import subprocess
import asyncio
import logging
from tortoise import Tortoise
from app.config import TORTOISE_ORM


AERICH_CONFIG = "aerich.ini"
MIGRATIONS_DIR = "migrations"

logger = logging.getLogger(__name__)


async def ensure_tortoise_connected():
    await Tortoise.init(config=TORTOISE_ORM)
    await Tortoise.generate_schemas(safe=True)
    await Tortoise.close_connections()


def run_command(cmd):
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    if result.returncode != 0:

        logger.error(f"Error: {result.stderr}")
    else:
        logger.info(result.stdout)


def is_first_time():
    return not os.path.exists(MIGRATIONS_DIR) or not os.listdir(MIGRATIONS_DIR)


async def run():
    if is_first_time():
        logger.info("First-time setup: Running aerich init and init-db...")
        run_command("aerich init -t app.config.TORTOISE_ORM")
        run_command("aerich init-db")
    else:
        print("Running aerich migrate and upgrade...")
        logger.info("Running aerich migrate and upgrade...")
        run_command("aerich migrate")
        run_command("aerich upgrade")

    # Optional: ensure Tortoise connection is valid
    await ensure_tortoise_connected()


if __name__ == "__main__":
    asyncio.run(run())
