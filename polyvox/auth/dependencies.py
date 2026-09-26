import uuid
from dataclasses import dataclass
from datetime import datetime, timezone

from fastapi import Depends, HTTPException, Request
from sqlalchemy.orm import Session

from polyvox.auth.security import hash_api_key
from polyvox.auth.session import read_session_token
from polyvox.config import settings
from polyvox.db.base import get_db
from polyvox.db.models import ApiKey, Job, User


class RedirectToLogin(Exception):
    """Raised by page routes when no valid session is present."""


@dataclass
class Principal:
    user: User
    api_key: ApiKey | None
    source: str  # "ui" or "api"


def _get_session_user(request: Request, db: Session) -> User | None:
    token = request.cookies.get(settings.session_cookie_name)
    if not token:
        return None
    user_id = read_session_token(token)
    if not user_id:
        return None
    try:
        user_uuid = uuid.UUID(user_id)
    except ValueError:
        return None
    user = db.get(User, user_uuid)
    if user is None or not user.is_active:
        return None
    return user


def _get_api_key_user(request: Request, db: Session) -> tuple[User, ApiKey] | None:
    raw_key = request.headers.get("X-API-Key")
    if not raw_key:
        return None
    key_hash = hash_api_key(raw_key)
    api_key = db.query(ApiKey).filter(ApiKey.key_hash == key_hash).first()
    if api_key is None or api_key.revoked_at is not None:
        return None
    owner = db.get(User, api_key.owner_user_id)
    if owner is None or not owner.is_active:
        return None
    api_key.last_used_at = datetime.now(timezone.utc)
    db.commit()
    return owner, api_key


# --- Page routes (browser, session cookie only) ---


def require_user_page(request: Request, db: Session = Depends(get_db)) -> User:
    user = _get_session_user(request, db)
    if user is None:
        raise RedirectToLogin()
    return user


def require_admin_page(user: User = Depends(require_user_page)) -> User:
    if not user.is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")
    return user


# --- JSON API routes (session cookie OR API key) ---


def get_current_principal(request: Request, db: Session = Depends(get_db)) -> Principal:
    api_key_result = _get_api_key_user(request, db)
    if api_key_result is not None:
        owner, api_key = api_key_result
        return Principal(user=owner, api_key=api_key, source="api")

    session_user = _get_session_user(request, db)
    if session_user is not None:
        return Principal(user=session_user, api_key=None, source="ui")

    raise HTTPException(status_code=401, detail="Authentication required")


def require_job_access(job: Job, principal: Principal) -> None:
    if job.user_id != principal.user.id and not principal.user.is_admin:
        raise HTTPException(status_code=404, detail="Job not found")
