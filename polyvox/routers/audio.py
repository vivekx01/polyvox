import os

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from polyvox.auth.dependencies import Principal, get_current_principal, require_job_access
from polyvox.db.base import get_db
from polyvox.services.jobs import get_job
from polyvox.storage.paths import audio_path, parse_job_id_from_filename

router = APIRouter()


@router.get("/audio/{filename}")
def get_audio(
    filename: str,
    principal: Principal = Depends(get_current_principal),
    db: Session = Depends(get_db),
):
    job_id = parse_job_id_from_filename(filename)
    if job_id is None:
        raise HTTPException(status_code=404, detail="Not found")

    job = get_job(db, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Not found")
    require_job_access(job, principal)

    if job.audio_expired_at is not None:
        raise HTTPException(status_code=410, detail="Audio has expired")

    path = audio_path(str(job_id))
    if not os.path.isfile(path):
        raise HTTPException(status_code=410, detail="Audio has expired")

    # Inline disposition so it streams straight into an <audio> player;
    # the UI's Download link adds its own `download` attribute when a
    # forced save is actually wanted.
    return FileResponse(path, media_type="audio/wav", filename=filename, content_disposition_type="inline")
