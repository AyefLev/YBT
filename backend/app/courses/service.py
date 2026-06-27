from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.auth.models import User
from app.courses.models import (
    Chapter,
    Course,
    KnowledgePoint,
    LessonSession,
    SessionLessonLink,
)
from app.courses.schemas import (
    ChapterCreateRequest,
    CourseCreateRequest,
    CourseUpdateRequest,
    KnowledgePointCreateRequest,
    LessonSessionCreateRequest,
    TeachingAssetRead,
)
from app.exercises.models import Exercise
from app.lessons.models import Lesson
from app.materials.models import Material


def create_course(
    db: Session,
    *,
    payload: CourseCreateRequest,
    current_user: User,
) -> Course:
    course = Course(
        owner_id=current_user.id,
        title=payload.title,
        subject=payload.subject,
        exam_type=payload.exam_type,
        description=payload.description,
        status=payload.status,
    )
    db.add(course)
    db.flush()
    return course


def list_courses(db: Session, *, current_user: User) -> list[Course]:
    statement = select(Course).order_by(Course.created_at.desc(), Course.id.desc())
    if not can_view_all_courses(current_user):
        statement = statement.where(Course.owner_id == current_user.id)
    return list(db.scalars(statement).all())


def get_owned_course(
    db: Session,
    *,
    course_id: int,
    current_user: User,
    include_detail: bool = False,
) -> Course | None:
    statement = select(Course).where(Course.id == course_id)
    if not can_view_all_courses(current_user):
        statement = statement.where(Course.owner_id == current_user.id)
    if include_detail:
        statement = statement.options(
            selectinload(Course.chapters).selectinload(Chapter.sessions).selectinload(
                LessonSession.lesson_links
            ),
            selectinload(Course.knowledge_points),
        )
    return db.scalar(statement)


def can_manage_course(course: Course, *, current_user: User) -> bool:
    return (
        "course:manage_all" in current_user.permission_codes
        or course.owner_id == current_user.id
    )


def can_view_all_courses(current_user: User) -> bool:
    return (
        "course:view_all" in current_user.permission_codes
        or "course:manage_all" in current_user.permission_codes
    )


def archive_course(db: Session, *, course: Course) -> Course:
    course.status = "archived"
    db.flush()
    return course


def update_course(
    db: Session,
    *,
    course: Course,
    payload: CourseUpdateRequest,
) -> Course:
    updates = payload.model_dump(exclude_unset=True)
    for field_name, value in updates.items():
        setattr(course, field_name, value)
    db.flush()
    return course


def create_chapter(
    db: Session,
    *,
    course: Course,
    payload: ChapterCreateRequest,
) -> Chapter:
    chapter = Chapter(
        course_id=course.id,
        title=payload.title,
        summary=payload.summary,
        order_index=payload.order_index,
    )
    db.add(chapter)
    db.flush()
    return chapter


def get_owned_chapter(
    db: Session,
    *,
    chapter_id: int,
    current_user: User,
) -> Chapter | None:
    statement = (
        select(Chapter)
        .join(Course, Chapter.course_id == Course.id)
        .where(Chapter.id == chapter_id)
    )
    if not can_view_all_courses(current_user):
        statement = statement.where(Course.owner_id == current_user.id)
    return db.scalar(statement)


def create_session(
    db: Session,
    *,
    chapter: Chapter,
    payload: LessonSessionCreateRequest,
    current_user: User,
) -> LessonSession:
    session = LessonSession(
        course_id=chapter.course_id,
        chapter_id=chapter.id,
        title=payload.title,
        duration_minutes=payload.duration_minutes,
        teaching_goal=payload.teaching_goal,
        order_index=payload.order_index,
    )
    db.add(session)
    db.flush()

    if payload.lesson_id is not None:
        lesson = db.scalar(
            select(Lesson).where(
                Lesson.id == payload.lesson_id,
                Lesson.owner_id == current_user.id,
            )
        )
        if lesson is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Lesson not found",
            )
        db.add(SessionLessonLink(session_id=session.id, lesson_id=lesson.id))
        db.flush()

    return session


def create_knowledge_point(
    db: Session,
    *,
    course: Course,
    payload: KnowledgePointCreateRequest,
) -> KnowledgePoint:
    if payload.chapter_id is not None:
        chapter = db.scalar(
            select(Chapter).where(
                Chapter.id == payload.chapter_id,
                Chapter.course_id == course.id,
            )
        )
        if chapter is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Chapter not found",
            )

    if payload.session_id is not None:
        session = db.scalar(
            select(LessonSession)
            .join(Chapter, LessonSession.chapter_id == Chapter.id)
            .where(
                LessonSession.id == payload.session_id,
                Chapter.course_id == course.id,
            )
        )
        if session is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Session not found",
            )
        if payload.chapter_id is not None and session.chapter_id != payload.chapter_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Session does not belong to chapter",
            )

    knowledge_point = KnowledgePoint(
        course_id=course.id,
        chapter_id=payload.chapter_id,
        session_id=payload.session_id,
        name=payload.name,
        description=payload.description,
        difficulty=payload.difficulty,
    )
    db.add(knowledge_point)
    db.flush()
    return knowledge_point


def list_course_assets(
    db: Session,
    *,
    course: Course,
    current_user: User,
) -> list[TeachingAssetRead]:
    assets: list[TeachingAssetRead] = []
    user_names = {
        user.id: user.display_name or user.username
        for user in db.scalars(select(User)).all()
    }

    material_query = select(Material).where(Material.course_id == course.id)
    if (
        "material:view_all" not in current_user.permission_codes
        and "material:manage_all" not in current_user.permission_codes
    ):
        material_query = material_query.where(
            (Material.uploader_id == current_user.id)
            | (Material.resource_scope == "public")
        )
    for material in db.scalars(material_query).all():
        assets.append(
            TeachingAssetRead(
                asset_type="material",
                id=material.id,
                title=material.title,
                owner_id=material.uploader_id,
                owner_name=user_names.get(material.uploader_id, ""),
                resource_scope=material.resource_scope,
                status=material.parse_status,
                course_id=material.course_id,
                chapter_id=material.chapter_id,
                session_id=material.session_id,
                knowledge_point_id=material.knowledge_point_id,
                created_at=material.created_at,
            )
        )

    lesson_query = select(Lesson).where(Lesson.course_id == course.id)
    if "lesson:view_all" not in current_user.permission_codes:
        lesson_query = lesson_query.where(Lesson.owner_id == current_user.id)
    for lesson in db.scalars(lesson_query).all():
        assets.append(
            TeachingAssetRead(
                asset_type="lesson",
                id=lesson.id,
                title=lesson.title,
                owner_id=lesson.owner_id,
                owner_name=user_names.get(lesson.owner_id, ""),
                status=lesson.review_status,
                course_id=lesson.course_id,
                chapter_id=lesson.chapter_id,
                session_id=lesson.session_id,
                knowledge_point_id=lesson.knowledge_point_id,
                updated_at=lesson.updated_at,
                created_at=lesson.created_at,
            )
        )

    exercise_query = select(Exercise).where(Exercise.course_id == course.id)
    if "exercise:view_all" not in current_user.permission_codes:
        exercise_query = exercise_query.where(Exercise.owner_id == current_user.id)
    for exercise in db.scalars(exercise_query).all():
        assets.append(
            TeachingAssetRead(
                asset_type="exercise",
                id=exercise.id,
                title=exercise.title,
                owner_id=exercise.owner_id,
                owner_name=user_names.get(exercise.owner_id, ""),
                status=exercise.compliance_level,
                course_id=exercise.course_id,
                chapter_id=exercise.chapter_id,
                session_id=exercise.session_id,
                knowledge_point_id=exercise.knowledge_point_id,
                updated_at=exercise.updated_at,
                created_at=exercise.created_at,
            )
        )
    return sorted(
        assets,
        key=lambda asset: (asset.chapter_id or 0, asset.session_id or 0, asset.asset_type, asset.id),
    )
