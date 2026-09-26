import logging

from sqlalchemy.exc import IntegrityError

from polyvox.auth.security import hash_password
from polyvox.config import settings
from polyvox.db.base import Base, SessionLocal, engine
from polyvox.db.models import User, UserRole

logger = logging.getLogger("polyvox.bootstrap")


def init_db() -> None:
    Base.metadata.create_all(bind=engine)
    _ensure_admin()


def _ensure_admin() -> None:
    db = SessionLocal()
    try:
        existing_admin = db.query(User).filter(User.role == UserRole.admin).first()
        if existing_admin is not None:
            return
        admin = User(
            email=settings.admin_email,
            password_hash=hash_password(settings.admin_password),
            role=UserRole.admin,
        )
        db.add(admin)
        db.commit()
        logger.info("Bootstrapped admin account for %s", settings.admin_email)
    except IntegrityError:
        # Another process bootstrapped concurrently; nothing to do.
        db.rollback()
    finally:
        db.close()
