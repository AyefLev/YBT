from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, ValidationInfo, field_validator

COURSE_STATUSES = {"draft", "pending_review", "active", "archived"}
KNOWLEDGE_POINT_DIFFICULTIES = {"basic", "medium", "advanced"}


def _normalize_status(value: str) -> str:
    normalized = value.strip().lower()
    if normalized not in COURSE_STATUSES:
        raise ValueError("status must be draft, pending_review, active, or archived")
    return normalized


class CourseCreateRequest(BaseModel):
    title: str = Field(min_length=1)
    subject: str = Field(min_length=1)
    exam_type: str = Field(min_length=1)
    description: str = ""
    status: str = Field(default="draft", min_length=1)

    @field_validator("status")
    @classmethod
    def validate_status(cls, value: str) -> str:
        return _normalize_status(value)


class CourseUpdateRequest(BaseModel):
    title: str | None = Field(default=None, min_length=1)
    subject: str | None = Field(default=None, min_length=1)
    exam_type: str | None = Field(default=None, min_length=1)
    description: str | None = None
    status: str | None = Field(default=None, min_length=1)

    @field_validator("title", "subject", "exam_type", "description", "status", mode="before")
    @classmethod
    def reject_explicit_null(cls, value: str | None, info: ValidationInfo) -> str:
        if value is None:
            raise ValueError(f"{info.field_name} may not be null")
        return value

    @field_validator("status")
    @classmethod
    def validate_status(cls, value: str) -> str:
        return _normalize_status(value)


class ChapterCreateRequest(BaseModel):
    title: str = Field(min_length=1)
    summary: str = ""
    order_index: int = 0


class LessonSessionCreateRequest(BaseModel):
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

    @field_validator("difficulty")
    @classmethod
    def normalize_difficulty(cls, value: str) -> str:
        normalized = value.strip().lower()
        if normalized not in KNOWLEDGE_POINT_DIFFICULTIES:
            return "basic"
        return normalized


class LessonSessionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    course_id: int
    chapter_id: int
    title: str
    duration_minutes: int
    teaching_goal: str
    order_index: int
    lesson_id: int | None = None
    created_at: datetime
    updated_at: datetime


class ChapterRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    course_id: int
    title: str
    summary: str
    order_index: int
    sessions: list[LessonSessionRead] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime


class KnowledgePointRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    course_id: int
    chapter_id: int | None
    session_id: int | None
    name: str
    description: str
    difficulty: str
    created_at: datetime
    updated_at: datetime


class CourseRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    owner_id: int
    owner_name: str = ""
    owner_username: str = ""
    title: str
    subject: str
    exam_type: str
    description: str
    status: str
    created_at: datetime
    updated_at: datetime


class CourseDetailRead(CourseRead):
    chapters: list[ChapterRead] = Field(default_factory=list)
    knowledge_points: list[KnowledgePointRead] = Field(default_factory=list)


class TeachingAssetRead(BaseModel):
    asset_type: str
    id: int
    title: str
    owner_id: int | None = None
    owner_name: str = ""
    resource_scope: str = ""
    status: str = ""
    course_id: int | None = None
    chapter_id: int | None = None
    session_id: int | None = None
    knowledge_point_id: int | None = None
    updated_at: datetime | None = None
    created_at: datetime | None = None


class CourseAssetsRead(BaseModel):
    course_id: int
    assets: list[TeachingAssetRead] = Field(default_factory=list)
