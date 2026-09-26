from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from polyvox.auth.security import verify_password
from polyvox.auth.session import create_session_token
from polyvox.config import settings
from polyvox.db.base import get_db
from polyvox.db.models import User
from polyvox.templating import templates
from datetime import datetime, timezone

router = APIRouter()


@router.get("/")
def index():
    return RedirectResponse(url="/generate", status_code=303)


@router.get("/login")
def login_form(request: Request):
    return templates.TemplateResponse(request, "login.html", {"error": None})


@router.post("/login")
def login_submit(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db),
):
    user = db.query(User).filter(User.email == email).first()
    if user is None or not user.is_active or not verify_password(password, user.password_hash):
        return templates.TemplateResponse(
            request, "login.html", {"error": "Invalid email or password"}, status_code=401
        )

    user.last_login_at = datetime.now(timezone.utc)
    db.commit()

    token = create_session_token(str(user.id))
    response = RedirectResponse(url="/generate", status_code=303)
    response.set_cookie(
        key=settings.session_cookie_name,
        value=token,
        max_age=settings.session_max_age_seconds,
        httponly=True,
        samesite="lax",
        secure=settings.env == "production",
    )
    return response


@router.post("/logout")
def logout():
    response = RedirectResponse(url="/login", status_code=303)
    response.delete_cookie(settings.session_cookie_name)
    return response
