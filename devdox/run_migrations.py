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
from tortoise.exceptions import OperationalError
from app.config import TORTOISE_ORM


AERICH_CONFIG = "aerich.ini"
MIGRATIONS_DIR = "../migrations"

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
        return False
    except Exception as e:
        logger.error("Unexpected error running command '%s': %s", cmd, str(e))
        return False


def is_first_time():
    """Check if this is the first time running migrations."""
    if not os.path.exists(MIGRATIONS_DIR):
        return True

    files = os.listdir(MIGRATIONS_DIR)
    # Filter out __init__.py when checking if directory has meaningful content
    migration_files = [f for f in files if f != "__init__.py"]
    return len(migration_files) == 0


async def database_tables_exist():
    """Check if the 'aerich' table exists in the PostgreSQL database (Supabase)."""
    try:
        # Initialize Tortoise connection
        await Tortoise.init(config=TORTOISE_ORM)

        connection = Tortoise.get_connection("default")

        # Execute the query to check for 'aerich' table
        rows, _ = await connection.execute_query(
            "SELECT tablename FROM pg_catalog.pg_tables WHERE schemaname = 'public' AND tablename = 'aerich';"
        )

        # If any row is returned, the table exists
        return rows > 0

    except (OperationalError, AttributeError) as e:
        logger.debug("Database check failed: %s", e)
        return False
    except Exception as e:
        logger.error("Unexpected error during database check: %s", str(e))
        return False
    finally:
        await Tortoise.close_connections()


async def needs_initialization():
    """
    Determine if we need to run init-db based on:
    Migration files exist but database tables don't exist (deployment scenario)
    """

    # Check if database tables exist
    tables_exist = await database_tables_exist()
    if not tables_exist:
        logger.info(
            "Migration files exist but no database tables found - treating as fresh deployment"
        )
        return True

    return False


async def run():
    try:
        if not os.path.exists(MIGRATIONS_DIR):
            _ = run_command("aerich init -t app.config.TORTOISE_ORM")
        _ = run_command("aerich init-db")
        # if await needs_initialization():
        #     logger.info("Initializing database: Running aerich init and init-db...")
        #
        #     # Only run aerich init if migrations directory doesn't exist
        #     if not os.path.exists(MIGRATIONS_DIR):
        #         run_command("aerich init -t app.config.TORTOISE_ORM")

        # else:
        #     logger.info("Running aerich migrate and upgrade...")
        #     run_command("aerich migrate")
        #     run_command("aerich upgrade")
        logger.info("Running aerich migrate and upgrade...")
        _ = run_command("aerich migrate")
        _ = run_command("aerich upgrade")
        # Optional: ensure Tortoise connection is valid
        await ensure_tortoise_connected()

    except subprocess.CalledProcessError:
        logger.error("Migration failed - this may require manual intervention")
        raise


if __name__ == "__main__":
    asyncio.run(run())
