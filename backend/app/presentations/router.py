from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth.models import User
from app.core.database import get_db
from app.core.deps import require_permission
from app.lessons.service import get_owned_lesson
from app.presentations.schemas import (
    PresentationGenerateRequest,
    PresentationGenerateResponse,
)
from app.tasks.queue import enqueue_task

router = APIRouter(prefix="/api/presentations", tags=["presentations"])


@router.post("/lesson/{lesson_id}/generate", response_model=PresentationGenerateResponse)
def generate_lesson_presentation(
    lesson_id: int,
    payload: PresentationGenerateRequest,
    current_user: User = Depends(require_permission("lesson:create")),
    db: Session = Depends(get_db),
) -> PresentationGenerateResponse:
    lesson = get_owned_lesson(db, lesson_id=lesson_id, current_user=current_user)
    if lesson is None or lesson.owner_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lesson not found")

    queued = enqueue_task(
        "presentation.generate",
        {
            "lesson_id": lesson.id,
            "template_id": payload.template_id,
            "style": payload.style,
            "include_exercises": payload.include_exercises,
            "requested_by": current_user.id,
        },
        queue="presentations",
    )
    return PresentationGenerateResponse(
        lesson_id=lesson.id,
        status="queued" if queued else "not_configured",
        queued=queued,
        message=(
            "PPT generation task queued."
            if queued
            else "Presentation worker handler is reserved but not implemented yet."
        ),
    )
