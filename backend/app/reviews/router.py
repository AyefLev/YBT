from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.auth.models import User
from app.core.database import get_db
from app.core.deps import require_permission
from app.lessons.router import lesson_to_read
from app.questions.service import question_to_read
from app.reviews.schemas import ReviewActionRequest, ReviewableRead
from app.reviews.service import (
    approve_resource,
    list_pending_reviews,
    reject_resource,
    return_resource_to_draft,
)

router = APIRouter(prefix="/api/reviews", tags=["reviews"])


@router.get("/pending", response_model=list[ReviewableRead])
def pending_reviews(
    current_user: User = Depends(require_permission("review:manage")),
    db: Session = Depends(get_db),
) -> list[ReviewableRead]:
    _ = current_user
    return list_pending_reviews(db)


@router.post("/{resource_type}/{resource_id}/approve")
def approve(
    resource_type: str,
    resource_id: int,
    payload: ReviewActionRequest,
    current_user: User = Depends(require_permission("review:manage")),
    db: Session = Depends(get_db),
):
    resource = approve_resource(
        db,
        resource_type=resource_type,
        resource_id=resource_id,
        reviewer=current_user,
        comment=payload.comment,
    )
    db.commit()
    if resource_type == "question":
        return question_to_read(resource, db=db)
    return lesson_to_read(resource, db)


@router.post("/{resource_type}/{resource_id}/reject")
def reject(
    resource_type: str,
    resource_id: int,
    payload: ReviewActionRequest,
    current_user: User = Depends(require_permission("review:manage")),
    db: Session = Depends(get_db),
):
    resource = reject_resource(
        db,
        resource_type=resource_type,
        resource_id=resource_id,
        reviewer=current_user,
        comment=payload.comment,
    )
    db.commit()
    if resource_type == "question":
        return question_to_read(resource, db=db)
    return lesson_to_read(resource, db)


@router.post("/{resource_type}/{resource_id}/return-draft")
def return_draft(
    resource_type: str,
    resource_id: int,
    current_user: User = Depends(require_permission("exercise:create")),
    db: Session = Depends(get_db),
):
    resource = return_resource_to_draft(
        db,
        resource_type=resource_type,
        resource_id=resource_id,
        current_user=current_user,
    )
    db.commit()
    if resource_type == "question":
        return question_to_read(resource, db=db)
    return lesson_to_read(resource, db)
