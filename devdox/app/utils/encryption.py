from app.config import settings
from encryption_src.fernet.service import FernetEncryptionHelper


def get_encryption_helper() -> FernetEncryptionHelper:
    env_secret_key: str = settings.SECRET_KEY
    return FernetEncryptionHelper(secret_key=env_secret_key)
