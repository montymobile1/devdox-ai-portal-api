import pytest

from models_src.configs.mongo_config import MongoConfig

from app.main import init_mongo, shutdown_mongo

# Toggle these tests on/off with an env var so CI doesn’t explode accidentally

def make_test_mongo_config() -> MongoConfig:
    """
    Build a MongoConfig specifically for tests.

    - By default this reads MONGO__* env vars, so you can point tests to a
      dedicated 'devdox_test' DB or test cluster.
    - If you want a fixed DB just for tests, you can explicitly do:

        return MongoConfig(
            host="localhost",
            port=27017,
            db="devdox_test",
        )
    """
    return MongoConfig(
	    HOST="localhost",
	    PORT=27017,
	    DB="devdox",
    )


async def test_init_mongo_success_and_shutdown_idempotent():
    """
    Happy-path test against a *real* MongoDB:

    - init_mongo should return a working client & db
    - db.command('ping') should succeed
    - shutdown_mongo should close the client without raising
    - calling shutdown_mongo twice should be a no-op (no exceptions)
    """
    cfg = make_test_mongo_config()

    client, db = await init_mongo(cfg)

    # Sanity checks
    assert client is not None
    assert db is not None

    # The health check inside init_mongo already pinged once; ping again here
    ping_res = await db.command("ping")
    assert ping_res.get("ok") == 1

    # First shutdown
    await shutdown_mongo(cfg, client)

    # Second shutdown (idempotency / no exception)
    await shutdown_mongo(cfg, client)


async def test_init_mongo_returns_none_tuple_when_config_is_none():
    """
    Even in integration tests, verify the 'no config' branch:

    - init_mongo(None) should *not* talk to Mongo at all
    - it should simply return (None, None)
    """
    client, db = await init_mongo(None)

    assert client is None
    assert db is None


# ----------------------------------------------------------------------
# Manual chaos test: run this with Mongo intentionally *down*
# ----------------------------------------------------------------------

async def test_init_mongo_fails_when_server_is_down():
    """
    Manual chaos scenario:

    1. Stop your Mongo container / service.
    2. Unskip this test temporarily.
    3. Run pytest. This should:

       - call init_mongo(cfg)
       - have the internal ping fail
       - trigger shutdown of the client
       - re-raise the ping exception

    This uses the real driver and real network failure, no mocks.
    """
    cfg = MongoConfig(
	    HOST="localhost",
	    PORT=30000,
	    DB="some_random_db",
    )

    with pytest.raises(Exception):
        await init_mongo(cfg)
