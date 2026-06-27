from __future__ import annotations

from datetime import datetime, timezone
import json
from typing import Any
from uuid import uuid4

from app.core.config import Settings, get_settings


def queue_key(queue: str, settings: Settings | None = None) -> str:
    active_settings = settings or get_settings()
    normalized_queue = queue.strip() or "default"
    return f"{active_settings.task_queue_prefix}:{normalized_queue}"


def worker_queue_names(settings: Settings | None = None) -> list[str]:
    active_settings = settings or get_settings()
    queues = [
        queue.strip()
        for queue in active_settings.task_worker_queues.split(",")
        if queue.strip()
    ]
    return queues or ["default"]


def worker_queue_keys(settings: Settings | None = None) -> list[str]:
    active_settings = settings or get_settings()
    return [queue_key(queue, active_settings) for queue in worker_queue_names(active_settings)]


def enqueue_task(
    task_type: str,
    payload: dict[str, Any],
    *,
    queue: str = "default",
) -> bool:
    settings = get_settings()
    mode = settings.task_queue_mode.lower().strip()
    if mode in {"", "inline", "thread", "local"}:
        return False
    if not settings.redis_url:
        if mode == "redis":
            raise RuntimeError("TASK_QUEUE_MODE=redis requires REDIS_URL.")
        return False

    message = {
        "id": uuid4().hex,
        "type": task_type,
        "queue": queue,
        "payload": payload,
        "queued_at": datetime.now(timezone.utc).isoformat(),
    }
    try:
        from redis import Redis

        client = Redis.from_url(settings.redis_url, decode_responses=True)
        client.rpush(queue_key(queue, settings), json.dumps(message, ensure_ascii=False))
    except Exception:
        if mode == "redis":
            raise
        return False
    return True

