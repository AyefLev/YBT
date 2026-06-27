from datetime import datetime

from pydantic import BaseModel, Field

from app.ai.schemas import AIResult, AIReview
from app.compliance.schemas import ComplianceCheckResponse


class ExerciseGenerateRequest(BaseModel):
    course_id: int | None = None
    chapter_id: int | None = None
    session_id: int | None = None
    knowledge_point_id: int | None = None
    lesson_id: int | None = None
    title: str = Field(min_length=1)
    subject: str = Field(min_length=1)
    knowledge_point: str = Field(min_length=1)
    question_type: str = Field(min_length=1)
    difficulty: str = Field(min_length=1)
    count: int = Field(gt=0)
    use_materials: bool = False
    material_ids: list[int] = Field(default_factory=list)
    prompt_template: str = ""
    output_format: str = ""
    multi_agent_review: bool | None = None
    auto_revise: bool = True


class ExerciseCreateRequest(BaseModel):
    course_id: int | None = None
    chapter_id: int | None = None
    session_id: int | None = None
    knowledge_point_id: int | None = None
    lesson_id: int | None = None
    title: str = Field(min_length=1)
    subject: str = Field(min_length=1)
    knowledge_point: str = Field(min_length=1)
    question_type: str = Field(min_length=1)
    difficulty: str = Field(min_length=1)
    content: str = Field(min_length=1)
    material_ids: list[int] = Field(default_factory=list)
    prompt_template: str = ""
    output_format: str = ""
    change_note: str = ""


class ExerciseRead(BaseModel):
    id: int
    owner_id: int
    owner_name: str = ""
    owner_username: str = ""
    course_id: int | None = None
    chapter_id: int | None = None
    session_id: int | None = None
    knowledge_point_id: int | None = None
    lesson_id: int | None = None
    title: str
    subject: str
    knowledge_point: str
    question_type: str
    difficulty: str
    current_content: str
    material_ids: list[int] = Field(default_factory=list)
    prompt_template: str = ""
    output_format: str = ""
    compliance_level: str
    created_at: datetime
    updated_at: datetime


class ExerciseVersionRead(BaseModel):
    id: int
    exercise_id: int
    version_no: int
    content: str
    change_note: str
    created_at: datetime


class ExerciseRestoreRequest(BaseModel):
    version_id: int


class ExerciseReference(BaseModel):
    id: int
    material_id: int
    material_title: str | None = None
    source: str | None = None
    content: str
    page_no: int | None
    slide_no: int | None
    score: float


class ExerciseGenerateResponse(BaseModel):
    content: str
    references: list[ExerciseReference]
    provider_status: AIResult
    compliance: ComplianceCheckResponse
    review: AIReview | None = None
