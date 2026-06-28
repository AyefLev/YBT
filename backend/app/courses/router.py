from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth.models import User
from app.core.database import get_db
from app.core.deps import require_any_permission, require_permission
from app.courses.models import Chapter, Course, KnowledgePoint, LessonSession
from app.courses.schemas import (
    ChapterCreateRequest,
    ChapterRead,
    CourseCreateRequest,
    CourseAssetsRead,
    CourseDetailRead,
    CourseRead,
    CourseUpdateRequest,
    KnowledgePointCreateRequest,
    KnowledgePointRead,
    LessonSessionCreateRequest,
    LessonSessionRead,
    TeachingAssetRead,
)
from app.courses.service import (
    archive_course,
    can_manage_course,
    create_chapter,
    create_course,
    create_knowledge_point,
    create_session,
    get_owned_chapter,
    get_owned_course,
    list_course_assets,
    list_courses,
    update_course,
)

router = APIRouter(prefix="/api", tags=["courses"])


def _session_lesson_id(session: LessonSession) -> int | None:
    if not session.lesson_links:
        return None
    return session.lesson_links[0].lesson_id


def session_to_read(session: LessonSession) -> LessonSessionRead:
    return LessonSessionRead(
        id=session.id,
        course_id=session.course_id,
        chapter_id=session.chapter_id,
        title=session.title,
        duration_minutes=session.duration_minutes,
        teaching_goal=session.teaching_goal,
        order_index=session.order_index,
        lesson_id=_session_lesson_id(session),
        created_at=session.created_at,
        updated_at=session.updated_at,
    )


def chapter_to_read(chapter: Chapter) -> ChapterRead:
    return ChapterRead(
        id=chapter.id,
        course_id=chapter.course_id,
        title=chapter.title,
        summary=chapter.summary,
        order_index=chapter.order_index,
        sessions=[session_to_read(session) for session in chapter.sessions],
        created_at=chapter.created_at,
        updated_at=chapter.updated_at,
    )


def knowledge_point_to_read(knowledge_point: KnowledgePoint) -> KnowledgePointRead:
    return KnowledgePointRead.model_validate(knowledge_point)


def course_to_read(course: Course, db: Session) -> CourseRead:
    owner = db.get(User, course.owner_id)
    return CourseRead(
        id=course.id,
        owner_id=course.owner_id,
        owner_name=owner.display_name if owner else "",
        owner_username=owner.username if owner else "",
        title=course.title,
        subject=course.subject,
        exam_type=course.exam_type,
        description=course.description,
        status=course.status,
        created_at=course.created_at,
        updated_at=course.updated_at,
    )


def course_to_detail(course: Course, db: Session) -> CourseDetailRead:
    return CourseDetailRead(
        **course_to_read(course, db).model_dump(),
        chapters=[chapter_to_read(chapter) for chapter in course.chapters],
        knowledge_points=[
            knowledge_point_to_read(knowledge_point)
            for knowledge_point in course.knowledge_points
        ],
    )


def _course_or_404(db: Session, course_id: int, current_user: User) -> Course:
    course = get_owned_course(db, course_id=course_id, current_user=current_user)
    if course is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Course not found",
        )
    return course


def _manageable_course_or_404(db: Session, course_id: int, current_user: User) -> Course:
    course = _course_or_404(db, course_id, current_user)
    if not can_manage_course(course, current_user=current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions to manage this course",
        )
    return course


@router.post("/courses", response_model=CourseRead, status_code=status.HTTP_201_CREATED)
def create_current_user_course(
    payload: CourseCreateRequest,
    current_user: User = Depends(require_permission("course:create")),
    db: Session = Depends(get_db),
) -> CourseRead:
    course = create_course(db, payload=payload, current_user=current_user)
    response = course_to_read(course, db)
    db.commit()
    return response


@router.get("/courses", response_model=list[CourseRead])
def list_current_user_courses(
    current_user: User = Depends(require_any_permission("course:create", "course:view_all", "course:manage_all")),
    db: Session = Depends(get_db),
) -> list[CourseRead]:
    return [course_to_read(course, db) for course in list_courses(db, current_user=current_user)]


@router.get("/courses/{course_id}", response_model=CourseDetailRead)
def get_course_detail(
    course_id: int,
    current_user: User = Depends(require_any_permission("course:create", "course:view_all", "course:manage_all")),
    db: Session = Depends(get_db),
) -> CourseDetailRead:
    course = get_owned_course(
        db,
        course_id=course_id,
        current_user=current_user,
        include_detail=True,
    )
    if course is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Course not found",
        )
    return course_to_detail(course, db)


@router.get("/courses/{course_id}/assets", response_model=CourseAssetsRead)
def get_course_assets(
    course_id: int,
    current_user: User = Depends(require_any_permission("course:create", "course:view_all", "course:manage_all")),
    db: Session = Depends(get_db),
) -> CourseAssetsRead:
    course = _course_or_404(db, course_id, current_user)
    return CourseAssetsRead(
        course_id=course.id,
        assets=list_course_assets(db, course=course, current_user=current_user),
    )


@router.patch("/courses/{course_id}", response_model=CourseRead)
def update_current_user_course(
    course_id: int,
    payload: CourseUpdateRequest,
    current_user: User = Depends(require_permission("course:create")),
    db: Session = Depends(get_db),
) -> CourseRead:
    course = _manageable_course_or_404(db, course_id, current_user)
    updated = update_course(db, course=course, payload=payload)
    response = course_to_read(updated, db)
    db.commit()
    return response


@router.delete("/courses/{course_id}", response_model=CourseRead)
def delete_course(
    course_id: int,
    current_user: User = Depends(require_permission("course:create")),
    db: Session = Depends(get_db),
) -> CourseRead:
    course = _manageable_course_or_404(db, course_id, current_user)
    archived = archive_course(db, course=course)
    response = course_to_read(archived, db)
    db.commit()
    return response


@router.post(
    "/courses/{course_id}/chapters",
    response_model=ChapterRead,
    status_code=status.HTTP_201_CREATED,
)
def create_course_chapter(
    course_id: int,
    payload: ChapterCreateRequest,
    current_user: User = Depends(require_permission("course:create")),
    db: Session = Depends(get_db),
) -> ChapterRead:
    course = _manageable_course_or_404(db, course_id, current_user)
    chapter = create_chapter(db, course=course, payload=payload)
    response = chapter_to_read(chapter)
    db.commit()
    return response


@router.post(
    "/chapters/{chapter_id}/sessions",
    response_model=LessonSessionRead,
    status_code=status.HTTP_201_CREATED,
)
def create_chapter_session(
    chapter_id: int,
    payload: LessonSessionCreateRequest,
    current_user: User = Depends(require_permission("course:create")),
    db: Session = Depends(get_db),
) -> LessonSessionRead:
    chapter = get_owned_chapter(db, chapter_id=chapter_id, current_user=current_user)
    if chapter is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chapter not found",
        )
    session = create_session(
        db,
        chapter=chapter,
        payload=payload,
        current_user=current_user,
    )
    response = session_to_read(session)
    db.commit()
    return response


@router.post(
    "/courses/{course_id}/knowledge-points",
    response_model=KnowledgePointRead,
    status_code=status.HTTP_201_CREATED,
)
def create_course_knowledge_point(
    course_id: int,
    payload: KnowledgePointCreateRequest,
    current_user: User = Depends(require_permission("course:create")),
    db: Session = Depends(get_db),
) -> KnowledgePointRead:
    course = _manageable_course_or_404(db, course_id, current_user)
    knowledge_point = create_knowledge_point(db, course=course, payload=payload)
    response = knowledge_point_to_read(knowledge_point)
    db.commit()
    return response
