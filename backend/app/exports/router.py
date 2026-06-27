from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.auth.models import User
from app.core.database import get_db
from app.core.deps import require_permission
from app.courses.service import get_owned_course
from app.exercises.service import get_owned_exercise
from app.exports.schemas import QuestionPackageExportRequest
from app.exports.service import (
    export_course_outline_docx,
    export_exercise_docx,
    export_lesson_docx,
    export_question_package_docx,
    remove_export_file,
)
from app.lessons.service import get_owned_lesson
from app.questions.service import get_owned_question

router = APIRouter(prefix="/api/exports", tags=["exports"])
DOCX_MEDIA_TYPE = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"


@router.post("/lesson/{lesson_id}/docx")
def export_lesson(
    lesson_id: int,
    current_user: User = Depends(require_permission("lesson:export")),
    db: Session = Depends(get_db),
) -> FileResponse:
    lesson = get_owned_lesson(db, lesson_id=lesson_id, current_user=current_user)
    if lesson is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lesson not found")

    file_path = export_lesson_docx(db, lesson=lesson, current_user=current_user)
    try:
        db.commit()
    except Exception:
        db.rollback()
        remove_export_file(file_path)
        raise
    return FileResponse(
        file_path,
        media_type=DOCX_MEDIA_TYPE,
        filename=file_path.name,
        content_disposition_type="attachment",
    )


@router.post("/exercise/{exercise_id}/docx")
def export_exercise(
    exercise_id: int,
    current_user: User = Depends(require_permission("lesson:export")),
    db: Session = Depends(get_db),
) -> FileResponse:
    exercise = get_owned_exercise(
        db,
        exercise_id=exercise_id,
        current_user=current_user,
    )
    if exercise is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Exercise not found")

    file_path = export_exercise_docx(db, exercise=exercise, current_user=current_user)
    try:
        db.commit()
    except Exception:
        db.rollback()
        remove_export_file(file_path)
        raise
    return FileResponse(
        file_path,
        media_type=DOCX_MEDIA_TYPE,
        filename=file_path.name,
        content_disposition_type="attachment",
    )


@router.post("/course/{course_id}/outline-docx")
def export_course_outline(
    course_id: int,
    current_user: User = Depends(require_permission("lesson:export")),
    db: Session = Depends(get_db),
) -> FileResponse:
    course = get_owned_course(
        db,
        course_id=course_id,
        current_user=current_user,
        include_detail=True,
    )
    if course is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Course not found")

    file_path = export_course_outline_docx(db, course=course, current_user=current_user)
    try:
        db.commit()
    except Exception:
        db.rollback()
        remove_export_file(file_path)
        raise
    return FileResponse(
        file_path,
        media_type=DOCX_MEDIA_TYPE,
        filename=file_path.name,
        content_disposition_type="attachment",
    )


@router.post("/questions/docx")
def export_question_package(
    payload: QuestionPackageExportRequest,
    current_user: User = Depends(require_permission("lesson:export")),
    db: Session = Depends(get_db),
) -> FileResponse:
    questions = []
    for question_id in payload.question_ids:
        question = get_owned_question(
            db,
            question_id=question_id,
            current_user=current_user,
        )
        if question is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Question not found",
            )
        questions.append(question)

    file_path = export_question_package_docx(
        db,
        questions=questions,
        current_user=current_user,
    )
    try:
        db.commit()
    except Exception:
        db.rollback()
        remove_export_file(file_path)
        raise
    return FileResponse(
        file_path,
        media_type=DOCX_MEDIA_TYPE,
        filename=file_path.name,
        content_disposition_type="attachment",
    )
