from app.config import settings
from encryption_src.fernet.service import FernetEncryptionHelper as ConcreteEncryptionHelper


def get_encryption_helper() -> ConcreteEncryptionHelper:
    env_secret_key: str = settings.SECRET_KEY
    return ConcreteEncryptionHelper(secret_key=env_secret_key)
