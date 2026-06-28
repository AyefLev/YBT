from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.auth.models import User
from app.core.database import get_db
from app.core.deps import require_any_permission, require_permission
from app.exports.models import ExportRecord
from app.lessons.service import get_owned_lesson
from app.presentations.schemas import (
    PresentationGenerateRequest,
    PresentationGenerateResponse,
)
from app.presentations.service import generate_lesson_presentation_file

router = APIRouter(prefix="/api/presentations", tags=["presentations"])
PPTX_MEDIA_TYPE = "application/vnd.openxmlformats-officedocument.presentationml.presentation"


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

    try:
        result = generate_lesson_presentation_file(
            db,
            lesson=lesson,
            payload=payload,
            current_user=current_user,
        )
        db.commit()
    except Exception:
        db.rollback()
        raise
    return result


@router.get("/exports/{export_id}/pptx")
def download_generated_presentation(
    export_id: int,
    current_user: User = Depends(require_any_permission("lesson:create", "lesson:export", "lesson:view_all")),
    db: Session = Depends(get_db),
) -> FileResponse:
    record = db.get(ExportRecord, export_id)
    if record is None or record.resource_type != "presentation":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Presentation export not found")
    if record.exported_by != current_user.id and "lesson:view_all" not in current_user.permission_codes:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Presentation export not found")

    file_path = Path(record.file_path)
    if not file_path.exists():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Presentation file not found")

    return FileResponse(
        file_path,
        media_type=PPTX_MEDIA_TYPE,
        filename=file_path.name,
        content_disposition_type="attachment",
    )
