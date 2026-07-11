from cryptography.fernet import Fernet

from app.config import settings


def _get_fernet() -> Fernet:
    return Fernet(settings.encryption_key.encode())


def encrypt(plain_text: str) -> str:
    """Encrypt a value (e.g. a Plaid access token) before storing it in the DB."""
    return _get_fernet().encrypt(plain_text.encode()).decode()


def decrypt(encrypted_text: str) -> str:
    """Decrypt a value previously stored via encrypt()."""
    return _get_fernet().decrypt(encrypted_text.encode()).decode()
