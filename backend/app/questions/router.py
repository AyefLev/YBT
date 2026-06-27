from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from app.auth.models import User
from app.core.database import get_db
from app.core.deps import get_current_user, require_permission
from app.questions.models import QuestionBankItem
from app.questions.schemas import (
    QuestionCreateRequest,
    QuestionRead,
    QuestionUpdateRequest,
)
from app.questions.service import (
    create_question,
    get_owned_question,
    list_questions,
    question_to_read,
    update_question,
)

router = APIRouter(prefix="/api/questions", tags=["questions"])


def question_or_404(
    db: Session,
    question_id: int,
    current_user: User,
) -> QuestionBankItem:
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
    return question


@router.get("", response_model=list[QuestionRead])
def list_current_questions(
    subject: str | None = None,
    difficulty: str | None = None,
    status: str | None = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[QuestionRead]:
    return [
        question_to_read(question, db=db)
        for question in list_questions(
            db,
            current_user=current_user,
            subject=subject,
            difficulty=difficulty,
            status=status,
        )
    ]


@router.post("", response_model=QuestionRead, status_code=status.HTTP_201_CREATED)
def create_current_question(
    payload: QuestionCreateRequest,
    current_user: User = Depends(require_permission("exercise:create")),
    db: Session = Depends(get_db),
) -> QuestionRead:
    question = create_question(db, payload=payload, current_user=current_user)
    response = question_to_read(question, db=db)
    db.commit()
    return response


@router.get("/{question_id}", response_model=QuestionRead)
def get_question(
    question_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> QuestionRead:
    return question_to_read(question_or_404(db, question_id, current_user), db=db)


@router.patch("/{question_id}", response_model=QuestionRead)
def patch_question(
    question_id: int,
    payload: QuestionUpdateRequest,
    current_user: User = Depends(require_permission("exercise:create")),
    db: Session = Depends(get_db),
) -> QuestionRead:
    question = update_question(
        db,
        question=question_or_404(db, question_id, current_user),
        payload=payload,
    )
    response = question_to_read(question, db=db)
    db.commit()
    return response


@router.delete("/{question_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_question(
    question_id: int,
    current_user: User = Depends(require_permission("exercise:create")),
    db: Session = Depends(get_db),
) -> Response:
    db.delete(question_or_404(db, question_id, current_user))
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/{question_id}/submit-review", response_model=QuestionRead)
def submit_question_review(
    question_id: int,
    current_user: User = Depends(require_permission("exercise:create")),
    db: Session = Depends(get_db),
) -> QuestionRead:
    from app.reviews.service import submit_question_for_review

    question = submit_question_for_review(
        db,
        question=question_or_404(db, question_id, current_user),
    )
    response = question_to_read(question, db=db)
    db.commit()
    return response
