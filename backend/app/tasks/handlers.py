from __future__ import annotations

from collections.abc import Callable
from typing import Any


TaskHandler = Callable[[dict[str, Any]], None]


def handle_material_parse(payload: dict[str, Any]) -> None:
    from app.materials.service import parse_material_job

    material_id = int(payload["material_id"])
    parse_material_job(material_id)


def handle_material_index_vectors(payload: dict[str, Any]) -> None:
    from app.materials.service import index_material_vectors_job

    material_id = int(payload["material_id"])
    index_material_vectors_job(material_id)


def handle_presentation_generate(payload: dict[str, Any]) -> None:
    from datetime import datetime, timezone

    from app.core.database import get_session_local
    from app.logs.models import JobLog

    lesson_id = int(payload["lesson_id"])
    requested_by = int(payload.get("requested_by") or 0) or None
    session_local = get_session_local()
    with session_local() as db:
        now = datetime.now(timezone.utc)
        db.add(
            JobLog(
                job_type="presentation_generate",
                status="skipped",
                resource_type="lesson",
                resource_id=lesson_id,
                user_id=requested_by,
                detail="PPT generation endpoint is reserved; renderer is not implemented yet.",
                started_at=now,
                finished_at=now,
                duration_ms=0,
            )
        )
        db.commit()


TASK_HANDLERS: dict[str, TaskHandler] = {
    "material.parse": handle_material_parse,
    "material.index_vectors": handle_material_index_vectors,
    "presentation.generate": handle_presentation_generate,
}


def dispatch_task(task_type: str, payload: dict[str, Any]) -> None:
    handler = TASK_HANDLERS.get(task_type)
    if handler is None:
        raise RuntimeError(f"Unsupported task type: {task_type}")
    handler(payload)
