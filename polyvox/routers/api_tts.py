import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from polyvox.auth.dependencies import Principal, get_current_principal, require_job_access
from polyvox.db.base import get_db
from polyvox.db.models import Job, JobStatus
from polyvox.schemas.tts import JobCreateRequest, JobCreateResponse, JobStatusResponse, LanguageOut, VoiceOut
from polyvox.services.jobs import create_job, delete_job, get_job, sync_job_from_rq
from polyvox.tts.languages import LANGUAGES, VOICES

router = APIRouter(prefix="/api/v1")


def _to_status_response(job: Job) -> JobStatusResponse:
    audio_url = None
    if job.status == JobStatus.finished and job.audio_expired_at is None and job.audio_filename:
        audio_url = f"/audio/{job.audio_filename}"

    return JobStatusResponse(
        job_id=str(job.id),
        status=job.status.value,
        lang=job.lang,
        voice=job.voice,
        char_count=job.char_count,
        audio_url=audio_url,
        duration_seconds=job.duration_seconds,
        error=job.error_message,
        created_at=job.created_at,
        finished_at=job.finished_at,
    )


@router.get("/languages", response_model=list[LanguageOut])
def list_languages(_: Principal = Depends(get_current_principal)):
    return LANGUAGES


@router.get("/voices", response_model=list[VoiceOut])
def list_voices(_: Principal = Depends(get_current_principal)):
    return VOICES


@router.post("/jobs", response_model=JobCreateResponse, status_code=202)
def submit_job(
    payload: JobCreateRequest,
    principal: Principal = Depends(get_current_principal),
    db: Session = Depends(get_db),
):
    job = create_job(
        db,
        principal,
        text=payload.text,
        lang=payload.lang,
        voice=payload.voice,
        speed=payload.speed,
        steps=payload.steps,
    )
    return JobCreateResponse(job_id=str(job.id), status=job.status.value, created_at=job.created_at)


@router.get("/jobs/{job_id}", response_model=JobStatusResponse)
def get_job_status(
    job_id: uuid.UUID,
    principal: Principal = Depends(get_current_principal),
    db: Session = Depends(get_db),
):
    job = get_job(db, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    require_job_access(job, principal)
    job = sync_job_from_rq(db, job)
    return _to_status_response(job)


@router.delete("/jobs/{job_id}", status_code=204)
def delete_job_endpoint(
    job_id: uuid.UUID,
    principal: Principal = Depends(get_current_principal),
    db: Session = Depends(get_db),
):
    job = get_job(db, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    require_job_access(job, principal)
    delete_job(db, job)


@router.get("/jobs", response_model=list[JobStatusResponse])
def list_jobs(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    principal: Principal = Depends(get_current_principal),
    db: Session = Depends(get_db),
):
    query = db.query(Job).filter(Job.user_id == principal.user.id).order_by(Job.created_at.desc())
    jobs = query.offset(offset).limit(limit).all()
    return [_to_status_response(sync_job_from_rq(db, job)) for job in jobs]
