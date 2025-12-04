import pytest
from starlette.testclient import TestClient

from app.main import app

@pytest.fixture(autouse=True)
def _disable_mongo(monkeypatch):
    # Make settings.MONGO falsy so lifespan() skips Mongo init in tests
    import app.main as app_main
    monkeypatch.setattr(app_main.settings, "MONGO", None, raising=False)


@pytest.fixture
def client_permissive():
    with TestClient(app, raise_server_exceptions=False) as c:
        yield c


TOKEN_ENCRYPTED_1 = "gAAAAABoMFiNIvAc7WIFnoKXBjkpAVrdiTFrhlmZtG8BBwvmy1dtvfEFmupm0fcvDUo3unosoAQz5eclP2QFMnPMLG4Hj21MBt-xTdWL661JnWP-wQarnLI="
