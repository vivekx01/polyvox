import hashlib
import secrets

import bcrypt

API_KEY_PREFIX = "pvx_"


def hash_password(raw_password: str) -> str:
    return bcrypt.hashpw(raw_password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(raw_password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(raw_password.encode("utf-8"), password_hash.encode("utf-8"))
    except ValueError:
        return False


def generate_api_key() -> tuple[str, str, str]:
    """Returns (raw_key, display_prefix, key_hash). Only the hash is persisted."""
    token = secrets.token_urlsafe(32)
    raw_key = f"{API_KEY_PREFIX}{token}"
    display_prefix = raw_key[: len(API_KEY_PREFIX) + 8]
    key_hash = hash_api_key(raw_key)
    return raw_key, display_prefix, key_hash


def hash_api_key(raw_key: str) -> str:
    return hashlib.sha256(raw_key.encode("utf-8")).hexdigest()
