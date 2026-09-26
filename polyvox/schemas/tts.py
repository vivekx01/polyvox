from datetime import datetime

from pydantic import BaseModel, Field, field_validator
from supertonic.config import AVAILABLE_LANGUAGES, MAX_SPEED, MIN_SPEED

from polyvox.config import settings
from polyvox.tts.languages import VOICE_IDS


class JobCreateRequest(BaseModel):
    text: str
    lang: str = Field(default=settings.supertonic_default_lang)
    voice: str = Field(default=settings.supertonic_default_voice)
    speed: float = Field(default=1.0)
    steps: int = Field(default=settings.supertonic_default_steps, ge=1, le=32)

    @field_validator("text")
    @classmethod
    def validate_text(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("text must not be empty")
        if len(v) > settings.max_text_chars:
            raise ValueError(f"text must be at most {settings.max_text_chars} characters")
        return v

    @field_validator("lang")
    @classmethod
    def validate_lang(cls, v: str) -> str:
        if v not in AVAILABLE_LANGUAGES:
            raise ValueError(f"unsupported lang '{v}'; valid: {', '.join(AVAILABLE_LANGUAGES)}")
        return v

    @field_validator("voice")
    @classmethod
    def validate_voice(cls, v: str) -> str:
        if v not in VOICE_IDS:
            raise ValueError(f"unsupported voice '{v}'; valid: {', '.join(VOICE_IDS)}")
        return v

    @field_validator("speed")
    @classmethod
    def validate_speed(cls, v: float) -> float:
        if not (MIN_SPEED <= v <= MAX_SPEED):
            raise ValueError(f"speed must be between {MIN_SPEED} and {MAX_SPEED}")
        return v


class JobCreateResponse(BaseModel):
    job_id: str
    status: str
    created_at: datetime


class JobStatusResponse(BaseModel):
    job_id: str
    status: str
    lang: str
    voice: str
    char_count: int
    audio_url: str | None = None
    duration_seconds: float | None = None
    error: str | None = None
    created_at: datetime
    finished_at: datetime | None = None


class LanguageOut(BaseModel):
    code: str
    name: str


class VoiceOut(BaseModel):
    id: str
    label: str
