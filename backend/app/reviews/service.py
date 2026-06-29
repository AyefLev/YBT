from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.models import User
from app.lessons.models import Lesson
from app.logs.models import OperationLog
from app.questions.models import QuestionBankItem
from app.questions.service import decode_list
from app.reviews.schemas import ReviewableRead

REVIEW_DRAFT_STATUSES = {"draft", "rejected"}


def submit_question_for_review(
    db: Session,
    *,
    question: QuestionBankItem,
) -> QuestionBankItem:
    _require_submittable(question.status, "Question")
    question.status = "pending_review"
    question.reviewer_id = None
    question.review_comment = ""
    question.reviewed_at = None
    db.add(
        OperationLog(
            user_id=question.owner_id,
            action="question.submit_review",
            resource="question",
            detail=str(question.id),
        )
    )
    db.flush()
    return question


def submit_lesson_for_review(db: Session, *, lesson: Lesson) -> Lesson:
    _require_submittable(lesson.review_status, "Lesson")
    lesson.review_status = "pending_review"
    lesson.reviewer_id = None
    lesson.review_comment = ""
    lesson.reviewed_at = None
    db.add(
        OperationLog(
            user_id=lesson.owner_id,
            action="lesson.submit_review",
            resource="lesson",
            detail=str(lesson.id),
        )
    )
    db.flush()
    return lesson


def list_pending_reviews(db: Session) -> list[ReviewableRead]:
    lessons = db.scalars(
        select(Lesson).where(Lesson.review_status == "pending_review")
    ).all()
    questions = db.scalars(
        select(QuestionBankItem).where(QuestionBankItem.status == "pending_review")
    ).all()

    items = [
        ReviewableRead(
            resource_type="lesson",
            resource_id=lesson.id,
            title=lesson.title,
            owner_id=lesson.owner_id,
            owner_name=_owner_name(db, lesson.owner_id),
            owner_username=_owner_username(db, lesson.owner_id),
            status=lesson.review_status,
            subject=lesson.subject,
            detail=_lesson_review_detail(lesson),
            created_at=lesson.created_at,
            updated_at=lesson.updated_at,
        )
        for lesson in lessons
    ]
    items.extend(
        ReviewableRead(
            resource_type="question",
            resource_id=question.id,
            title=question.title,
            owner_id=question.owner_id,
            owner_name=_owner_name(db, question.owner_id),
            owner_username=_owner_username(db, question.owner_id),
            status=question.status,
            subject=question.subject,
            detail=_question_review_detail(question),
            created_at=question.created_at,
            updated_at=question.updated_at,
        )
        for question in questions
    )
    return sorted(items, key=lambda item: (item.updated_at, item.resource_id), reverse=True)


def _owner_name(db: Session, owner_id: int) -> str:
    owner = db.get(User, owner_id)
    return owner.display_name if owner else ""


def _owner_username(db: Session, owner_id: int) -> str:
    owner = db.get(User, owner_id)
    return owner.username if owner else ""


def _lesson_review_detail(lesson: Lesson) -> dict[str, object]:
    return {
        "content": lesson.current_content,
        "chapter": lesson.chapter,
        "stage": lesson.stage,
        "duration_minutes": lesson.duration_minutes,
        "student_level": lesson.student_level,
        "course_id": lesson.course_id,
        "chapter_id": lesson.chapter_id,
        "session_id": lesson.session_id,
        "knowledge_point_id": lesson.knowledge_point_id,
        "compliance_level": lesson.compliance_level,
    }


def _question_review_detail(question: QuestionBankItem) -> dict[str, object]:
    return {
        "stem": question.stem,
        "options": decode_list(question.options_json),
        "answer": question.answer,
        "analysis": question.analysis,
        "tags": decode_list(question.tags_json),
        "question_type": question.question_type,
        "difficulty": question.difficulty,
        "course_id": question.course_id,
        "chapter_id": question.chapter_id,
        "session_id": question.session_id,
        "knowledge_point_id": question.knowledge_point_id,
        "source_exercise_id": question.source_exercise_id,
        "source_material_id": question.source_material_id,
    }


def approve_resource(
    db: Session,
    *,
    resource_type: str,
    resource_id: int,
    reviewer: User,
    comment: str,
):
    resource = _get_review_resource(db, resource_type, resource_id)
    _require_pending(resource, resource_type)
    _set_review_fields(resource, resource_type, "approved", reviewer.id, comment)
    db.add(
        OperationLog(
            user_id=reviewer.id,
            action=f"{resource_type}.approve",
            resource=resource_type,
            detail=str(resource_id),
        )
    )
    db.flush()
    return resource


def reject_resource(
    db: Session,
    *,
    resource_type: str,
    resource_id: int,
    reviewer: User,
    comment: str,
):
    resource = _get_review_resource(db, resource_type, resource_id)
    _require_pending(resource, resource_type)
    _set_review_fields(resource, resource_type, "rejected", reviewer.id, comment)
    db.add(
        OperationLog(
            user_id=reviewer.id,
            action=f"{resource_type}.reject",
            resource=resource_type,
            detail=str(resource_id),
        )
    )
    db.flush()
    return resource


def return_resource_to_draft(
    db: Session,
    *,
    resource_type: str,
    resource_id: int,
    current_user: User,
):
    resource = _get_review_resource(db, resource_type, resource_id)
    if resource.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Review resource not found",
        )

    current = resource.review_status if resource_type == "lesson" else resource.status
    if current != "rejected":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only rejected resources can return to draft",
        )

    if resource_type == "lesson":
        resource.review_status = "draft"
    else:
        resource.status = "draft"
    resource.reviewer_id = None
    resource.review_comment = ""
    resource.reviewed_at = None
    db.add(
        OperationLog(
            user_id=current_user.id,
            action=f"{resource_type}.return_draft",
            resource=resource_type,
            detail=str(resource_id),
        )
    )
    db.flush()
    return resource


def _require_submittable(current_status: str, label: str) -> None:
    if current_status not in REVIEW_DRAFT_STATUSES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"{label} cannot be submitted from current status",
        )


def _get_review_resource(db: Session, resource_type: str, resource_id: int):
    if resource_type == "lesson":
        resource = db.get(Lesson, resource_id)
    elif resource_type == "question":
        resource = db.get(QuestionBankItem, resource_id)
    else:
        resource = None

    if resource is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Review resource not found",
        )
    return resource


def _require_pending(resource, resource_type: str) -> None:
    current = resource.review_status if resource_type == "lesson" else resource.status
    if current != "pending_review":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Resource is not pending review",
        )


def _set_review_fields(
    resource,
    resource_type: str,
    next_status: str,
    reviewer_id: int,
    comment: str,
) -> None:
    if resource_type == "lesson":
        resource.review_status = next_status
    else:
        resource.status = next_status
    resource.reviewer_id = reviewer_id
    resource.review_comment = comment
    resource.reviewed_at = datetime.now(timezone.utc)
