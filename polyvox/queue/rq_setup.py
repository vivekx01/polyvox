import redis
from rq import Queue

from polyvox.config import settings

redis_conn = redis.from_url(settings.redis_url)
queue = Queue(settings.rq_queue_name, connection=redis_conn)


def enqueue_job(job_id: str, text: str, lang: str, voice: str, speed: float, steps: int):
    return queue.enqueue(
        "polyvox.tts.tasks.run_tts_job",
        job_id=job_id,
        args=(job_id, text, lang, voice, speed, steps),
        job_timeout=settings.rq_job_timeout_seconds,
        result_ttl=settings.rq_result_ttl_seconds,
        failure_ttl=settings.rq_failure_ttl_seconds,
    )
