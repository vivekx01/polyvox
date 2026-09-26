from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer

from polyvox.config import settings

_serializer = URLSafeTimedSerializer(settings.secret_key, salt="polyvox-session")


def create_session_token(user_id: str) -> str:
    return _serializer.dumps({"user_id": user_id})


def read_session_token(token: str) -> str | None:
    try:
        data = _serializer.loads(token, max_age=settings.session_max_age_seconds)
    except (BadSignature, SignatureExpired):
        return None
    return data.get("user_id")
