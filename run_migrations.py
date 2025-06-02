"""
Automated database migration runner for Tortoise ORM using Aerich.

This script handles both initial database setup and subsequent migrations,
integrating with the FastAPI application startup process.
"""

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
    """Initialize Tortoise ORM connection and generate schemas safely."""
    try:
        await Tortoise.init(config=TORTOISE_ORM)
        await Tortoise.generate_schemas(safe=True)
    except Exception as e:
        logger.error("Failed to initialize Tortoise ORM: %s", str(e))
        raise
    finally:
        await Tortoise.close_connections()


def run_command(cmd):
    """Execute a command and log the result."""
    try:
        # Split command for security (avoid shell=True)
        cmd_list = cmd.split()
        result = subprocess.run(cmd_list, capture_output=True, text=True, check=True)
        logger.info("Command executed successfully: %s", result.stdout)
    except subprocess.CalledProcessError as e:
        logger.error("Command failed with return code %s: %s", e.returncode, e.stderr)
        raise
    except Exception as e:
        logger.error("Unexpected error running command '%s': %s", cmd, str(e))
        raise


def is_first_time():
    """Check if this is the first time running migrations."""
    if not os.path.exists(MIGRATIONS_DIR):
        return True

    files = os.listdir(MIGRATIONS_DIR)
    # Filter out __init__.py when checking if directory has meaningful content
    migration_files = [f for f in files if f != "__init__.py"]
    return len(migration_files) == 0


async def run():
    try:
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
    except subprocess.CalledProcessError:
        logger.error("Migration failed - this may require manual intervention")
        raise


if __name__ == "__main__":
    asyncio.run(run())
