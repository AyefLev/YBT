import json

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.ai.prompts import build_lesson_prompt
from app.ai.service import generate_text, review_generated_content
from app.auth.models import User
from app.compliance.service import check_content
from app.courses.models import Chapter, Course, KnowledgePoint, LessonSession, SessionLessonLink
from app.lessons.models import Lesson, LessonVersion
from app.lessons.schemas import (
    LessonCreateRequest,
    LessonGenerateRequest,
    LessonGenerateResponse,
    LessonReference,
)
from app.retrieval.service import search_chunks


def generate_lesson(
    db: Session,
    *,
    payload: LessonGenerateRequest,
    current_user: User,
) -> LessonGenerateResponse:
    references: list[LessonReference] = []
    teaching_context = _build_teaching_context(db, payload=payload, current_user=current_user)
    if payload.use_materials:
        chunks = search_chunks(
            db,
            query=f"{payload.chapter} {payload.teaching_goal}",
            top_k=5,
            material_ids=payload.material_ids,
            current_user=current_user,
        )
        references = [LessonReference.model_validate(chunk.model_dump()) for chunk in chunks]

    form = payload.model_dump()
    form["teaching_context"] = teaching_context
    if payload.web_search_enabled:
        form["web_search_note"] = "已预留网络检索接入点；当前离线演示版本不会主动访问公网。"
    prompt = build_lesson_prompt(form, [reference.content for reference in references])
    ai_result = generate_text(db, "lesson", prompt)
    review = review_generated_content(db, task_type="lesson", content=ai_result.content)
    compliance = check_content(db, "lesson", ai_result.content)

    return LessonGenerateResponse(
        content=ai_result.content,
        references=references,
        provider_status=ai_result,
        compliance=compliance,
        review=review,
    )


def create_lesson(
    db: Session,
    *,
    payload: LessonCreateRequest,
    current_user: User,
) -> Lesson:
    _validate_teaching_scope(
        db,
        current_user=current_user,
        course_id=payload.course_id,
        chapter_id=payload.chapter_id,
        session_id=payload.session_id,
        knowledge_point_id=payload.knowledge_point_id,
    )
    lesson = Lesson(
        owner_id=current_user.id,
        course_id=payload.course_id,
        chapter_id=payload.chapter_id,
        session_id=payload.session_id,
        knowledge_point_id=payload.knowledge_point_id,
        title=payload.title,
        subject=payload.subject,
        chapter=payload.chapter,
        stage=payload.stage,
        duration_minutes=payload.duration_minutes,
        student_level=payload.student_level,
        material_ids_json=_encode_ids(payload.material_ids),
        prompt_template=payload.prompt_template,
        output_format=payload.output_format,
        current_content=payload.content,
        compliance_level="unknown",
    )
    db.add(lesson)
    db.flush()

    compliance = check_content(db, "lesson", payload.content, str(lesson.id))
    lesson.compliance_level = compliance.risk_level
    add_lesson_version(
        db,
        lesson_id=lesson.id,
        content=payload.content,
        change_note=payload.change_note,
        version_no=1,
    )
    if payload.session_id is not None:
        _link_lesson_to_session(db, session_id=payload.session_id, lesson_id=lesson.id)
    return lesson


def list_lessons(db: Session, *, current_user: User) -> list[Lesson]:
    statement = select(Lesson).order_by(Lesson.created_at.desc(), Lesson.id.desc())
    if not can_view_all_lessons(current_user):
        statement = statement.where(Lesson.owner_id == current_user.id)
    return list(db.scalars(statement).all())


def get_owned_lesson(db: Session, *, lesson_id: int, current_user: User) -> Lesson | None:
    statement = select(Lesson).where(Lesson.id == lesson_id)
    if not can_view_all_lessons(current_user):
        statement = statement.where(Lesson.owner_id == current_user.id)
    return db.scalar(statement)


def can_view_all_lessons(current_user: User) -> bool:
    return "lesson:view_all" in current_user.permission_codes


def lesson_material_ids(lesson: Lesson) -> list[int]:
    return _decode_ids(lesson.material_ids_json)


def list_versions(db: Session, *, lesson: Lesson) -> list[LessonVersion]:
    return list(
        db.scalars(
            select(LessonVersion)
            .where(LessonVersion.lesson_id == lesson.id)
            .order_by(LessonVersion.version_no)
        ).all()
    )


def restore_version(
    db: Session,
    *,
    lesson: Lesson,
    version_id: int,
) -> Lesson | None:
    restored_version = db.scalar(
        select(LessonVersion).where(
            LessonVersion.id == version_id,
            LessonVersion.lesson_id == lesson.id,
        )
    )
    if restored_version is None:
        return None

    add_lesson_version(
        db,
        lesson_id=lesson.id,
        content=restored_version.content,
        change_note=f"恢复版本 {restored_version.version_no}",
    )
    lesson.current_content = restored_version.content
    compliance = check_content(db, "lesson", restored_version.content, str(lesson.id))
    lesson.compliance_level = compliance.risk_level
    db.flush()
    return lesson


def add_lesson_version(
    db: Session,
    *,
    lesson_id: int,
    content: str,
    change_note: str,
    version_no: int | None = None,
    max_retries: int = 1,
) -> LessonVersion:
    attempts = max_retries + 1 if version_no is None else 1
    last_error: IntegrityError | None = None

    for _ in range(attempts):
        try:
            with db.begin_nested():
                candidate_version_no = (
                    version_no
                    if version_no is not None
                    else _next_lesson_version_no(db, lesson_id)
                )
                version = LessonVersion(
                    lesson_id=lesson_id,
                    version_no=candidate_version_no,
                    content=content,
                    change_note=change_note,
                )
                db.add(version)
                db.flush()
            return version
        except IntegrityError as exc:
            # The nested transaction rolls back the failed insert savepoint, so
            # a concurrent duplicate version_no can be recomputed and retried.
            last_error = exc

    if last_error is not None:
        raise last_error
    raise RuntimeError("Could not create lesson version")


def _next_lesson_version_no(db: Session, lesson_id: int) -> int:
    max_version_no = db.scalar(
        select(func.max(LessonVersion.version_no)).where(
            LessonVersion.lesson_id == lesson_id,
        )
    )
    return (max_version_no or 0) + 1


def _build_teaching_context(
    db: Session,
    *,
    payload: LessonGenerateRequest,
    current_user: User,
) -> str:
    _validate_teaching_scope(
        db,
        current_user=current_user,
        course_id=payload.course_id,
        chapter_id=payload.chapter_id,
        session_id=payload.session_id,
        knowledge_point_id=payload.knowledge_point_id,
    )
    lines: list[str] = []
    if payload.course_id is not None:
        course = db.get(Course, payload.course_id)
        if course:
            lines.append(f"课程：{course.title}（{course.subject}，{course.exam_type}）")
            if course.description:
                lines.append(f"课程说明：{course.description}")
    if payload.chapter_id is not None:
        chapter = db.get(Chapter, payload.chapter_id)
        if chapter:
            lines.append(f"章节：{chapter.title}")
            if chapter.summary:
                lines.append(f"章节摘要：{chapter.summary}")
    if payload.session_id is not None:
        session = db.get(LessonSession, payload.session_id)
        if session:
            lines.append(f"课次：{session.title}，预计 {session.duration_minutes} 分钟")
            if session.teaching_goal:
                lines.append(f"课次目标：{session.teaching_goal}")
    if payload.knowledge_point_id is not None:
        point = db.get(KnowledgePoint, payload.knowledge_point_id)
        if point:
            lines.append(f"知识点：{point.name}")
            if point.description:
                lines.append(f"知识点说明：{point.description}")
    return "\n".join(lines)


def _validate_teaching_scope(
    db: Session,
    *,
    current_user: User,
    course_id: int | None,
    chapter_id: int | None,
    session_id: int | None,
    knowledge_point_id: int | None,
) -> None:
    resolved_course_id = course_id
    if course_id is not None:
        course_query = select(Course).where(Course.id == course_id)
        if (
            "course:manage_all" not in current_user.permission_codes
            and "course:view_all" not in current_user.permission_codes
        ):
            course_query = course_query.where(Course.owner_id == current_user.id)
        if db.scalar(course_query) is None:
            raise HTTPException(status_code=404, detail="Course not found")
    if chapter_id is not None:
        chapter = db.get(Chapter, chapter_id)
        if chapter is None:
            raise HTTPException(status_code=404, detail="Chapter not found")
        resolved_course_id = _ensure_same_course(resolved_course_id, chapter.course_id)
    if session_id is not None:
        session = db.get(LessonSession, session_id)
        if session is None:
            raise HTTPException(status_code=404, detail="Session not found")
        resolved_course_id = _ensure_same_course(resolved_course_id, session.course_id)
        if chapter_id is not None and session.chapter_id != chapter_id:
            raise HTTPException(status_code=400, detail="Session does not belong to chapter")
    if knowledge_point_id is not None:
        point = db.get(KnowledgePoint, knowledge_point_id)
        if point is None:
            raise HTTPException(status_code=404, detail="Knowledge point not found")
        resolved_course_id = _ensure_same_course(resolved_course_id, point.course_id)
    if resolved_course_id is not None:
        course_query = select(Course).where(Course.id == resolved_course_id)
        if (
            "course:manage_all" not in current_user.permission_codes
            and "course:view_all" not in current_user.permission_codes
        ):
            course_query = course_query.where(Course.owner_id == current_user.id)
        if db.scalar(course_query) is None:
            raise HTTPException(status_code=404, detail="Course not found")


def _link_lesson_to_session(db: Session, *, session_id: int, lesson_id: int) -> None:
    existing = db.scalar(
        select(SessionLessonLink).where(
            SessionLessonLink.session_id == session_id,
            SessionLessonLink.lesson_id == lesson_id,
        )
    )
    if existing is None:
        db.add(SessionLessonLink(session_id=session_id, lesson_id=lesson_id))
        db.flush()


def _ensure_same_course(current_course_id: int | None, linked_course_id: int) -> int:
    if current_course_id is not None and current_course_id != linked_course_id:
        raise HTTPException(status_code=400, detail="Linked resources must belong to the same course")
    return linked_course_id


def _encode_ids(values: list[int]) -> str:
    return json.dumps(sorted({int(value) for value in values if int(value) > 0}))


def _decode_ids(value: str | None) -> list[int]:
    if not value:
        return []
    try:
        decoded = json.loads(value)
    except json.JSONDecodeError:
        return []
    if not isinstance(decoded, list):
        return []
    return [int(item) for item in decoded if isinstance(item, int)]
