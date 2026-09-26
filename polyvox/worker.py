import logging

from rq import SimpleWorker

from polyvox.queue.rq_setup import queue, redis_conn
from polyvox.tts.engine import get_engine

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("polyvox.worker")


def main() -> None:
    logger.info("Loading Supertonic model (this can take a while on first run)...")
    get_engine()
    logger.info("Model loaded. Listening for jobs on queue '%s'.", queue.name)

    worker = SimpleWorker([queue], connection=redis_conn)
    worker.work(with_scheduler=False)


if __name__ == "__main__":
    main()
