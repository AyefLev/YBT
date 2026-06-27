from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth.models import User
from app.core.database import get_db
from app.core.deps import get_current_user, require_permission
from app.exercises.models import Exercise, ExerciseVersion
from app.exercises.schemas import (
    ExerciseCreateRequest,
    ExerciseGenerateRequest,
    ExerciseGenerateResponse,
    ExerciseRead,
    ExerciseRestoreRequest,
    ExerciseVersionRead,
)
from app.exercises.service import (
    create_exercise,
    exercise_material_ids,
    generate_exercise,
    get_owned_exercise,
    list_exercises,
    list_versions,
    restore_version,
    save_exercise_to_question_bank,
)
from app.questions.schemas import QuestionRead
from app.questions.service import question_to_read

router = APIRouter(prefix="/api/exercises", tags=["exercises"])


def exercise_to_read(exercise: Exercise, db: Session) -> ExerciseRead:
    owner = db.get(User, exercise.owner_id)
    return ExerciseRead(
        id=exercise.id,
        owner_id=exercise.owner_id,
        owner_name=owner.display_name if owner else "",
        owner_username=owner.username if owner else "",
        course_id=exercise.course_id,
        chapter_id=exercise.chapter_id,
        session_id=exercise.session_id,
        knowledge_point_id=exercise.knowledge_point_id,
        lesson_id=exercise.lesson_id,
        title=exercise.title,
        subject=exercise.subject,
        knowledge_point=exercise.knowledge_point,
        question_type=exercise.question_type,
        difficulty=exercise.difficulty,
        current_content=exercise.current_content,
        material_ids=exercise_material_ids(exercise),
        prompt_template=exercise.prompt_template,
        output_format=exercise.output_format,
        compliance_level=exercise.compliance_level,
        created_at=exercise.created_at,
        updated_at=exercise.updated_at,
    )


def version_to_read(version: ExerciseVersion) -> ExerciseVersionRead:
    return ExerciseVersionRead(
        id=version.id,
        exercise_id=version.exercise_id,
        version_no=version.version_no,
        content=version.content,
        change_note=version.change_note,
        created_at=version.created_at,
    )


def _owned_exercise_or_404(
    db: Session,
    exercise_id: int,
    current_user: User,
) -> Exercise:
    exercise = get_owned_exercise(db, exercise_id=exercise_id, current_user=current_user)
    if exercise is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Exercise not found",
        )
    return exercise


@router.post("/generate", response_model=ExerciseGenerateResponse)
def generate(
    payload: ExerciseGenerateRequest,
    current_user: User = Depends(require_permission("exercise:create")),
    db: Session = Depends(get_db),
) -> ExerciseGenerateResponse:
    response = generate_exercise(db, payload=payload, current_user=current_user)
    db.commit()
    return response


@router.post("", response_model=ExerciseRead, status_code=status.HTTP_201_CREATED)
def create(
    payload: ExerciseCreateRequest,
    current_user: User = Depends(require_permission("exercise:create")),
    db: Session = Depends(get_db),
) -> ExerciseRead:
    exercise = create_exercise(db, payload=payload, current_user=current_user)
    response = exercise_to_read(exercise, db)
    db.commit()
    return response


@router.get("", response_model=list[ExerciseRead])
def list_current_user_exercises(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[ExerciseRead]:
    return [
        exercise_to_read(exercise, db)
        for exercise in list_exercises(db, current_user=current_user)
    ]


@router.get("/{exercise_id}", response_model=ExerciseRead)
def get_exercise(
    exercise_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ExerciseRead:
    exercise = _owned_exercise_or_404(db, exercise_id, current_user)
    return exercise_to_read(exercise, db)


@router.get("/{exercise_id}/versions", response_model=list[ExerciseVersionRead])
def get_versions(
    exercise_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[ExerciseVersionRead]:
    exercise = _owned_exercise_or_404(db, exercise_id, current_user)
    return [version_to_read(version) for version in list_versions(db, exercise=exercise)]


@router.post("/{exercise_id}/restore-version", response_model=ExerciseRead)
def restore_exercise_version(
    exercise_id: int,
    payload: ExerciseRestoreRequest,
    current_user: User = Depends(require_permission("exercise:create")),
    db: Session = Depends(get_db),
) -> ExerciseRead:
    exercise = _owned_exercise_or_404(db, exercise_id, current_user)
    restored = restore_version(db, exercise=exercise, version_id=payload.version_id)
    if restored is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Version not found")

    response = exercise_to_read(restored, db)
    db.commit()
    return response


@router.post(
    "/{exercise_id}/save-to-question-bank",
    response_model=list[QuestionRead],
    status_code=status.HTTP_201_CREATED,
)
def save_exercise_questions_to_bank(
    exercise_id: int,
    current_user: User = Depends(require_permission("exercise:create")),
    db: Session = Depends(get_db),
) -> list[QuestionRead]:
    exercise = _owned_exercise_or_404(db, exercise_id, current_user)
    questions = save_exercise_to_question_bank(
        db,
        exercise=exercise,
        current_user=current_user,
    )
    response = [question_to_read(question, db=db) for question in questions]
    db.commit()
    return response
