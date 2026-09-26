import os

from polyvox.config import settings
from polyvox.storage.paths import audio_path
from polyvox.tts.engine import get_engine


def run_tts_job(job_id: str, text: str, lang: str, voice: str, speed: float, steps: int) -> dict:
    engine = get_engine()
    wav, duration_seconds = engine.synthesize(text, lang=lang, voice=voice, speed=speed, steps=steps)

    os.makedirs(settings.audio_storage_dir, exist_ok=True)
    path = audio_path(job_id)
    engine.save(wav, path)

    return {
        "audio_filename": os.path.basename(path),
        "duration_seconds": duration_seconds,
        "char_count": len(text),
    }
