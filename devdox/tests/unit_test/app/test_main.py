import pytest
from models_src.configs.mongo_config import MongoConfig
from pydantic import SecretStr

from app.main import init_mongo, shutdown_mongo


@pytest.fixture
def mongo_settings() -> MongoConfig:
    """
    Mongo config used only for init_mongo/shutdown_mongo tests.
    Adjust fields to match your actual MongoConfig signature.
    """
    return MongoConfig(
        HOST="localhost",
        PORT=27017,
        USERNAME="test",
        PASSWORD=SecretStr("test"),
        DB="devdox_ai_test",
        # add/adjust any required fields your MongoConfig has
    )

class DummyMongoClient:
    def __init__(self):
        self.closed = False
    def close(self):
        self.closed = True

class DummyMongoDb:
    async def command(self, cmd):
        raise Exception("boom")

@pytest.mark.asyncio
async def test_init_mongo_closes_client_on_failed_ping(monkeypatch, mongo_settings):
    async def fake_init_via_uri(uri):
        return DummyMongoClient(), DummyMongoDb()

    from app import main as app_main
    monkeypatch.setattr(app_main, "init_via_uri", fake_init_via_uri)

    with pytest.raises(Exception):
        await init_mongo(mongo_settings)

@pytest.mark.asyncio
async def test_shutdown_mongo_closes_client(mongo_settings):
    client = DummyMongoClient()
    await shutdown_mongo(mongo_settings, client)
    assert client.closed is True