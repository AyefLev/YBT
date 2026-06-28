from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth.models import User
from app.core.database import get_db
from app.core.deps import require_any_permission, require_permission
from app.lessons.models import Lesson, LessonVersion
from app.lessons.schemas import (
    LessonCreateRequest,
    LessonGenerateRequest,
    LessonGenerateResponse,
    LessonRead,
    LessonRestoreRequest,
    LessonVersionRead,
)
from app.lessons.service import (
    create_lesson,
    generate_lesson,
    get_owned_lesson,
    lesson_material_ids,
    list_lessons,
    list_versions,
    restore_version,
)

router = APIRouter(prefix="/api/lessons", tags=["lessons"])


def lesson_to_read(lesson: Lesson, db: Session) -> LessonRead:
    owner = db.get(User, lesson.owner_id)
    return LessonRead(
        id=lesson.id,
        owner_id=lesson.owner_id,
        owner_name=owner.display_name if owner else "",
        owner_username=owner.username if owner else "",
        course_id=lesson.course_id,
        chapter_id=lesson.chapter_id,
        session_id=lesson.session_id,
        knowledge_point_id=lesson.knowledge_point_id,
        title=lesson.title,
        subject=lesson.subject,
        chapter=lesson.chapter,
        stage=lesson.stage,
        duration_minutes=lesson.duration_minutes,
        student_level=lesson.student_level,
        current_content=lesson.current_content,
        material_ids=lesson_material_ids(lesson),
        prompt_template=lesson.prompt_template,
        output_format=lesson.output_format,
        compliance_level=lesson.compliance_level,
        review_status=lesson.review_status,
        reviewer_id=lesson.reviewer_id,
        review_comment=lesson.review_comment,
        reviewed_at=lesson.reviewed_at,
        created_at=lesson.created_at,
        updated_at=lesson.updated_at,
    )


def version_to_read(version: LessonVersion) -> LessonVersionRead:
    return LessonVersionRead(
        id=version.id,
        lesson_id=version.lesson_id,
        version_no=version.version_no,
        content=version.content,
        change_note=version.change_note,
        created_at=version.created_at,
    )


def _owned_lesson_or_404(
    db: Session,
    lesson_id: int,
    current_user: User,
) -> Lesson:
    lesson = get_owned_lesson(db, lesson_id=lesson_id, current_user=current_user)
    if lesson is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lesson not found")
    return lesson


@router.post("/generate", response_model=LessonGenerateResponse)
def generate(
    payload: LessonGenerateRequest,
    current_user: User = Depends(require_permission("lesson:create")),
    db: Session = Depends(get_db),
) -> LessonGenerateResponse:
    response = generate_lesson(db, payload=payload, current_user=current_user)
    db.commit()
    return response


@router.post("", response_model=LessonRead, status_code=status.HTTP_201_CREATED)
def create(
    payload: LessonCreateRequest,
    current_user: User = Depends(require_permission("lesson:create")),
    db: Session = Depends(get_db),
) -> LessonRead:
    lesson = create_lesson(db, payload=payload, current_user=current_user)
    response = lesson_to_read(lesson, db)
    db.commit()
    return response


@router.get("", response_model=list[LessonRead])
def list_current_user_lessons(
    current_user: User = Depends(require_any_permission("lesson:create", "lesson:view_all")),
    db: Session = Depends(get_db),
) -> list[LessonRead]:
    return [lesson_to_read(lesson, db) for lesson in list_lessons(db, current_user=current_user)]


@router.get("/{lesson_id}", response_model=LessonRead)
def get_lesson(
    lesson_id: int,
    current_user: User = Depends(require_any_permission("lesson:create", "lesson:view_all")),
    db: Session = Depends(get_db),
) -> LessonRead:
    lesson = _owned_lesson_or_404(db, lesson_id, current_user)
    return lesson_to_read(lesson, db)


@router.get("/{lesson_id}/versions", response_model=list[LessonVersionRead])
def get_versions(
    lesson_id: int,
    current_user: User = Depends(require_any_permission("lesson:create", "lesson:view_all")),
    db: Session = Depends(get_db),
) -> list[LessonVersionRead]:
    lesson = _owned_lesson_or_404(db, lesson_id, current_user)
    return [version_to_read(version) for version in list_versions(db, lesson=lesson)]


@router.post("/{lesson_id}/restore-version", response_model=LessonRead)
def restore_lesson_version(
    lesson_id: int,
    payload: LessonRestoreRequest,
    current_user: User = Depends(require_permission("lesson:create")),
    db: Session = Depends(get_db),
) -> LessonRead:
    lesson = _owned_lesson_or_404(db, lesson_id, current_user)
    restored = restore_version(db, lesson=lesson, version_id=payload.version_id)
    if restored is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Version not found")

    response = lesson_to_read(restored, db)
    db.commit()
    return response


@router.post("/{lesson_id}/submit-review", response_model=LessonRead)
def submit_lesson_review(
    lesson_id: int,
    current_user: User = Depends(require_permission("lesson:create")),
    db: Session = Depends(get_db),
) -> LessonRead:
    from app.reviews.service import submit_lesson_for_review

    lesson = submit_lesson_for_review(
        db,
        lesson=_owned_lesson_or_404(db, lesson_id, current_user),
    )
    response = lesson_to_read(lesson, db)
    db.commit()
    return response
