import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from polyvox.auth.dependencies import require_admin_page
from polyvox.auth.security import generate_api_key, hash_password
from polyvox.db.base import get_db
from polyvox.db.models import ApiKey, User, UserRole
from polyvox.templating import templates

router = APIRouter(prefix="/admin")


@router.get("/users")
def list_users(
    request: Request,
    admin: User = Depends(require_admin_page),
    db: Session = Depends(get_db),
):
    users = db.query(User).order_by(User.created_at.desc()).all()
    return templates.TemplateResponse(
        request, "admin_users.html", {"current_user": admin, "users": users, "error": None}
    )


@router.post("/users")
def create_user(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    role: str = Form(default="user"),
    admin: User = Depends(require_admin_page),
    db: Session = Depends(get_db),
):
    role_enum = UserRole.admin if role == "admin" else UserRole.user

    if db.query(User).filter(User.email == email).first() is not None:
        users = db.query(User).order_by(User.created_at.desc()).all()
        return templates.TemplateResponse(
            request,
            "admin_users.html",
            {"current_user": admin, "users": users, "error": f"A user with email {email} already exists"},
            status_code=400,
        )

    user = User(email=email, password_hash=hash_password(password), role=role_enum)
    db.add(user)
    db.commit()
    return RedirectResponse(url="/admin/users", status_code=303)


@router.post("/users/{user_id}/deactivate")
def toggle_user_active(
    user_id: uuid.UUID,
    admin: User = Depends(require_admin_page),
    db: Session = Depends(get_db),
):
    user = db.get(User, user_id)
    if user is not None and user.id != admin.id:
        user.is_active = not user.is_active
        db.commit()
    return RedirectResponse(url="/admin/users", status_code=303)


@router.get("/api-keys")
def list_api_keys(
    request: Request,
    admin: User = Depends(require_admin_page),
    db: Session = Depends(get_db),
):
    keys = db.query(ApiKey).order_by(ApiKey.created_at.desc()).all()
    users = db.query(User).filter(User.is_active.is_(True)).order_by(User.email).all()
    return templates.TemplateResponse(
        request,
        "admin_api_keys.html",
        {"current_user": admin, "keys": keys, "users": users, "new_raw_key": None, "new_key_label": None},
    )


@router.post("/api-keys")
def create_api_key(
    request: Request,
    label: str = Form(...),
    owner_user_id: uuid.UUID = Form(...),
    admin: User = Depends(require_admin_page),
    db: Session = Depends(get_db),
):
    owner = db.get(User, owner_user_id)
    users = db.query(User).filter(User.is_active.is_(True)).order_by(User.email).all()
    if owner is None or not owner.is_active:
        keys = db.query(ApiKey).order_by(ApiKey.created_at.desc()).all()
        return templates.TemplateResponse(
            request,
            "admin_api_keys.html",
            {"current_user": admin, "keys": keys, "users": users, "new_raw_key": None, "new_key_label": None},
            status_code=400,
        )

    raw_key, prefix, key_hash = generate_api_key()
    api_key = ApiKey(
        owner_user_id=owner.id,
        created_by_user_id=admin.id,
        label=label,
        prefix=prefix,
        key_hash=key_hash,
    )
    db.add(api_key)
    db.commit()

    keys = db.query(ApiKey).order_by(ApiKey.created_at.desc()).all()
    return templates.TemplateResponse(
        request,
        "admin_api_keys.html",
        {"current_user": admin, "keys": keys, "users": users, "new_raw_key": raw_key, "new_key_label": label},
    )


@router.post("/api-keys/{key_id}/revoke")
def revoke_api_key(
    key_id: uuid.UUID,
    admin: User = Depends(require_admin_page),
    db: Session = Depends(get_db),
):
    key = db.get(ApiKey, key_id)
    if key is not None and key.revoked_at is None:
        key.revoked_at = datetime.now(timezone.utc)
        db.commit()
    return RedirectResponse(url="/admin/api-keys", status_code=303)
