from __future__ import annotations

import json
import logging
import time
from typing import Any

from app.auth.service import seed_bootstrap_admin, seed_default_auth_data
from app.core.config import get_settings
from app.core.database import get_session_local, init_db
from app.tasks.handlers import dispatch_task
from app.tasks.queue import worker_queue_keys

logger = logging.getLogger("yanbeitong.worker")


def bootstrap_worker() -> None:
    settings = get_settings()
    settings.validate_jwt_secret()
    init_db(settings.database_url)
    session_local = get_session_local(settings.database_url)
    with session_local() as db:
        seed_default_auth_data(db)
        seed_bootstrap_admin(db, settings)


def run_worker() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    settings = get_settings()
    if not settings.redis_url:
        raise RuntimeError("Worker requires REDIS_URL.")

    from redis import Redis

    bootstrap_worker()
    client = Redis.from_url(settings.redis_url, decode_responses=True)
    queues = worker_queue_keys(settings)
    logger.info("Worker started; listening queues: %s", ", ".join(queues))

    while True:
        item = client.blpop(queues, timeout=max(1, int(settings.task_worker_poll_seconds)))
        if item is None:
            continue

        queue_name, raw_message = item
        try:
            message = _decode_message(raw_message)
            task_type = str(message["type"])
            payload = message.get("payload") or {}
            if not isinstance(payload, dict):
                raise RuntimeError("Task payload must be an object.")
            logger.info("Running task %s from %s", task_type, queue_name)
            dispatch_task(task_type, payload)
            logger.info("Finished task %s", task_type)
        except Exception:
            logger.exception("Task failed from queue %s: %s", queue_name, raw_message)
            time.sleep(0.2)


def _decode_message(raw_message: str) -> dict[str, Any]:
    decoded = json.loads(raw_message)
    if not isinstance(decoded, dict):
        raise RuntimeError("Task message must be an object.")
    return decoded


if __name__ == "__main__":
    run_worker()

