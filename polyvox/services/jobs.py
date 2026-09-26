import os
import uuid
from datetime import datetime, timezone

from rq.exceptions import NoSuchJobError
from rq.job import Job as RQJob
from sqlalchemy.orm import Session

from polyvox.auth.dependencies import Principal
from polyvox.db.models import Job, JobSource, JobStatus
from polyvox.queue.rq_setup import enqueue_job, redis_conn
from polyvox.storage.paths import audio_path

PREVIEW_LEN = 200


def create_job(
    db: Session,
    principal: Principal,
    text: str,
    lang: str,
    voice: str,
    speed: float,
    steps: int,
) -> Job:
    job = Job(
        id=uuid.uuid4(),
        user_id=principal.user.id,
        api_key_id=principal.api_key.id if principal.api_key else None,
        source=JobSource.api if principal.source == "api" else JobSource.ui,
        text_preview=text[:PREVIEW_LEN],
        char_count=len(text),
        lang=lang,
        voice=voice,
        speed=speed,
        steps=steps,
        status=JobStatus.queued,
    )
    db.add(job)
    db.commit()
    db.refresh(job)

    enqueue_job(str(job.id), text, lang, voice, speed, steps)
    return job


def sync_job_from_rq(db: Session, job: Job) -> Job:
    """Write-through the live RQ status into the `jobs` row. No-op once the
    job has reached a terminal state we've already recorded."""
    if job.status in (JobStatus.finished, JobStatus.failed, JobStatus.expired):
        return job

    try:
        rq_job = RQJob.fetch(str(job.id), connection=redis_conn)
    except NoSuchJobError:
        # RQ's own result TTL expired before anyone looked, or it vanished.
        job.status = JobStatus.expired
        job.finished_at = datetime.now(timezone.utc)
        db.commit()
        return job

    rq_status = rq_job.get_status(refresh=True)

    if rq_status == "started" and job.status != JobStatus.started:
        job.status = JobStatus.started
        job.started_at = rq_job.started_at or datetime.now(timezone.utc)
        db.commit()
    elif rq_status == "finished":
        result = rq_job.return_value() or {}
        job.status = JobStatus.finished
        job.audio_filename = result.get("audio_filename")
        job.duration_seconds = result.get("duration_seconds")
        job.finished_at = rq_job.ended_at or datetime.now(timezone.utc)
        db.commit()
    elif rq_status == "failed":
        job.status = JobStatus.failed
        error_text = rq_job.exc_info or "synthesis failed"
        job.error_message = error_text[-500:]
        job.finished_at = rq_job.ended_at or datetime.now(timezone.utc)
        db.commit()

    return job


def get_job(db: Session, job_id: uuid.UUID) -> Job | None:
    return db.get(Job, job_id)


def delete_job(db: Session, job: Job) -> None:
    """Removes the audio file (if any), the RQ record, and the history row."""
    try:
        os.remove(audio_path(str(job.id)))
    except FileNotFoundError:
        pass

    try:
        RQJob.fetch(str(job.id), connection=redis_conn).delete()
    except NoSuchJobError:
        pass

    db.delete(job)
    db.commit()
