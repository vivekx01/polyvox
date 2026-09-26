from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from polyvox.auth.dependencies import require_user_page
from polyvox.db.base import get_db
from polyvox.db.models import User
from polyvox.services.jobs import sync_job_from_rq
from polyvox.templating import templates
from polyvox.tts.languages import LANGUAGES, VOICES
from polyvox.db.models import Job

router = APIRouter()


@router.get("/generate")
def generate_page(
    request: Request,
    user: User = Depends(require_user_page),
    db: Session = Depends(get_db),
):
    recent_jobs = (
        db.query(Job).filter(Job.user_id == user.id).order_by(Job.created_at.desc()).limit(20).all()
    )
    recent_jobs = [sync_job_from_rq(db, job) for job in recent_jobs]

    return templates.TemplateResponse(
        request,
        "generate.html",
        {
            "current_user": user,
            "languages": LANGUAGES,
            "voices": VOICES,
            "recent_jobs": recent_jobs,
        },
    )
