import asyncio
import logging
import os
import time
from datetime import datetime, timedelta, timezone

from polyvox.config import settings
from polyvox.db.base import SessionLocal
from polyvox.db.models import Job, JobStatus
from polyvox.services.jobs import sync_job_from_rq

logger = logging.getLogger("polyvox.cleanup")

# Stop deleting once back under this fraction of the cap, so we don't
# re-trigger eviction on every single pass right at the boundary.
SIZE_CAP_HYSTERESIS = 0.9

# Only reconcile jobs created within this window; anything older that's
# still "queued"/"started" is presumed stuck and left for manual inspection.
RECONCILE_WINDOW = timedelta(hours=24)


def _list_audio_files() -> list[tuple[str, float, int]]:
    """Returns (path, mtime, size) for every file in the audio storage dir."""
    directory = settings.audio_storage_dir
    if not os.path.isdir(directory):
        return []
    entries = []
    for name in os.listdir(directory):
        path = os.path.join(directory, name)
        try:
            stat = os.stat(path)
        except FileNotFoundError:
            continue
        entries.append((path, stat.st_mtime, stat.st_size))
    return entries


def _stamp_expired(db, job_id_stem: str) -> None:
    try:
        job = db.get(Job, job_id_stem)
    except Exception:
        job = None
    if job is not None and job.audio_expired_at is None:
        job.audio_expired_at = datetime.now(timezone.utc)
        db.commit()


def sweep_expired(db) -> None:
    cutoff = time.time() - settings.audio_ttl_seconds
    for path, mtime, _size in _list_audio_files():
        if mtime < cutoff:
            stem = os.path.splitext(os.path.basename(path))[0]
            try:
                os.remove(path)
            except FileNotFoundError:
                pass
            _stamp_expired(db, stem)


def enforce_size_cap(db) -> None:
    entries = _list_audio_files()
    total_size = sum(size for _, _, size in entries)
    if total_size <= settings.audio_storage_max_bytes:
        return

    target_size = int(settings.audio_storage_max_bytes * SIZE_CAP_HYSTERESIS)
    for path, _mtime, size in sorted(entries, key=lambda e: e[1]):
        if total_size <= target_size:
            break
        stem = os.path.splitext(os.path.basename(path))[0]
        try:
            os.remove(path)
        except FileNotFoundError:
            continue
        total_size -= size
        _stamp_expired(db, stem)


def reconcile_pending_jobs(db) -> None:
    cutoff = datetime.now(timezone.utc) - RECONCILE_WINDOW
    pending = (
        db.query(Job)
        .filter(Job.status.in_([JobStatus.queued, JobStatus.started]))
        .filter(Job.created_at > cutoff)
        .all()
    )
    for job in pending:
        sync_job_from_rq(db, job)


def run_cleanup_pass() -> None:
    db = SessionLocal()
    try:
        sweep_expired(db)
        enforce_size_cap(db)
        reconcile_pending_jobs(db)
    except Exception:
        logger.exception("Cleanup pass failed")
    finally:
        db.close()


async def cleanup_loop() -> None:
    while True:
        await asyncio.to_thread(run_cleanup_pass)
        await asyncio.sleep(settings.audio_cleanup_interval_seconds)
