"""Unit tests for auth primitives that need no live Postgres/Redis.

Full end-to-end verification (login, job submission, admin flows) requires
`docker compose up` (Postgres + Redis) — see README.md.
"""

from polyvox.auth.security import API_KEY_PREFIX, generate_api_key, hash_api_key, hash_password, verify_password
from polyvox.auth.session import create_session_token, read_session_token


def test_password_hash_roundtrip():
    hashed = hash_password("correct horse battery staple")
    assert verify_password("correct horse battery staple", hashed)
    assert not verify_password("wrong password", hashed)


def test_api_key_generation():
    raw_key, prefix, key_hash = generate_api_key()
    assert raw_key.startswith(API_KEY_PREFIX)
    assert raw_key.startswith(prefix)
    assert key_hash == hash_api_key(raw_key)
    # Two keys should never collide.
    raw_key_2, _, key_hash_2 = generate_api_key()
    assert raw_key != raw_key_2
    assert key_hash != key_hash_2


def test_session_token_roundtrip():
    token = create_session_token("11111111-1111-1111-1111-111111111111")
    assert read_session_token(token) == "11111111-1111-1111-1111-111111111111"


def test_session_token_rejects_tampering():
    token = create_session_token("11111111-1111-1111-1111-111111111111")
    assert read_session_token(token + "x") is None
