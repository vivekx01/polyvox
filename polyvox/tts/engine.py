"""TTS engine wrapper. Only ever imported/used inside the `worker` process —
the `web` process never loads the ONNX model.
"""

import threading
from functools import lru_cache

from supertonic import TTS

from polyvox.config import settings

_engine: "TTSEngine | None" = None
_engine_lock = threading.Lock()


class TTSEngine:
    def __init__(self) -> None:
        self._tts = TTS(
            model=settings.supertonic_model,
            auto_download=True,
            intra_op_num_threads=settings.onnx_threads,
        )

    @lru_cache(maxsize=32)
    def _voice_style(self, voice_name: str):
        return self._tts.get_voice_style(voice_name=voice_name)

    def synthesize(self, text: str, lang: str, voice: str, speed: float, steps: int):
        style = self._voice_style(voice)
        wav, duration = self._tts.synthesize(
            text,
            voice_style=style,
            total_steps=steps,
            speed=speed,
            lang=lang,
            silence_duration=settings.chunk_silence_seconds,
        )
        return wav, float(duration[0]) if hasattr(duration, "__getitem__") else float(duration)

    def save(self, wav, path: str) -> None:
        self._tts.save_audio(wav, path)


def get_engine() -> TTSEngine:
    global _engine
    if _engine is None:
        with _engine_lock:
            if _engine is None:
                _engine = TTSEngine()
    return _engine
