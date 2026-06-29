from datetime import datetime

from pydantic import BaseModel, Field

from app.ai.schemas import AIResult, AIReview
from app.compliance.schemas import ComplianceCheckResponse


class LessonGenerateRequest(BaseModel):
    course_id: int | None = None
    chapter_id: int | None = None
    session_id: int | None = None
    knowledge_point_id: int | None = None
    subject: str = Field(min_length=1)
    chapter: str = Field(min_length=1)
    stage: str = Field(min_length=1)
    duration_minutes: int = Field(gt=0)
    student_level: str = Field(min_length=1)
    teaching_goal: str = Field(min_length=1)
    use_materials: bool = False
    material_ids: list[int] = Field(default_factory=list)
    reference_count: int = Field(default=5, ge=1, le=20)
    retrieval_focus: str = "balanced"
    prompt_template: str = ""
    output_format: str = ""
    web_search_enabled: bool = False
    multi_agent_review: bool | None = None
    auto_revise: bool = True


class LessonCreateRequest(BaseModel):
    course_id: int | None = None
    chapter_id: int | None = None
    session_id: int | None = None
    knowledge_point_id: int | None = None
    title: str = Field(min_length=1)
    subject: str = Field(min_length=1)
    chapter: str = Field(min_length=1)
    stage: str = Field(min_length=1)
    duration_minutes: int = Field(gt=0)
    student_level: str = Field(min_length=1)
    content: str = Field(min_length=1)
    material_ids: list[int] = Field(default_factory=list)
    prompt_template: str = ""
    output_format: str = ""
    change_note: str = ""


class LessonRead(BaseModel):
    id: int
    owner_id: int
    owner_name: str = ""
    owner_username: str = ""
    course_id: int | None = None
    chapter_id: int | None = None
    session_id: int | None = None
    knowledge_point_id: int | None = None
    title: str
    subject: str
    chapter: str
    stage: str
    duration_minutes: int
    student_level: str
    current_content: str
    material_ids: list[int] = Field(default_factory=list)
    prompt_template: str = ""
    output_format: str = ""
    compliance_level: str
    review_status: str
    reviewer_id: int | None
    review_comment: str
    reviewed_at: datetime | None
    created_at: datetime
    updated_at: datetime


class LessonVersionRead(BaseModel):
    id: int
    lesson_id: int
    version_no: int
    content: str
    change_note: str
    created_at: datetime


class LessonRestoreRequest(BaseModel):
    version_id: int


class LessonReference(BaseModel):
    id: int
    material_id: int
    material_title: str | None = None
    source: str | None = None
    content: str
    page_no: int | None
    slide_no: int | None
    score: float


class LessonGenerateResponse(BaseModel):
    content: str
    references: list[LessonReference]
    provider_status: AIResult
    compliance: ComplianceCheckResponse
    review: AIReview | None = None
