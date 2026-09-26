from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    env: str = "production"
    secret_key: str = "changeme"
    session_cookie_name: str = "polyvox_session"
    session_max_age_seconds: int = 604800

    admin_email: str = "admin@example.com"
    admin_password: str = "changeme"

    database_url: str = "postgresql+psycopg://polyvox:changeme@localhost:5432/polyvox"

    redis_url: str = "redis://localhost:6379/0"
    rq_queue_name: str = "tts"
    rq_job_timeout_seconds: int = 600
    rq_result_ttl_seconds: int = 86400
    rq_failure_ttl_seconds: int = 86400

    supertonic_model: str = "supertonic-3"
    supertonic_default_voice: str = "M1"
    supertonic_default_lang: str = "en"
    supertonic_default_steps: int = 8
    onnx_threads: int = 4
    max_text_chars: int = 20000
    chunk_silence_seconds: float = 0.3

    audio_storage_dir: str = "/data/audio"
    audio_ttl_seconds: int = 1800
    audio_storage_max_bytes: int = 5 * 1024 * 1024 * 1024
    audio_cleanup_interval_seconds: int = 60

    host: str = "0.0.0.0"
    port: int = 8000
    uvicorn_workers: int = 1


settings = Settings()
