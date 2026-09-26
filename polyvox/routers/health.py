from fastapi import APIRouter, Depends, Response
from sqlalchemy import text
from sqlalchemy.orm import Session

from polyvox.db.base import get_db
from polyvox.queue.rq_setup import redis_conn

router = APIRouter()


@router.get("/health")
def health(response: Response, db: Session = Depends(get_db)):
    checks = {"database": "ok", "redis": "ok"}

    try:
        db.execute(text("SELECT 1"))
    except Exception as exc:
        checks["database"] = f"error: {exc}"

    try:
        redis_conn.ping()
    except Exception as exc:
        checks["redis"] = f"error: {exc}"

    healthy = all(v == "ok" for v in checks.values())
    if not healthy:
        response.status_code = 503

    return {"status": "ok" if healthy else "degraded", "checks": checks}
