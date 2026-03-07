import base64
import os
from .exceptions import InvalidKeyError


def load_key() -> bytes:
    """
    Load AES key from environment variable
    """

    key_b64 = os.getenv("AES_SECRET_KEY")

    if not key_b64:
        raise InvalidKeyError("AES_SECRET_KEY not set")

    try:
        key = base64.urlsafe_b64decode(key_b64)
    except Exception:
        raise InvalidKeyError("Invalid AES key format")

    if len(key) != 32:
        raise InvalidKeyError("AES key must be 32 bytes")

    return key
