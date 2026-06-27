import json
import re

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.ai.formatting import normalize_generated_math_text
from app.ai.prompts import build_exercise_prompt
from app.ai.service import generate_text, review_generated_content
from app.auth.models import User
from app.compliance.service import check_content
from app.courses.models import Chapter, Course, KnowledgePoint, LessonSession
from app.exercises.models import Exercise, ExerciseVersion
from app.exercises.schemas import (
    ExerciseCreateRequest,
    ExerciseGenerateRequest,
    ExerciseGenerateResponse,
    ExerciseReference,
)
from app.questions.schemas import QuestionCreateRequest
from app.questions.service import create_question
from app.retrieval.service import search_chunks
from app.lessons.models import Lesson


def generate_exercise(
    db: Session,
    *,
    payload: ExerciseGenerateRequest,
    current_user: User,
) -> ExerciseGenerateResponse:
    references: list[ExerciseReference] = []
    teaching_context = _build_teaching_context(db, payload=payload, current_user=current_user)
    lesson_context = _build_lesson_context(db, lesson_id=payload.lesson_id, current_user=current_user)
    if payload.use_materials:
        chunks = search_chunks(
            db,
            query=payload.knowledge_point,
            top_k=5,
            material_ids=payload.material_ids,
            current_user=current_user,
        )
        references = [ExerciseReference.model_validate(chunk.model_dump()) for chunk in chunks]

    form = payload.model_dump()
    form["teaching_context"] = teaching_context
    form["lesson_context"] = lesson_context
    prompt = build_exercise_prompt(form, [reference.content for reference in references])
    ai_result = generate_text(db, "exercise", prompt)
    normalized_content = normalize_generated_math_text(ai_result.content)
    ai_result = ai_result.model_copy(update={"content": normalized_content})
    review = review_generated_content(
        db,
        task_type="exercise",
        content=normalized_content,
        enabled=payload.multi_agent_review,
        auto_revise=payload.auto_revise,
    )
    compliance = check_content(db, "exercise", normalized_content)

    return ExerciseGenerateResponse(
        content=normalized_content,
        references=references,
        provider_status=ai_result,
        compliance=compliance,
        review=review,
    )


def create_exercise(
    db: Session,
    *,
    payload: ExerciseCreateRequest,
    current_user: User,
) -> Exercise:
    content = normalize_generated_math_text(payload.content)
    _validate_teaching_scope(
        db,
        current_user=current_user,
        course_id=payload.course_id,
        chapter_id=payload.chapter_id,
        session_id=payload.session_id,
        knowledge_point_id=payload.knowledge_point_id,
        lesson_id=payload.lesson_id,
    )
    exercise = Exercise(
        owner_id=current_user.id,
        course_id=payload.course_id,
        chapter_id=payload.chapter_id,
        session_id=payload.session_id,
        knowledge_point_id=payload.knowledge_point_id,
        lesson_id=payload.lesson_id,
        title=payload.title,
        subject=payload.subject,
        knowledge_point=payload.knowledge_point,
        question_type=payload.question_type,
        difficulty=payload.difficulty,
        material_ids_json=_encode_ids(payload.material_ids),
        prompt_template=payload.prompt_template,
        output_format=payload.output_format,
        current_content=content,
        compliance_level="unknown",
    )
    db.add(exercise)
    db.flush()

    compliance = check_content(db, "exercise", content, str(exercise.id))
    exercise.compliance_level = compliance.risk_level
    add_exercise_version(
        db,
        exercise_id=exercise.id,
        content=content,
        change_note=payload.change_note,
        version_no=1,
    )
    return exercise


def list_exercises(db: Session, *, current_user: User) -> list[Exercise]:
    statement = select(Exercise).order_by(Exercise.created_at.desc(), Exercise.id.desc())
    if not can_view_all_exercises(current_user):
        statement = statement.where(Exercise.owner_id == current_user.id)
    return list(db.scalars(statement).all())


def get_owned_exercise(
    db: Session,
    *,
    exercise_id: int,
    current_user: User,
) -> Exercise | None:
    statement = select(Exercise).where(Exercise.id == exercise_id)
    if not can_view_all_exercises(current_user):
        statement = statement.where(Exercise.owner_id == current_user.id)
    return db.scalar(statement)


def can_view_all_exercises(current_user: User) -> bool:
    return "exercise:view_all" in current_user.permission_codes


def exercise_material_ids(exercise: Exercise) -> list[int]:
    return _decode_ids(exercise.material_ids_json)


def list_versions(db: Session, *, exercise: Exercise) -> list[ExerciseVersion]:
    return list(
        db.scalars(
            select(ExerciseVersion)
            .where(ExerciseVersion.exercise_id == exercise.id)
            .order_by(ExerciseVersion.version_no)
        ).all()
    )


def restore_version(
    db: Session,
    *,
    exercise: Exercise,
    version_id: int,
) -> Exercise | None:
    restored_version = db.scalar(
        select(ExerciseVersion).where(
            ExerciseVersion.id == version_id,
            ExerciseVersion.exercise_id == exercise.id,
        )
    )
    if restored_version is None:
        return None

    add_exercise_version(
        db,
        exercise_id=exercise.id,
        content=restored_version.content,
        change_note=f"Restore version {restored_version.version_no}",
    )
    exercise.current_content = restored_version.content
    compliance = check_content(db, "exercise", restored_version.content, str(exercise.id))
    exercise.compliance_level = compliance.risk_level
    db.flush()
    return exercise


def save_exercise_to_question_bank(
    db: Session,
    *,
    exercise: Exercise,
    current_user: User,
) -> list:
    drafts = _parse_exercise_questions(exercise)
    created = []
    for index, draft in enumerate(drafts, start=1):
        payload = QuestionCreateRequest(
            course_id=exercise.course_id,
            chapter_id=exercise.chapter_id,
            session_id=exercise.session_id,
            knowledge_point_id=exercise.knowledge_point_id,
            source_exercise_id=exercise.id,
            title=f"{exercise.title} - 题目 {index}",
            subject=exercise.subject,
            question_type=draft["question_type"],
            difficulty=_normalize_question_difficulty(exercise.difficulty),
            stem=draft["stem"],
            options=draft["options"],
            answer=draft["answer"],
            analysis=draft["analysis"],
            tags=[exercise.knowledge_point],
        )
        created.append(create_question(db, payload=payload, current_user=current_user))
    return created


def add_exercise_version(
    db: Session,
    *,
    exercise_id: int,
    content: str,
    change_note: str,
    version_no: int | None = None,
    max_retries: int = 1,
) -> ExerciseVersion:
    attempts = max_retries + 1 if version_no is None else 1
    last_error: IntegrityError | None = None

    for _ in range(attempts):
        try:
            with db.begin_nested():
                candidate_version_no = (
                    version_no
                    if version_no is not None
                    else _next_exercise_version_no(db, exercise_id)
                )
                version = ExerciseVersion(
                    exercise_id=exercise_id,
                    version_no=candidate_version_no,
                    content=content,
                    change_note=change_note,
                )
                db.add(version)
                db.flush()
            return version
        except IntegrityError as exc:
            last_error = exc

    if last_error is not None:
        raise last_error
    raise RuntimeError("Could not create exercise version")


def _next_exercise_version_no(db: Session, exercise_id: int) -> int:
    max_version_no = db.scalar(
        select(func.max(ExerciseVersion.version_no)).where(
            ExerciseVersion.exercise_id == exercise_id,
        )
    )
    return (max_version_no or 0) + 1


def _parse_exercise_questions(exercise: Exercise) -> list[dict[str, object]]:
    blocks = _split_question_blocks(exercise.current_content)
    return [_parse_question_block(block, exercise.question_type) for block in blocks]


def _split_question_blocks(content: str) -> list[str]:
    normalized = content.strip()
    if not normalized:
        return []

    matches = list(re.finditer(r"(?m)^\s*(?:题目|第)\s*[一二三四五六七八九十\d]+\s*(?:题)?\s*$|^\s*\d+[.、]\s+", normalized))
    if len(matches) <= 1:
        return [normalized]

    blocks: list[str] = []
    for index, match in enumerate(matches):
        start = match.start()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(normalized)
        block = normalized[start:end].strip()
        if block:
            blocks.append(block)
    return blocks or [normalized]


def _parse_question_block(block: str, source_question_type: str) -> dict[str, object]:
    lines = [line.strip() for line in block.splitlines() if line.strip()]
    if lines and re.match(r"^(?:题目|第)\s*[一二三四五六七八九十\d]+\s*(?:题)?$|^\d+[.、]\s*", lines[0]):
        lines = lines[1:]

    options: list[str] = []
    stem_lines: list[str] = []
    answer = ""
    analysis_lines: list[str] = []
    in_analysis = False

    for line in lines:
        answer_match = re.match(r"^(?:答案|正确答案)\s*[:：]\s*(.+)$", line)
        analysis_match = re.match(r"^(?:解析|答案解析|答案与解析)\s*[:：]\s*(.*)$", line)
        if answer_match:
            answer = answer_match.group(1).strip()
            in_analysis = False
        elif analysis_match:
            in_analysis = True
            if analysis_match.group(1).strip():
                analysis_lines.append(analysis_match.group(1).strip())
        elif re.match(r"^[A-H][.、]\s*", line):
            options.append(line)
        elif in_analysis:
            analysis_lines.append(line)
        else:
            stem_lines.append(line)

    stem = "\n".join(stem_lines).strip() or block.strip()
    question_type = "single_choice" if options else _normalize_question_type(source_question_type)
    return {
        "stem": stem,
        "options": options,
        "answer": answer,
        "analysis": "\n".join(analysis_lines).strip(),
        "question_type": question_type,
    }


def _normalize_question_type(value: str) -> str:
    if "判断" in value:
        return "true_false"
    if "填空" in value:
        return "fill_blank"
    if "选择" in value:
        return "single_choice"
    return "short_answer"


def _normalize_question_difficulty(value: str) -> str:
    if value in {"basic", "medium", "advanced"}:
        return value
    if "基础" in value or "简单" in value:
        return "basic"
    if "提高" in value or "高级" in value or "困难" in value:
        return "advanced"
    return "medium"


def _build_teaching_context(
    db: Session,
    *,
    payload: ExerciseGenerateRequest,
    current_user: User,
) -> str:
    _validate_teaching_scope(
        db,
        current_user=current_user,
        course_id=payload.course_id,
        chapter_id=payload.chapter_id,
        session_id=payload.session_id,
        knowledge_point_id=payload.knowledge_point_id,
        lesson_id=payload.lesson_id,
    )
    lines: list[str] = []
    if payload.course_id is not None:
        course = db.get(Course, payload.course_id)
        if course:
            lines.append(f"课程：{course.title}（{course.subject}，{course.exam_type}）")
    if payload.chapter_id is not None:
        chapter = db.get(Chapter, payload.chapter_id)
        if chapter:
            lines.append(f"章节：{chapter.title}；{chapter.summary}")
    if payload.session_id is not None:
        session = db.get(LessonSession, payload.session_id)
        if session:
            lines.append(f"课次：{session.title}；目标：{session.teaching_goal}")
    if payload.knowledge_point_id is not None:
        point = db.get(KnowledgePoint, payload.knowledge_point_id)
        if point:
            lines.append(f"知识点：{point.name}；说明：{point.description}")
    return "\n".join(line for line in lines if line.strip())


def _build_lesson_context(
    db: Session,
    *,
    lesson_id: int | None,
    current_user: User,
) -> str:
    if lesson_id is None:
        return ""
    query = select(Lesson).where(Lesson.id == lesson_id)
    if "lesson:view_all" not in current_user.permission_codes:
        query = query.where(Lesson.owner_id == current_user.id)
    lesson = db.scalar(query)
    if lesson is None:
        raise HTTPException(status_code=404, detail="Lesson not found")
    return f"教案：{lesson.title}\n{lesson.current_content[:2000]}"


def _validate_teaching_scope(
    db: Session,
    *,
    current_user: User,
    course_id: int | None,
    chapter_id: int | None,
    session_id: int | None,
    knowledge_point_id: int | None,
    lesson_id: int | None,
) -> None:
    resolved_course_id = course_id
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
    if lesson_id is not None:
        lesson = db.get(Lesson, lesson_id)
        if lesson is None:
            raise HTTPException(status_code=404, detail="Lesson not found")
        if lesson.course_id is not None:
            resolved_course_id = _ensure_same_course(resolved_course_id, lesson.course_id)

    if resolved_course_id is not None:
        course_query = select(Course).where(Course.id == resolved_course_id)
        if (
            "course:manage_all" not in current_user.permission_codes
            and "course:view_all" not in current_user.permission_codes
        ):
            course_query = course_query.where(Course.owner_id == current_user.id)
        if db.scalar(course_query) is None:
            raise HTTPException(status_code=404, detail="Course not found")


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
