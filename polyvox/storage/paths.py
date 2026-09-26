import os
import uuid

from polyvox.config import settings


def audio_path(job_id: str) -> str:
    return os.path.join(settings.audio_storage_dir, f"{job_id}.wav")


def audio_filename_for(job_id: uuid.UUID) -> str:
    return f"{job_id}.wav"


def parse_job_id_from_filename(filename: str) -> uuid.UUID | None:
    """Guards against path traversal: only accepts `<uuid>.wav` exactly."""
    if not filename.endswith(".wav"):
        return None
    stem = filename[: -len(".wav")]
    try:
        return uuid.UUID(stem)
    except ValueError:
        return None
