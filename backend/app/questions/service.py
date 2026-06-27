import json

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.models import User
from app.courses.models import Chapter, Course, KnowledgePoint, LessonSession
from app.exercises.models import Exercise
from app.materials.models import Material
from app.questions.models import QuestionBankItem
from app.questions.schemas import (
    QuestionCreateRequest,
    QuestionRead,
    QuestionUpdateRequest,
)


def encode_list(values: list[str]) -> str:
    cleaned = [value.strip() for value in values if value.strip()]
    return json.dumps(cleaned, ensure_ascii=False)


def decode_list(value: str | None) -> list[str]:
    if not value:
        return []
    try:
        decoded = json.loads(value)
    except json.JSONDecodeError:
        return []
    if not isinstance(decoded, list):
        return []
    return [str(item) for item in decoded if str(item).strip()]


def question_to_read(question: QuestionBankItem, *, db: Session | None = None) -> QuestionRead:
    owner = db.get(User, question.owner_id) if db is not None else None
    return QuestionRead(
        id=question.id,
        owner_id=question.owner_id,
        owner_name=owner.display_name if owner else "",
        owner_username=owner.username if owner else "",
        course_id=question.course_id,
        chapter_id=question.chapter_id,
        session_id=question.session_id,
        knowledge_point_id=question.knowledge_point_id,
        source_exercise_id=question.source_exercise_id,
        source_material_id=question.source_material_id,
        title=question.title,
        subject=question.subject,
        question_type=question.question_type,
        difficulty=question.difficulty,
        stem=question.stem,
        options=decode_list(question.options_json),
        answer=question.answer,
        analysis=question.analysis,
        tags=decode_list(question.tags_json),
        status=question.status,
        reviewer_id=question.reviewer_id,
        review_comment=question.review_comment,
        reviewed_at=question.reviewed_at,
        created_at=question.created_at,
        updated_at=question.updated_at,
    )


def list_questions(
    db: Session,
    *,
    current_user: User,
    subject: str | None = None,
    difficulty: str | None = None,
    status: str | None = None,
) -> list[QuestionBankItem]:
    query = select(QuestionBankItem)
    if "question:view_all" not in current_user.permission_codes:
        query = query.where(QuestionBankItem.owner_id == current_user.id)
    if subject:
        query = query.where(QuestionBankItem.subject == subject)
    if difficulty:
        query = query.where(QuestionBankItem.difficulty == difficulty)
    if status:
        query = query.where(QuestionBankItem.status == status)

    return list(
        db.scalars(
            query.order_by(QuestionBankItem.updated_at.desc(), QuestionBankItem.id.desc())
        ).all()
    )


def get_owned_question(
    db: Session,
    *,
    question_id: int,
    current_user: User,
) -> QuestionBankItem | None:
    query = select(QuestionBankItem).where(QuestionBankItem.id == question_id)
    if "question:view_all" not in current_user.permission_codes:
        query = query.where(QuestionBankItem.owner_id == current_user.id)
    return db.scalar(query)


def create_question(
    db: Session,
    *,
    payload: QuestionCreateRequest,
    current_user: User,
) -> QuestionBankItem:
    _validate_owned_links(db, payload=payload, current_user=current_user)
    question = QuestionBankItem(
        owner_id=current_user.id,
        course_id=payload.course_id,
        chapter_id=payload.chapter_id,
        session_id=payload.session_id,
        knowledge_point_id=payload.knowledge_point_id,
        source_exercise_id=payload.source_exercise_id,
        source_material_id=payload.source_material_id,
        title=payload.title,
        subject=payload.subject,
        question_type=payload.question_type,
        difficulty=payload.difficulty,
        stem=payload.stem,
        options_json=encode_list(payload.options),
        answer=payload.answer,
        analysis=payload.analysis,
        tags_json=encode_list(payload.tags),
        status="draft",
    )
    db.add(question)
    db.flush()
    return question


def update_question(
    db: Session,
    *,
    question: QuestionBankItem,
    payload: QuestionUpdateRequest,
) -> QuestionBankItem:
    data = payload.model_dump(exclude_unset=True)
    if "options" in data:
        question.options_json = encode_list(data.pop("options") or [])
    if "tags" in data:
        question.tags_json = encode_list(data.pop("tags") or [])
    for field_name, value in data.items():
        setattr(question, field_name, value)
    db.flush()
    return question


def _validate_owned_links(
    db: Session,
    *,
    payload: QuestionCreateRequest,
    current_user: User,
) -> None:
    course_id = payload.course_id

    if course_id is not None:
        course_query = select(Course).where(Course.id == course_id)
        if "course:manage_all" not in current_user.permission_codes:
            course_query = course_query.where(Course.owner_id == current_user.id)
        course = db.scalar(course_query)
        if course is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Course not found",
            )

    if payload.chapter_id is not None:
        chapter_query = (
            select(Chapter)
            .join(Course, Chapter.course_id == Course.id)
            .where(Chapter.id == payload.chapter_id)
        )
        if "course:manage_all" not in current_user.permission_codes:
            chapter_query = chapter_query.where(Course.owner_id == current_user.id)
        chapter = db.scalar(chapter_query)
        if chapter is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Chapter not found",
            )
        course_id = _ensure_same_course(course_id, chapter.course_id)

    if payload.session_id is not None:
        session_query = (
            select(LessonSession)
            .join(Course, LessonSession.course_id == Course.id)
            .where(LessonSession.id == payload.session_id)
        )
        if "course:manage_all" not in current_user.permission_codes:
            session_query = session_query.where(Course.owner_id == current_user.id)
        session = db.scalar(session_query)
        if session is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Session not found",
            )
        course_id = _ensure_same_course(course_id, session.course_id)
        if payload.chapter_id is not None and session.chapter_id != payload.chapter_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Session does not belong to chapter",
            )

    if payload.knowledge_point_id is not None:
        knowledge_point_query = (
            select(KnowledgePoint)
            .join(Course, KnowledgePoint.course_id == Course.id)
            .where(KnowledgePoint.id == payload.knowledge_point_id)
        )
        if "course:manage_all" not in current_user.permission_codes:
            knowledge_point_query = knowledge_point_query.where(Course.owner_id == current_user.id)
        knowledge_point = db.scalar(knowledge_point_query)
        if knowledge_point is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Knowledge point not found",
            )
        _ensure_same_course(course_id, knowledge_point.course_id)

    if payload.source_exercise_id is not None:
        exercise_query = select(Exercise).where(Exercise.id == payload.source_exercise_id)
        if "exercise:view_all" not in current_user.permission_codes:
            exercise_query = exercise_query.where(Exercise.owner_id == current_user.id)
        exercise = db.scalar(exercise_query)
        if exercise is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Exercise not found",
            )

    if payload.source_material_id is not None:
        material_query = select(Material).where(Material.id == payload.source_material_id)
        if "material:view_all" not in current_user.permission_codes:
            material_query = material_query.where(
                (Material.uploader_id == current_user.id)
                | (Material.resource_scope == "public")
            )
        material = db.scalar(material_query)
        if material is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Material not found",
            )


def _ensure_same_course(current_course_id: int | None, linked_course_id: int) -> int:
    if current_course_id is not None and current_course_id != linked_course_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Linked resources must belong to the same course",
        )
    return linked_course_id
