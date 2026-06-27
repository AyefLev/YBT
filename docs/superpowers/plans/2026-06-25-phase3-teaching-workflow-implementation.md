# Phase 3 Teaching Workflow Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the Phase 3 institutional teaching-research workflow: course hierarchy, question bank, review workflow, and lightweight institutional DOCX exports.

**Architecture:** Add focused backend modules for courses, questions, and reviews while preserving existing lesson/material/exercise modules. Use owner-scoped SQLAlchemy models, explicit FastAPI routers, lightweight link tables, and the existing SQLite compatibility migration pattern. The frontend adds three focused pages: course structure, question bank, and review queue.

**Tech Stack:** FastAPI, SQLAlchemy, SQLite, Pydantic, python-docx, Vue 3, Vite, TypeScript, Vitest, pytest.

---

## File Structure

### Backend

- Create `backend/app/courses/models.py`
  - Course, Chapter, LessonSession, KnowledgePoint, CourseMaterialLink, SessionLessonLink.
- Create `backend/app/courses/schemas.py`
  - Request/response schemas for course hierarchy and asset links.
- Create `backend/app/courses/service.py`
  - Owner-scoped CRUD, ordering, linking, and delete/archive rules.
- Create `backend/app/courses/router.py`
  - REST API for course hierarchy and links.
- Create `backend/app/questions/models.py`
  - QuestionBankItem model.
- Create `backend/app/questions/schemas.py`
  - Question create/update/filter/read schemas.
- Create `backend/app/questions/service.py`
  - Owner-scoped question CRUD, filters, status updates.
- Create `backend/app/questions/router.py`
  - Question bank API.
- Create `backend/app/reviews/schemas.py`
  - Review action and pending review response schemas.
- Create `backend/app/reviews/service.py`
  - Shared review transition logic for lessons and question-bank items.
- Create `backend/app/reviews/router.py`
  - Pending queue and approve/reject/return-draft APIs.
- Modify `backend/app/lessons/models.py`
  - Add review fields to `Lesson`.
- Modify `backend/app/lessons/schemas.py`
  - Add review fields to `LessonRead`.
- Modify `backend/app/lessons/router.py`
  - Return review fields.
- Modify `backend/app/auth/permissions.py`
  - Add `review:manage`.
- Modify `backend/app/auth/service.py`
  - Ensure seeded role updates preserve managed permissions.
- Modify `backend/app/core/database.py`
  - Add SQLite compatibility migration for new lesson review columns.
- Modify `backend/app/main.py`
  - Import and register new routers/models.
- Modify `backend/app/exports/service.py`
  - Add course outline and question package DOCX exports.
- Modify `backend/app/exports/router.py`
  - Add export endpoints.
- Test files:
  - `backend/tests/test_courses.py`
  - `backend/tests/test_questions.py`
  - `backend/tests/test_reviews.py`
  - `backend/tests/test_phase3_exports.py`
  - Update `backend/tests/test_admin_logs.py` only if permissions tests need role assertions.

### Frontend

- Create `frontend/src/pages/CoursesPage.vue`
  - Course list/detail hierarchy management.
- Create `frontend/src/pages/QuestionBankPage.vue`
  - Question list, filters, create/edit, submit review, export.
- Create `frontend/src/pages/ReviewQueuePage.vue`
  - Pending reviews, approve/reject.
- Modify `frontend/src/router.ts`
  - Add `/dashboard/courses`, `/dashboard/questions`, `/dashboard/reviews`.
- Modify `frontend/src/layouts/WorkbenchLayout.vue`
  - Add navigation items.
- Modify `frontend/src/router.test.ts`
  - Assert new authenticated routes exist.

---

## Task 1: Backend Course Hierarchy Tests

**Files:**
- Create: `backend/tests/test_courses.py`

- [ ] **Step 1: Write failing course hierarchy tests**

Create `backend/tests/test_courses.py`:

```python
def _auth_headers(client, username: str = "teacher_courses") -> dict[str, str]:
    client.post(
        "/api/auth/register",
        json={
            "username": username,
            "email": f"{username}@example.com",
            "password": "secret-password",
            "display_name": "Course Teacher",
        },
    )
    login_response = client.post(
        "/api/auth/login",
        json={"username": username, "password": "secret-password"},
    )
    return {"Authorization": f"Bearer {login_response.json()['access_token']}"}


def _create_course(client, headers: dict[str, str], **overrides):
    payload = {
        "title": "考研英语一基础班",
        "subject": "英语",
        "exam_type": "考研英语一",
        "description": "基础阶段课程",
        "status": "draft",
    }
    payload.update(overrides)
    response = client.post("/api/courses", headers=headers, json=payload)
    assert response.status_code == 201
    return response.json()


def test_course_hierarchy_crud_and_detail(client):
    headers = _auth_headers(client)
    course = _create_course(client, headers)

    chapter_response = client.post(
        f"/api/courses/{course['id']}/chapters",
        headers=headers,
        json={"title": "书信写作", "summary": "小作文书信", "order_index": 1},
    )
    assert chapter_response.status_code == 201
    chapter = chapter_response.json()

    session_response = client.post(
        f"/api/chapters/{chapter['id']}/sessions",
        headers=headers,
        json={
            "title": "建议信写作",
            "duration_minutes": 90,
            "teaching_goal": "掌握建议信结构",
            "order_index": 1,
            "lesson_id": None,
        },
    )
    assert session_response.status_code == 201
    session = session_response.json()

    kp_response = client.post(
        f"/api/courses/{course['id']}/knowledge-points",
        headers=headers,
        json={
            "chapter_id": chapter["id"],
            "session_id": session["id"],
            "name": "建议信结构",
            "description": "目的、建议、结尾",
            "difficulty": "basic",
        },
    )
    assert kp_response.status_code == 201
    knowledge_point = kp_response.json()

    detail_response = client.get(f"/api/courses/{course['id']}", headers=headers)
    assert detail_response.status_code == 200
    detail = detail_response.json()
    assert detail["title"] == "考研英语一基础班"
    assert detail["chapters"][0]["id"] == chapter["id"]
    assert detail["chapters"][0]["sessions"][0]["id"] == session["id"]
    assert detail["knowledge_points"][0]["id"] == knowledge_point["id"]


def test_course_list_and_cross_user_scope(client):
    owner_headers = _auth_headers(client, "teacher_course_owner")
    other_headers = _auth_headers(client, "teacher_course_other")
    course = _create_course(client, owner_headers, title="Owner Course")
    _create_course(client, other_headers, title="Other Course")

    list_response = client.get("/api/courses", headers=owner_headers)
    assert list_response.status_code == 200
    assert [item["title"] for item in list_response.json()] == ["Owner Course"]

    other_detail = client.get(f"/api/courses/{course['id']}", headers=other_headers)
    assert other_detail.status_code == 404


def test_course_archive_instead_of_hard_delete(client):
    headers = _auth_headers(client, "teacher_course_archive")
    course = _create_course(client, headers, status="active")

    response = client.delete(f"/api/courses/{course['id']}", headers=headers)

    assert response.status_code == 200
    assert response.json()["status"] == "archived"
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```powershell
cd backend
python -m pytest tests/test_courses.py -q
```

Expected:

- FAIL because `/api/courses` routes and course models do not exist.

- [ ] **Step 3: Commit failing tests**

```powershell
git add backend/tests/test_courses.py
git commit -m "test: cover phase 3 course hierarchy"
```

---

## Task 2: Backend Course Hierarchy Implementation

**Files:**
- Create: `backend/app/courses/models.py`
- Create: `backend/app/courses/schemas.py`
- Create: `backend/app/courses/service.py`
- Create: `backend/app/courses/router.py`
- Modify: `backend/app/main.py`

- [ ] **Step 1: Add course models**

Create `backend/app/courses/models.py` with:

```python
from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Course(Base):
    __tablename__ = "courses"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    title: Mapped[str] = mapped_column(String(255))
    subject: Mapped[str] = mapped_column(String(128))
    exam_type: Mapped[str] = mapped_column(String(128), default="")
    description: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(32), default="draft")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    chapters: Mapped[list["Chapter"]] = relationship(back_populates="course", cascade="all, delete-orphan", order_by="Chapter.order_index")
    knowledge_points: Mapped[list["KnowledgePoint"]] = relationship(back_populates="course", cascade="all, delete-orphan", order_by="KnowledgePoint.id")


class Chapter(Base):
    __tablename__ = "chapters"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    course_id: Mapped[int] = mapped_column(ForeignKey("courses.id"), index=True)
    title: Mapped[str] = mapped_column(String(255))
    summary: Mapped[str] = mapped_column(Text, default="")
    order_index: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    course: Mapped[Course] = relationship(back_populates="chapters")
    sessions: Mapped[list["LessonSession"]] = relationship(back_populates="chapter", cascade="all, delete-orphan", order_by="LessonSession.order_index")


class LessonSession(Base):
    __tablename__ = "lesson_sessions"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    course_id: Mapped[int] = mapped_column(ForeignKey("courses.id"), index=True)
    chapter_id: Mapped[int] = mapped_column(ForeignKey("chapters.id"), index=True)
    title: Mapped[str] = mapped_column(String(255))
    duration_minutes: Mapped[int] = mapped_column(Integer)
    teaching_goal: Mapped[str] = mapped_column(Text, default="")
    order_index: Mapped[int] = mapped_column(Integer, default=0)
    lesson_id: Mapped[int | None] = mapped_column(ForeignKey("lessons.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    chapter: Mapped[Chapter] = relationship(back_populates="sessions")


class KnowledgePoint(Base):
    __tablename__ = "knowledge_points"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    course_id: Mapped[int] = mapped_column(ForeignKey("courses.id"), index=True)
    chapter_id: Mapped[int | None] = mapped_column(ForeignKey("chapters.id"), nullable=True)
    session_id: Mapped[int | None] = mapped_column(ForeignKey("lesson_sessions.id"), nullable=True)
    name: Mapped[str] = mapped_column(String(255))
    description: Mapped[str] = mapped_column(Text, default="")
    difficulty: Mapped[str] = mapped_column(String(32), default="basic")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    course: Mapped[Course] = relationship(back_populates="knowledge_points")


class CourseMaterialLink(Base):
    __tablename__ = "course_material_links"
    __table_args__ = (UniqueConstraint("course_id", "material_id", name="uq_course_material_link"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    course_id: Mapped[int] = mapped_column(ForeignKey("courses.id"), index=True)
    material_id: Mapped[int] = mapped_column(ForeignKey("materials.id"), index=True)


class SessionLessonLink(Base):
    __tablename__ = "session_lesson_links"
    __table_args__ = (UniqueConstraint("session_id", "lesson_id", name="uq_session_lesson_link"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    session_id: Mapped[int] = mapped_column(ForeignKey("lesson_sessions.id"), index=True)
    lesson_id: Mapped[int] = mapped_column(ForeignKey("lessons.id"), index=True)
```

- [ ] **Step 2: Add schemas**

Create `backend/app/courses/schemas.py` with request and read models:

```python
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class CourseCreateRequest(BaseModel):
    title: str = Field(min_length=1)
    subject: str = Field(min_length=1)
    exam_type: str = ""
    description: str = ""
    status: str = "draft"


class CourseUpdateRequest(BaseModel):
    title: str | None = None
    subject: str | None = None
    exam_type: str | None = None
    description: str | None = None
    status: str | None = None


class ChapterCreateRequest(BaseModel):
    title: str = Field(min_length=1)
    summary: str = ""
    order_index: int = 0


class SessionCreateRequest(BaseModel):
    title: str = Field(min_length=1)
    duration_minutes: int = Field(gt=0)
    teaching_goal: str = ""
    order_index: int = 0
    lesson_id: int | None = None


class KnowledgePointCreateRequest(BaseModel):
    chapter_id: int | None = None
    session_id: int | None = None
    name: str = Field(min_length=1)
    description: str = ""
    difficulty: str = "basic"


class LessonSessionRead(BaseModel):
    id: int
    course_id: int
    chapter_id: int
    title: str
    duration_minutes: int
    teaching_goal: str
    order_index: int
    lesson_id: int | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ChapterRead(BaseModel):
    id: int
    course_id: int
    title: str
    summary: str
    order_index: int
    created_at: datetime
    updated_at: datetime
    sessions: list[LessonSessionRead] = []

    model_config = ConfigDict(from_attributes=True)


class KnowledgePointRead(BaseModel):
    id: int
    course_id: int
    chapter_id: int | None
    session_id: int | None
    name: str
    description: str
    difficulty: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CourseRead(BaseModel):
    id: int
    owner_id: int
    title: str
    subject: str
    exam_type: str
    description: str
    status: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CourseDetailRead(CourseRead):
    chapters: list[ChapterRead] = []
    knowledge_points: list[KnowledgePointRead] = []
```

- [ ] **Step 3: Add service functions**

Create `backend/app/courses/service.py` with:

```python
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.models import User
from app.courses.models import Chapter, Course, KnowledgePoint, LessonSession
from app.courses.schemas import (
    ChapterCreateRequest,
    CourseCreateRequest,
    CourseUpdateRequest,
    KnowledgePointCreateRequest,
    SessionCreateRequest,
)


VALID_COURSE_STATUSES = {"draft", "active", "archived"}
VALID_DIFFICULTIES = {"basic", "medium", "advanced"}


def list_courses(db: Session, *, current_user: User) -> list[Course]:
    return list(
        db.scalars(
            select(Course)
            .where(Course.owner_id == current_user.id)
            .order_by(Course.created_at.desc(), Course.id.desc())
        ).all()
    )


def get_owned_course(db: Session, *, course_id: int, current_user: User) -> Course | None:
    return db.scalar(select(Course).where(Course.id == course_id, Course.owner_id == current_user.id))


def create_course(db: Session, *, payload: CourseCreateRequest, current_user: User) -> Course:
    status = payload.status if payload.status in VALID_COURSE_STATUSES else "draft"
    course = Course(owner_id=current_user.id, title=payload.title, subject=payload.subject, exam_type=payload.exam_type, description=payload.description, status=status)
    db.add(course)
    db.flush()
    return course


def update_course(db: Session, *, course: Course, payload: CourseUpdateRequest) -> Course:
    for field in ("title", "subject", "exam_type", "description", "status"):
        value = getattr(payload, field)
        if value is not None:
            if field == "status" and value not in VALID_COURSE_STATUSES:
                continue
            setattr(course, field, value)
    db.flush()
    return course


def archive_course(db: Session, *, course: Course) -> Course:
    course.status = "archived"
    db.flush()
    return course


def create_chapter(db: Session, *, course: Course, payload: ChapterCreateRequest) -> Chapter:
    chapter = Chapter(course_id=course.id, title=payload.title, summary=payload.summary, order_index=payload.order_index)
    db.add(chapter)
    db.flush()
    return chapter


def get_owned_chapter(db: Session, *, chapter_id: int, current_user: User) -> Chapter | None:
    return db.scalar(select(Chapter).join(Course).where(Chapter.id == chapter_id, Course.owner_id == current_user.id))


def create_session(db: Session, *, chapter: Chapter, payload: SessionCreateRequest) -> LessonSession:
    session = LessonSession(course_id=chapter.course_id, chapter_id=chapter.id, title=payload.title, duration_minutes=payload.duration_minutes, teaching_goal=payload.teaching_goal, order_index=payload.order_index, lesson_id=payload.lesson_id)
    db.add(session)
    db.flush()
    return session


def create_knowledge_point(db: Session, *, course: Course, payload: KnowledgePointCreateRequest) -> KnowledgePoint:
    difficulty = payload.difficulty if payload.difficulty in VALID_DIFFICULTIES else "basic"
    point = KnowledgePoint(course_id=course.id, chapter_id=payload.chapter_id, session_id=payload.session_id, name=payload.name, description=payload.description, difficulty=difficulty)
    db.add(point)
    db.flush()
    return point
```

- [ ] **Step 4: Add router**

Create `backend/app/courses/router.py` with explicit 404 ownership checks:

```python
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth.models import User
from app.core.database import get_db
from app.core.deps import require_permission
from app.courses.models import Chapter, Course
from app.courses.schemas import (
    ChapterCreateRequest,
    ChapterRead,
    CourseCreateRequest,
    CourseDetailRead,
    CourseRead,
    CourseUpdateRequest,
    KnowledgePointCreateRequest,
    KnowledgePointRead,
    LessonSessionRead,
    SessionCreateRequest,
)
from app.courses.service import archive_course, create_chapter, create_course, create_knowledge_point, create_session, get_owned_chapter, get_owned_course, list_courses, update_course

router = APIRouter(prefix="/api", tags=["courses"])


def course_or_404(db: Session, course_id: int, current_user: User) -> Course:
    course = get_owned_course(db, course_id=course_id, current_user=current_user)
    if course is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Course not found")
    return course


def chapter_or_404(db: Session, chapter_id: int, current_user: User) -> Chapter:
    chapter = get_owned_chapter(db, chapter_id=chapter_id, current_user=current_user)
    if chapter is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Chapter not found")
    return chapter


@router.get("/courses", response_model=list[CourseRead])
def list_current_courses(current_user: User = Depends(require_permission("lesson:create")), db: Session = Depends(get_db)):
    return list_courses(db, current_user=current_user)


@router.post("/courses", response_model=CourseRead, status_code=status.HTTP_201_CREATED)
def create_current_course(payload: CourseCreateRequest, current_user: User = Depends(require_permission("lesson:create")), db: Session = Depends(get_db)):
    course = create_course(db, payload=payload, current_user=current_user)
    db.commit()
    return course


@router.get("/courses/{course_id}", response_model=CourseDetailRead)
def get_course_detail(course_id: int, current_user: User = Depends(require_permission("lesson:create")), db: Session = Depends(get_db)):
    return course_or_404(db, course_id, current_user)


@router.patch("/courses/{course_id}", response_model=CourseRead)
def patch_course(course_id: int, payload: CourseUpdateRequest, current_user: User = Depends(require_permission("lesson:create")), db: Session = Depends(get_db)):
    course = update_course(db, course=course_or_404(db, course_id, current_user), payload=payload)
    db.commit()
    return course


@router.delete("/courses/{course_id}", response_model=CourseRead)
def delete_course(course_id: int, current_user: User = Depends(require_permission("lesson:create")), db: Session = Depends(get_db)):
    course = archive_course(db, course=course_or_404(db, course_id, current_user))
    db.commit()
    return course


@router.post("/courses/{course_id}/chapters", response_model=ChapterRead, status_code=status.HTTP_201_CREATED)
def create_course_chapter(course_id: int, payload: ChapterCreateRequest, current_user: User = Depends(require_permission("lesson:create")), db: Session = Depends(get_db)):
    chapter = create_chapter(db, course=course_or_404(db, course_id, current_user), payload=payload)
    db.commit()
    return chapter


@router.post("/chapters/{chapter_id}/sessions", response_model=LessonSessionRead, status_code=status.HTTP_201_CREATED)
def create_chapter_session(chapter_id: int, payload: SessionCreateRequest, current_user: User = Depends(require_permission("lesson:create")), db: Session = Depends(get_db)):
    session = create_session(db, chapter=chapter_or_404(db, chapter_id, current_user), payload=payload)
    db.commit()
    return session


@router.post("/courses/{course_id}/knowledge-points", response_model=KnowledgePointRead, status_code=status.HTTP_201_CREATED)
def create_course_knowledge_point(course_id: int, payload: KnowledgePointCreateRequest, current_user: User = Depends(require_permission("lesson:create")), db: Session = Depends(get_db)):
    point = create_knowledge_point(db, course=course_or_404(db, course_id, current_user), payload=payload)
    db.commit()
    return point
```

- [ ] **Step 5: Register module in app**

Modify `backend/app/main.py`:

```python
from app.courses import models as courses_models  # noqa: F401
from app.courses.router import router as courses_router
```

Include router after materials:

```python
app.include_router(courses_router)
```

- [ ] **Step 6: Run course tests**

Run:

```powershell
cd backend
python -m pytest tests/test_courses.py -q
```

Expected:

- PASS for course hierarchy tests.

- [ ] **Step 7: Commit course implementation**

```powershell
git add backend/app/courses backend/app/main.py
git commit -m "feat: add course hierarchy"
```

---

## Task 3: Question Bank Tests

**Files:**
- Create: `backend/tests/test_questions.py`

- [ ] **Step 1: Write failing question bank tests**

Create `backend/tests/test_questions.py`:

```python
def _auth_headers(client, username: str = "teacher_questions") -> dict[str, str]:
    client.post(
        "/api/auth/register",
        json={
            "username": username,
            "email": f"{username}@example.com",
            "password": "secret-password",
            "display_name": "Question Teacher",
        },
    )
    login = client.post("/api/auth/login", json={"username": username, "password": "secret-password"})
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


def _create_question(client, headers: dict[str, str], **overrides):
    payload = {
        "title": "矩阵乘法条件",
        "subject": "数学",
        "question_type": "single_choice",
        "difficulty": "basic",
        "stem": "矩阵 AB 存在的条件是什么？",
        "options": ["A 的列数等于 B 的行数", "A 的行数等于 B 的列数", "两个矩阵必须相等", "任意矩阵都可以相乘"],
        "answer": "A",
        "analysis": "矩阵乘法要求前一个矩阵的列数等于后一个矩阵的行数。",
        "tags": ["矩阵", "线性代数"],
    }
    payload.update(overrides)
    response = client.post("/api/questions", headers=headers, json=payload)
    assert response.status_code == 201
    return response.json()


def test_question_crud_filters_and_options(client):
    headers = _auth_headers(client)
    question = _create_question(client, headers)

    list_response = client.get("/api/questions?subject=数学&difficulty=basic&status=draft", headers=headers)
    assert list_response.status_code == 200
    items = list_response.json()
    assert len(items) == 1
    assert items[0]["id"] == question["id"]
    assert items[0]["options"][0].startswith("A 的列数")
    assert items[0]["tags"] == ["矩阵", "线性代数"]

    patch_response = client.patch(
        f"/api/questions/{question['id']}",
        headers=headers,
        json={"difficulty": "medium", "analysis": "更新后的解析"},
    )
    assert patch_response.status_code == 200
    assert patch_response.json()["difficulty"] == "medium"
    assert patch_response.json()["analysis"] == "更新后的解析"


def test_question_scope_and_delete(client):
    owner_headers = _auth_headers(client, "teacher_question_owner")
    other_headers = _auth_headers(client, "teacher_question_other")
    question = _create_question(client, owner_headers)

    other_detail = client.get(f"/api/questions/{question['id']}", headers=other_headers)
    assert other_detail.status_code == 404

    delete_response = client.delete(f"/api/questions/{question['id']}", headers=owner_headers)
    assert delete_response.status_code == 204

    missing_response = client.get(f"/api/questions/{question['id']}", headers=owner_headers)
    assert missing_response.status_code == 404
```

- [ ] **Step 2: Run tests to verify they fail**

```powershell
cd backend
python -m pytest tests/test_questions.py -q
```

Expected:

- FAIL because `/api/questions` routes do not exist.

- [ ] **Step 3: Commit failing tests**

```powershell
git add backend/tests/test_questions.py
git commit -m "test: cover phase 3 question bank"
```

---

## Task 4: Question Bank Implementation

**Files:**
- Create: `backend/app/questions/models.py`
- Create: `backend/app/questions/schemas.py`
- Create: `backend/app/questions/service.py`
- Create: `backend/app/questions/router.py`
- Modify: `backend/app/main.py`

- [ ] **Step 1: Add question model**

Create `backend/app/questions/models.py`:

```python
from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class QuestionBankItem(Base):
    __tablename__ = "question_bank_items"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    course_id: Mapped[int | None] = mapped_column(ForeignKey("courses.id"), nullable=True, index=True)
    chapter_id: Mapped[int | None] = mapped_column(ForeignKey("chapters.id"), nullable=True, index=True)
    session_id: Mapped[int | None] = mapped_column(ForeignKey("lesson_sessions.id"), nullable=True, index=True)
    knowledge_point_id: Mapped[int | None] = mapped_column(ForeignKey("knowledge_points.id"), nullable=True, index=True)
    source_exercise_id: Mapped[int | None] = mapped_column(ForeignKey("exercises.id"), nullable=True)
    source_material_id: Mapped[int | None] = mapped_column(ForeignKey("materials.id"), nullable=True)
    title: Mapped[str] = mapped_column(String(255))
    subject: Mapped[str] = mapped_column(String(128), index=True)
    question_type: Mapped[str] = mapped_column(String(64), index=True)
    difficulty: Mapped[str] = mapped_column(String(64), index=True)
    stem: Mapped[str] = mapped_column(Text)
    options_json: Mapped[str] = mapped_column(Text, default="[]")
    answer: Mapped[str] = mapped_column(Text, default="")
    analysis: Mapped[str] = mapped_column(Text, default="")
    tags_json: Mapped[str] = mapped_column(Text, default="[]")
    status: Mapped[str] = mapped_column(String(32), default="draft", index=True)
    reviewer_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    review_comment: Mapped[str] = mapped_column(Text, default="")
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
```

- [ ] **Step 2: Add schemas**

Create `backend/app/questions/schemas.py`:

```python
from datetime import datetime

from pydantic import BaseModel, Field


class QuestionCreateRequest(BaseModel):
    course_id: int | None = None
    chapter_id: int | None = None
    session_id: int | None = None
    knowledge_point_id: int | None = None
    source_exercise_id: int | None = None
    source_material_id: int | None = None
    title: str = Field(min_length=1)
    subject: str = Field(min_length=1)
    question_type: str = Field(min_length=1)
    difficulty: str = Field(min_length=1)
    stem: str = Field(min_length=1)
    options: list[str] = Field(default_factory=list)
    answer: str = ""
    analysis: str = ""
    tags: list[str] = Field(default_factory=list)


class QuestionUpdateRequest(BaseModel):
    title: str | None = None
    subject: str | None = None
    question_type: str | None = None
    difficulty: str | None = None
    stem: str | None = None
    options: list[str] | None = None
    answer: str | None = None
    analysis: str | None = None
    tags: list[str] | None = None


class QuestionRead(BaseModel):
    id: int
    owner_id: int
    course_id: int | None
    chapter_id: int | None
    session_id: int | None
    knowledge_point_id: int | None
    source_exercise_id: int | None
    source_material_id: int | None
    title: str
    subject: str
    question_type: str
    difficulty: str
    stem: str
    options: list[str]
    answer: str
    analysis: str
    tags: list[str]
    status: str
    reviewer_id: int | None
    review_comment: str
    reviewed_at: datetime | None
    created_at: datetime
    updated_at: datetime
```

- [ ] **Step 3: Add service**

Create `backend/app/questions/service.py`:

```python
import json

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.models import User
from app.questions.models import QuestionBankItem
from app.questions.schemas import QuestionCreateRequest, QuestionRead, QuestionUpdateRequest


def encode_list(values: list[str]) -> str:
    return json.dumps([value.strip() for value in values if value.strip()], ensure_ascii=False)


def decode_list(value: str | None) -> list[str]:
    if not value:
        return []
    try:
        decoded = json.loads(value)
    except json.JSONDecodeError:
        return []
    return [str(item) for item in decoded if str(item).strip()] if isinstance(decoded, list) else []


def question_to_read(question: QuestionBankItem) -> QuestionRead:
    return QuestionRead(
        id=question.id,
        owner_id=question.owner_id,
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


def list_questions(db: Session, *, current_user: User, subject: str | None = None, difficulty: str | None = None, status: str | None = None) -> list[QuestionBankItem]:
    query = select(QuestionBankItem).where(QuestionBankItem.owner_id == current_user.id)
    if subject:
        query = query.where(QuestionBankItem.subject == subject)
    if difficulty:
        query = query.where(QuestionBankItem.difficulty == difficulty)
    if status:
        query = query.where(QuestionBankItem.status == status)
    return list(db.scalars(query.order_by(QuestionBankItem.updated_at.desc(), QuestionBankItem.id.desc())).all())


def get_owned_question(db: Session, *, question_id: int, current_user: User) -> QuestionBankItem | None:
    return db.scalar(select(QuestionBankItem).where(QuestionBankItem.id == question_id, QuestionBankItem.owner_id == current_user.id))


def create_question(db: Session, *, payload: QuestionCreateRequest, current_user: User) -> QuestionBankItem:
    question = QuestionBankItem(owner_id=current_user.id, **payload.model_dump(exclude={"options", "tags"}), options_json=encode_list(payload.options), tags_json=encode_list(payload.tags))
    db.add(question)
    db.flush()
    return question


def update_question(db: Session, *, question: QuestionBankItem, payload: QuestionUpdateRequest) -> QuestionBankItem:
    data = payload.model_dump(exclude_unset=True)
    if "options" in data:
        question.options_json = encode_list(data.pop("options"))
    if "tags" in data:
        question.tags_json = encode_list(data.pop("tags"))
    for field, value in data.items():
        setattr(question, field, value)
    db.flush()
    return question
```

- [ ] **Step 4: Add router**

Create `backend/app/questions/router.py`:

```python
from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from app.auth.models import User
from app.core.database import get_db
from app.core.deps import require_permission
from app.questions.schemas import QuestionCreateRequest, QuestionRead, QuestionUpdateRequest
from app.questions.service import create_question, get_owned_question, list_questions, question_to_read, update_question

router = APIRouter(prefix="/api/questions", tags=["questions"])


def question_or_404(db: Session, question_id: int, current_user: User):
    question = get_owned_question(db, question_id=question_id, current_user=current_user)
    if question is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Question not found")
    return question


@router.get("", response_model=list[QuestionRead])
def list_current_questions(subject: str | None = None, difficulty: str | None = None, status: str | None = None, current_user: User = Depends(require_permission("exercise:create")), db: Session = Depends(get_db)):
    return [question_to_read(item) for item in list_questions(db, current_user=current_user, subject=subject, difficulty=difficulty, status=status)]


@router.post("", response_model=QuestionRead, status_code=status.HTTP_201_CREATED)
def create_current_question(payload: QuestionCreateRequest, current_user: User = Depends(require_permission("exercise:create")), db: Session = Depends(get_db)):
    question = create_question(db, payload=payload, current_user=current_user)
    response = question_to_read(question)
    db.commit()
    return response


@router.get("/{question_id}", response_model=QuestionRead)
def get_question(question_id: int, current_user: User = Depends(require_permission("exercise:create")), db: Session = Depends(get_db)):
    return question_to_read(question_or_404(db, question_id, current_user))


@router.patch("/{question_id}", response_model=QuestionRead)
def patch_question(question_id: int, payload: QuestionUpdateRequest, current_user: User = Depends(require_permission("exercise:create")), db: Session = Depends(get_db)):
    question = update_question(db, question=question_or_404(db, question_id, current_user), payload=payload)
    response = question_to_read(question)
    db.commit()
    return response


@router.delete("/{question_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_question(question_id: int, current_user: User = Depends(require_permission("exercise:create")), db: Session = Depends(get_db)):
    db.delete(question_or_404(db, question_id, current_user))
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
```

- [ ] **Step 5: Register module**

Modify `backend/app/main.py`:

```python
from app.questions import models as questions_models  # noqa: F401
from app.questions.router import router as questions_router
```

Include:

```python
app.include_router(questions_router)
```

- [ ] **Step 6: Run tests**

```powershell
cd backend
python -m pytest tests/test_questions.py -q
```

Expected:

- PASS.

- [ ] **Step 7: Commit question bank**

```powershell
git add backend/app/questions backend/app/main.py
git commit -m "feat: add question bank"
```

---

## Task 5: Review Workflow Tests

**Files:**
- Create: `backend/tests/test_reviews.py`

- [ ] **Step 1: Write failing review tests**

Create `backend/tests/test_reviews.py`:

```python
def _auth_headers(client, username: str) -> dict[str, str]:
    client.post(
        "/api/auth/register",
        json={
            "username": username,
            "email": f"{username}@example.com",
            "password": "secret-password",
            "display_name": username,
        },
    )
    login = client.post("/api/auth/login", json={"username": username, "password": "secret-password"})
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


def _admin_headers(client, username: str = "admin_review") -> dict[str, str]:
    from sqlalchemy import select

    from app.auth.models import Role, User
    from app.core.database import get_session_local

    headers = _auth_headers(client, username)
    session_local = get_session_local()
    with session_local() as db:
        user = db.scalar(select(User).where(User.username == username))
        admin_role = db.scalar(select(Role).where(Role.name == "admin"))
        user.roles = [admin_role]
        db.commit()
    return headers


def _create_question(client, headers: dict[str, str]):
    response = client.post(
        "/api/questions",
        headers=headers,
        json={
            "title": "Review Question",
            "subject": "English",
            "question_type": "short_answer",
            "difficulty": "basic",
            "stem": "Explain letter format.",
            "options": [],
            "answer": "Greeting, body, closing.",
            "analysis": "Basic writing format.",
            "tags": [],
        },
    )
    assert response.status_code == 201
    return response.json()


def test_teacher_submits_question_and_manager_approves(client):
    teacher_headers = _auth_headers(client, "teacher_review_question")
    admin_headers = _admin_headers(client, "admin_review_question")
    question = _create_question(client, teacher_headers)

    submit = client.post(f"/api/questions/{question['id']}/submit-review", headers=teacher_headers)
    assert submit.status_code == 200
    assert submit.json()["status"] == "pending_review"

    pending = client.get("/api/reviews/pending", headers=admin_headers)
    assert pending.status_code == 200
    assert any(item["resource_type"] == "question" and item["resource_id"] == question["id"] for item in pending.json())

    approve = client.post(
        f"/api/reviews/question/{question['id']}/approve",
        headers=admin_headers,
        json={"comment": "Approved for class use."},
    )
    assert approve.status_code == 200
    assert approve.json()["status"] == "approved"
    assert approve.json()["review_comment"] == "Approved for class use."


def test_review_permission_and_invalid_transition(client):
    teacher_headers = _auth_headers(client, "teacher_review_denied")
    question = _create_question(client, teacher_headers)

    approve_without_permission = client.post(
        f"/api/reviews/question/{question['id']}/approve",
        headers=teacher_headers,
        json={"comment": "Should fail"},
    )
    assert approve_without_permission.status_code == 403

    admin_headers = _admin_headers(client, "admin_invalid_transition")
    invalid_approve = client.post(
        f"/api/reviews/question/{question['id']}/approve",
        headers=admin_headers,
        json={"comment": "Not submitted yet"},
    )
    assert invalid_approve.status_code == 400
```

- [ ] **Step 2: Run tests to verify they fail**

```powershell
cd backend
python -m pytest tests/test_reviews.py -q
```

Expected:

- FAIL because review routes and permission do not exist.

- [ ] **Step 3: Commit failing tests**

```powershell
git add backend/tests/test_reviews.py
git commit -m "test: cover phase 3 review workflow"
```

---

## Task 6: Review Workflow Implementation

**Files:**
- Create: `backend/app/reviews/schemas.py`
- Create: `backend/app/reviews/service.py`
- Create: `backend/app/reviews/router.py`
- Modify: `backend/app/lessons/models.py`
- Modify: `backend/app/lessons/schemas.py`
- Modify: `backend/app/lessons/router.py`
- Modify: `backend/app/questions/router.py`
- Modify: `backend/app/auth/permissions.py`
- Modify: `backend/app/core/database.py`
- Modify: `backend/app/main.py`

- [ ] **Step 1: Add permission**

Modify `backend/app/auth/permissions.py`:

```python
PERMISSION_CODES = [
    "lesson:create",
    "lesson:export",
    "exercise:create",
    "material:upload",
    "admin:user_manage",
    "admin:role_manage",
    "log:view",
    "review:manage",
]
```

Ensure `admin` uses `PERMISSION_CODES` and add `review:manage` to `teaching_manager`.

- [ ] **Step 2: Add lesson review columns**

Modify `backend/app/lessons/models.py` inside `Lesson`:

```python
review_status: Mapped[str] = mapped_column(String(32), default="draft", index=True)
reviewer_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
review_comment: Mapped[str] = mapped_column(Text, default="")
reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
```

- [ ] **Step 3: Add SQLite migration for lesson columns**

Modify `backend/app/core/database.py`, add `_apply_sqlite_lessons_review_migration`:

```python
def _apply_sqlite_lessons_review_migration(engine: Engine, inspector) -> None:
    if not inspector.has_table("lessons"):
        return
    columns = {column["name"] for column in inspector.get_columns("lessons")}
    migrations = {
        "review_status": "ALTER TABLE lessons ADD COLUMN review_status VARCHAR(32) NOT NULL DEFAULT 'draft'",
        "reviewer_id": "ALTER TABLE lessons ADD COLUMN reviewer_id INTEGER",
        "review_comment": "ALTER TABLE lessons ADD COLUMN review_comment TEXT NOT NULL DEFAULT ''",
        "reviewed_at": "ALTER TABLE lessons ADD COLUMN reviewed_at DATETIME",
    }
    with engine.begin() as connection:
        for column_name, statement in migrations.items():
            if column_name not in columns:
                connection.execute(text(statement))
```

Call it from `_apply_sqlite_compatibility_migrations`.

- [ ] **Step 4: Add review schemas**

Create `backend/app/reviews/schemas.py`:

```python
from datetime import datetime

from pydantic import BaseModel


class ReviewActionRequest(BaseModel):
    comment: str = ""


class ReviewableRead(BaseModel):
    resource_type: str
    resource_id: int
    title: str
    owner_id: int
    status: str
    subject: str | None = None
    created_at: datetime
    updated_at: datetime
```

- [ ] **Step 5: Add review service**

Create `backend/app/reviews/service.py`:

```python
from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.models import User
from app.lessons.models import Lesson
from app.logs.models import OperationLog
from app.questions.models import QuestionBankItem
from app.reviews.schemas import ReviewableRead


def submit_question_for_review(db: Session, *, question: QuestionBankItem) -> QuestionBankItem:
    if question.status not in {"draft", "rejected"}:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Question cannot be submitted from current status")
    question.status = "pending_review"
    db.add(OperationLog(user_id=question.owner_id, action="question.submit_review", resource="question", detail=str(question.id)))
    db.flush()
    return question


def list_pending_reviews(db: Session) -> list[ReviewableRead]:
    lessons = db.scalars(select(Lesson).where(Lesson.review_status == "pending_review")).all()
    questions = db.scalars(select(QuestionBankItem).where(QuestionBankItem.status == "pending_review")).all()
    items = [
        ReviewableRead(resource_type="lesson", resource_id=item.id, title=item.title, owner_id=item.owner_id, status=item.review_status, subject=item.subject, created_at=item.created_at, updated_at=item.updated_at)
        for item in lessons
    ]
    items.extend(
        ReviewableRead(resource_type="question", resource_id=item.id, title=item.title, owner_id=item.owner_id, status=item.status, subject=item.subject, created_at=item.created_at, updated_at=item.updated_at)
        for item in questions
    )
    return sorted(items, key=lambda item: (item.updated_at, item.resource_id), reverse=True)


def approve_resource(db: Session, *, resource_type: str, resource_id: int, reviewer: User, comment: str):
    resource = _get_review_resource(db, resource_type, resource_id)
    _require_pending(resource, resource_type)
    _set_review_fields(resource, resource_type, "approved", reviewer.id, comment)
    db.add(OperationLog(user_id=reviewer.id, action=f"{resource_type}.approve", resource=resource_type, detail=str(resource_id)))
    db.flush()
    return resource


def reject_resource(db: Session, *, resource_type: str, resource_id: int, reviewer: User, comment: str):
    resource = _get_review_resource(db, resource_type, resource_id)
    _require_pending(resource, resource_type)
    _set_review_fields(resource, resource_type, "rejected", reviewer.id, comment)
    db.add(OperationLog(user_id=reviewer.id, action=f"{resource_type}.reject", resource=resource_type, detail=str(resource_id)))
    db.flush()
    return resource


def _get_review_resource(db: Session, resource_type: str, resource_id: int):
    if resource_type == "lesson":
        resource = db.get(Lesson, resource_id)
    elif resource_type == "question":
        resource = db.get(QuestionBankItem, resource_id)
    else:
        resource = None
    if resource is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Review resource not found")
    return resource


def _require_pending(resource, resource_type: str) -> None:
    current = resource.review_status if resource_type == "lesson" else resource.status
    if current != "pending_review":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Resource is not pending review")


def _set_review_fields(resource, resource_type: str, next_status: str, reviewer_id: int, comment: str) -> None:
    if resource_type == "lesson":
        resource.review_status = next_status
    else:
        resource.status = next_status
    resource.reviewer_id = reviewer_id
    resource.review_comment = comment
    resource.reviewed_at = datetime.now(timezone.utc)
```

- [ ] **Step 6: Add review router**

Create `backend/app/reviews/router.py`:

```python
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.auth.models import User
from app.core.database import get_db
from app.core.deps import require_permission
from app.questions.service import question_to_read
from app.reviews.schemas import ReviewActionRequest, ReviewableRead
from app.reviews.service import approve_resource, list_pending_reviews, reject_resource

router = APIRouter(prefix="/api/reviews", tags=["reviews"])


@router.get("/pending", response_model=list[ReviewableRead])
def pending_reviews(current_user: User = Depends(require_permission("review:manage")), db: Session = Depends(get_db)):
    _ = current_user
    return list_pending_reviews(db)


@router.post("/{resource_type}/{resource_id}/approve")
def approve(resource_type: str, resource_id: int, payload: ReviewActionRequest, current_user: User = Depends(require_permission("review:manage")), db: Session = Depends(get_db)):
    resource = approve_resource(db, resource_type=resource_type, resource_id=resource_id, reviewer=current_user, comment=payload.comment)
    db.commit()
    if resource_type == "question":
        return question_to_read(resource)
    return resource


@router.post("/{resource_type}/{resource_id}/reject")
def reject(resource_type: str, resource_id: int, payload: ReviewActionRequest, current_user: User = Depends(require_permission("review:manage")), db: Session = Depends(get_db)):
    resource = reject_resource(db, resource_type=resource_type, resource_id=resource_id, reviewer=current_user, comment=payload.comment)
    db.commit()
    if resource_type == "question":
        return question_to_read(resource)
    return resource
```

- [ ] **Step 7: Add submit endpoint to question router**

Modify `backend/app/questions/router.py`:

```python
from app.reviews.service import submit_question_for_review


@router.post("/{question_id}/submit-review", response_model=QuestionRead)
def submit_question_review(question_id: int, current_user: User = Depends(require_permission("exercise:create")), db: Session = Depends(get_db)):
    question = submit_question_for_review(db, question=question_or_404(db, question_id, current_user))
    response = question_to_read(question)
    db.commit()
    return response
```

- [ ] **Step 8: Register reviews**

Modify `backend/app/main.py`:

```python
from app.reviews.router import router as reviews_router
app.include_router(reviews_router)
```

- [ ] **Step 9: Run review tests**

```powershell
cd backend
python -m pytest tests/test_reviews.py -q
```

Expected:

- PASS.

- [ ] **Step 10: Commit review workflow**

```powershell
git add backend/app/auth/permissions.py backend/app/core/database.py backend/app/lessons backend/app/questions backend/app/reviews backend/app/main.py
git commit -m "feat: add teaching research review workflow"
```

---

## Task 7: Lightweight Export Tests

**Files:**
- Create: `backend/tests/test_phase3_exports.py`

- [ ] **Step 1: Write failing export tests**

Create `backend/tests/test_phase3_exports.py`:

```python
from io import BytesIO

from docx import Document


def _auth_headers(client, username: str = "teacher_phase3_exports") -> dict[str, str]:
    client.post(
        "/api/auth/register",
        json={
            "username": username,
            "email": f"{username}@example.com",
            "password": "secret-password",
            "display_name": "Export Teacher",
        },
    )
    login = client.post("/api/auth/login", json={"username": username, "password": "secret-password"})
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


def _docx_text(response) -> str:
    document = Document(BytesIO(response.content))
    return "\n".join(paragraph.text for paragraph in document.paragraphs)


def test_export_course_outline_docx(client):
    headers = _auth_headers(client)
    course = client.post(
        "/api/courses",
        headers=headers,
        json={"title": "考研英语一基础班", "subject": "英语", "exam_type": "考研英语一", "description": "基础课程"},
    ).json()
    chapter = client.post(
        f"/api/courses/{course['id']}/chapters",
        headers=headers,
        json={"title": "书信写作", "summary": "小作文", "order_index": 1},
    ).json()
    client.post(
        f"/api/chapters/{chapter['id']}/sessions",
        headers=headers,
        json={"title": "建议信", "duration_minutes": 90, "teaching_goal": "掌握结构", "order_index": 1},
    )

    response = client.post(f"/api/exports/course/{course['id']}/outline-docx", headers=headers)

    assert response.status_code == 200
    assert response.content.startswith(b"PK")
    text = _docx_text(response)
    assert "考研英语一基础班" in text
    assert "书信写作" in text
    assert "建议信" in text


def test_export_question_package_docx(client):
    headers = _auth_headers(client, "teacher_question_export")
    question = client.post(
        "/api/questions",
        headers=headers,
        json={
            "title": "书信格式",
            "subject": "英语",
            "question_type": "short_answer",
            "difficulty": "basic",
            "stem": "建议信一般包括哪些部分？",
            "options": [],
            "answer": "写信目的、具体建议、结尾。",
            "analysis": "建议信要先说明目的，再给出建议。",
            "tags": ["小作文"],
        },
    ).json()

    response = client.post("/api/exports/questions/docx", headers=headers, json={"question_ids": [question["id"]]})

    assert response.status_code == 200
    text = _docx_text(response)
    assert "书信格式" in text
    assert "建议信一般包括哪些部分" in text
    assert "写信目的" in text
```

- [ ] **Step 2: Run tests to verify they fail**

```powershell
cd backend
python -m pytest tests/test_phase3_exports.py -q
```

Expected:

- FAIL because export endpoints do not exist.

- [ ] **Step 3: Commit failing tests**

```powershell
git add backend/tests/test_phase3_exports.py
git commit -m "test: cover phase 3 exports"
```

---

## Task 8: Lightweight Export Implementation

**Files:**
- Modify: `backend/app/exports/service.py`
- Modify: `backend/app/exports/router.py`
- Create or modify: `backend/app/exports/schemas.py`

- [ ] **Step 1: Add export schema**

Modify `backend/app/exports/schemas.py`:

```python
from pydantic import BaseModel, Field


class QuestionPackageExportRequest(BaseModel):
    question_ids: list[int] = Field(min_length=1)
```

- [ ] **Step 2: Add course outline export service**

Modify `backend/app/exports/service.py`:

```python
def export_course_outline_docx(db: Session, *, course, current_user) -> Path:
    document = Document()
    document.add_heading(course.title, level=1)
    document.add_paragraph(f"学科：{course.subject}")
    document.add_paragraph(f"考试类型：{course.exam_type}")
    if course.description:
        document.add_paragraph(f"课程说明：{course.description}")
    document.add_heading("章节与课次", level=2)
    for chapter in course.chapters:
        document.add_heading(chapter.title, level=3)
        if chapter.summary:
            document.add_paragraph(chapter.summary)
        for session in chapter.sessions:
            document.add_paragraph(f"{session.order_index}. {session.title}（{session.duration_minutes} 分钟）")
            if session.teaching_goal:
                document.add_paragraph(f"教学目标：{session.teaching_goal}")
    document.add_heading("知识点", level=2)
    for point in course.knowledge_points:
        document.add_paragraph(f"{point.name}：{point.description or point.difficulty}")
    return _save_export_document(db, document=document, resource_type="course", resource_id=course.id, current_user=current_user)
```

Use existing export helper patterns. If no `_save_export_document` exists, extract the repeated save/record logic already used by `export_lesson_docx` and `export_exercise_docx`.

- [ ] **Step 3: Add question package export service**

Modify `backend/app/exports/service.py`:

```python
def export_question_package_docx(db: Session, *, questions: list, current_user) -> Path:
    document = Document()
    document.add_heading("练习题包", level=1)
    for index, question in enumerate(questions, start=1):
        document.add_heading(f"{index}. {question.title}", level=2)
        document.add_paragraph(question.stem)
        for option in decode_list(question.options_json):
            document.add_paragraph(option)
        document.add_paragraph(f"答案：{question.answer}")
        if question.analysis:
            document.add_paragraph(f"解析：{question.analysis}")
    return _save_export_document(db, document=document, resource_type="question_package", resource_id=0, current_user=current_user)
```

Import `decode_list` from `app.questions.service`.

- [ ] **Step 4: Add export routes**

Modify `backend/app/exports/router.py`:

```python
from app.courses.service import get_owned_course
from app.exports.schemas import QuestionPackageExportRequest
from app.exports.service import export_course_outline_docx, export_question_package_docx
from app.questions.service import get_owned_question


@router.post("/course/{course_id}/outline-docx")
def export_course_outline(course_id: int, current_user: User = Depends(require_permission("lesson:export")), db: Session = Depends(get_db)) -> FileResponse:
    course = get_owned_course(db, course_id=course_id, current_user=current_user)
    if course is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Course not found")
    file_path = export_course_outline_docx(db, course=course, current_user=current_user)
    db.commit()
    return FileResponse(file_path, media_type=DOCX_MEDIA_TYPE, filename=file_path.name, content_disposition_type="attachment")


@router.post("/questions/docx")
def export_question_package(payload: QuestionPackageExportRequest, current_user: User = Depends(require_permission("lesson:export")), db: Session = Depends(get_db)) -> FileResponse:
    questions = []
    for question_id in payload.question_ids:
        question = get_owned_question(db, question_id=question_id, current_user=current_user)
        if question is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Question not found")
        questions.append(question)
    file_path = export_question_package_docx(db, questions=questions, current_user=current_user)
    db.commit()
    return FileResponse(file_path, media_type=DOCX_MEDIA_TYPE, filename=file_path.name, content_disposition_type="attachment")
```

- [ ] **Step 5: Run export tests**

```powershell
cd backend
python -m pytest tests/test_phase3_exports.py -q
```

Expected:

- PASS.

- [ ] **Step 6: Commit exports**

```powershell
git add backend/app/exports backend/tests/test_phase3_exports.py
git commit -m "feat: add phase 3 docx exports"
```

---

## Task 9: Frontend Routes and Pages

**Files:**
- Create: `frontend/src/pages/CoursesPage.vue`
- Create: `frontend/src/pages/QuestionBankPage.vue`
- Create: `frontend/src/pages/ReviewQueuePage.vue`
- Modify: `frontend/src/router.ts`
- Modify: `frontend/src/layouts/WorkbenchLayout.vue`
- Modify: `frontend/src/router.test.ts`

- [ ] **Step 1: Add route tests**

Modify `frontend/src/router.test.ts` to assert routes exist:

```ts
it('includes phase 3 workflow routes', () => {
  const childPaths = routes
    .find((route) => route.path === '/dashboard')
    ?.children?.map((route) => route.path)

  expect(childPaths).toContain('courses')
  expect(childPaths).toContain('questions')
  expect(childPaths).toContain('reviews')
})
```

- [ ] **Step 2: Run frontend tests to verify failure**

```powershell
cd frontend
npm.cmd test
```

Expected:

- FAIL because routes do not exist.

- [ ] **Step 3: Add simple page components**

Create `frontend/src/pages/CoursesPage.vue`:

```vue
<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { api } from '../api/client'

interface Course {
  id: number
  title: string
  subject: string
  exam_type: string
  description: string
  status: string
}

const courses = ref<Course[]>([])
const form = reactive({ title: '', subject: '', exam_type: '', description: '' })
const error = ref('')

async function loadCourses() {
  courses.value = await api<Course[]>('/api/courses')
}

async function createCourse() {
  error.value = ''
  try {
    await api<Course>('/api/courses', {
      method: 'POST',
      body: JSON.stringify({ ...form, status: 'draft' }),
    })
    form.title = ''
    form.subject = ''
    form.exam_type = ''
    form.description = ''
    await loadCourses()
  } catch (err) {
    error.value = err instanceof Error ? err.message : '课程创建失败'
  }
}

onMounted(loadCourses)
</script>

<template>
  <section class="page">
    <header>
      <p class="eyebrow">课程体系</p>
      <h1>课程体系管理</h1>
      <p>管理课程、章节、课次和知识点，沉淀机构标准课程结构。</p>
    </header>
    <p v-if="error" class="alert">{{ error }}</p>
    <form class="panel" @submit.prevent="createCourse">
      <input v-model.trim="form.title" required placeholder="课程名称" />
      <input v-model.trim="form.subject" required placeholder="学科" />
      <input v-model.trim="form.exam_type" placeholder="考试类型" />
      <textarea v-model.trim="form.description" placeholder="课程说明" />
      <button type="submit">创建课程</button>
    </form>
    <section class="panel">
      <h2>课程列表</h2>
      <p v-if="!courses.length">暂无课程。</p>
      <ul>
        <li v-for="course in courses" :key="course.id">
          <strong>{{ course.title }}</strong>
          <span>{{ course.subject }} · {{ course.exam_type || '未填考试类型' }} · {{ course.status }}</span>
        </li>
      </ul>
    </section>
  </section>
</template>
```

Use existing page CSS patterns from `MaterialsPage.vue`.

Create `frontend/src/pages/QuestionBankPage.vue` with form fields matching `QuestionCreateRequest` and a list from `/api/questions`.

Create `frontend/src/pages/ReviewQueuePage.vue` with:

- `GET /api/reviews/pending`
- approve button calling `/api/reviews/{resource_type}/{resource_id}/approve`
- reject button calling `/api/reviews/{resource_type}/{resource_id}/reject`

- [ ] **Step 4: Register routes**

Modify `frontend/src/router.ts`:

```ts
import CoursesPage from './pages/CoursesPage.vue'
import QuestionBankPage from './pages/QuestionBankPage.vue'
import ReviewQueuePage from './pages/ReviewQueuePage.vue'
```

Add children:

```ts
{ path: 'courses', component: CoursesPage },
{ path: 'questions', component: QuestionBankPage },
{ path: 'reviews', component: ReviewQueuePage },
```

- [ ] **Step 5: Add nav items**

Modify `frontend/src/layouts/WorkbenchLayout.vue` nav items:

```ts
{ label: '课程体系', to: '/dashboard/courses' },
{ label: '题库', to: '/dashboard/questions' },
{ label: '教研审核', to: '/dashboard/reviews' },
```

- [ ] **Step 6: Run frontend tests and build**

```powershell
cd frontend
npm.cmd test
npm.cmd run build
```

Expected:

- Tests pass.
- Build passes.

- [ ] **Step 7: Commit frontend workflow pages**

```powershell
git add frontend/src/router.ts frontend/src/router.test.ts frontend/src/layouts/WorkbenchLayout.vue frontend/src/pages/CoursesPage.vue frontend/src/pages/QuestionBankPage.vue frontend/src/pages/ReviewQueuePage.vue
git commit -m "feat: add phase 3 frontend workflow pages"
```

---

## Task 10: Full Verification and Documentation

**Files:**
- Modify: `README.md`
- Optionally create: `docs/phase3-demo-script.md`

- [ ] **Step 1: Add README summary**

Add a short Phase 3 section to `README.md`:

```markdown
## 三阶段能力

- 课程体系：课程、章节、课次、知识点。
- 题库管理：结构化题目保存、筛选、编辑。
- 教研审核：草稿、待审核、通过、驳回。
- 轻量导出：课程大纲和练习题包 DOCX。
```

- [ ] **Step 2: Add demo script**

Create `docs/phase3-demo-script.md`:

```markdown
# Phase 3 Demo Script

1. Start containers with `docker compose up --build`.
2. Log in as teacher.
3. Create a course.
4. Add a chapter, session, and knowledge point.
5. Create a question-bank item.
6. Submit the question for review.
7. Log in as admin or teaching manager.
8. Approve the question.
9. Export a question package DOCX.
10. Show `/api/reviews/pending`, `/api/questions`, and `/api/courses` in Swagger UI.
```

- [ ] **Step 3: Run backend full tests**

```powershell
cd backend
python -m pytest -q
```

Expected:

- All tests pass. Existing pytest cache warnings on this Windows workspace are acceptable if tests pass.

- [ ] **Step 4: Run frontend tests**

```powershell
cd frontend
npm.cmd test
```

Expected:

- All Vitest tests pass.

- [ ] **Step 5: Run frontend build**

```powershell
cd frontend
npm.cmd run build
```

Expected:

- TypeScript and Vite build pass.

- [ ] **Step 6: Validate Docker config**

```powershell
docker compose config
```

Expected:

- Compose config renders successfully.
- Do not paste config output publicly if `backend/.env` contains a real API key.

- [ ] **Step 7: Check git status**

```powershell
git status --short
```

Expected:

- Only intended doc updates remain before commit, or clean after commit.

- [ ] **Step 8: Commit docs**

```powershell
git add README.md docs/phase3-demo-script.md
git commit -m "docs: add phase 3 demo guide"
```

---

## Self-Review Checklist

- Spec coverage:
  - Course hierarchy: Tasks 1-2.
  - Question bank: Tasks 3-4.
  - Review workflow: Tasks 5-6.
  - Lightweight DOCX exports: Tasks 7-8.
  - Frontend pages: Task 9.
  - Documentation and verification: Task 10.
- Scope control:
  - No student accounts.
  - No student analytics.
  - No multi-tenant organization model.
  - No template designer.
  - No vector database.
- Testing:
  - Every backend feature starts with failing pytest tests.
  - Frontend route test added before route implementation.
  - Full backend/frontend verification happens at the end.
