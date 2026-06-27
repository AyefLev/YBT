from datetime import datetime

from pydantic import BaseModel, Field, ValidationInfo, field_validator

QUESTION_TYPES = {
    "single_choice",
    "multiple_choice",
    "fill_blank",
    "short_answer",
    "true_false",
}
DIFFICULTIES = {"basic", "medium", "advanced"}
QUESTION_STATUSES = {"draft", "pending_review", "approved", "rejected"}


def _normalize_enum(value: str, allowed: set[str], field_name: str) -> str:
    normalized = value.strip().lower()
    if normalized not in allowed:
        raise ValueError(f"{field_name} is not supported")
    return normalized


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

    @field_validator("question_type")
    @classmethod
    def validate_question_type(cls, value: str) -> str:
        return _normalize_enum(value, QUESTION_TYPES, "question_type")

    @field_validator("difficulty")
    @classmethod
    def validate_difficulty(cls, value: str) -> str:
        return _normalize_enum(value, DIFFICULTIES, "difficulty")


class QuestionUpdateRequest(BaseModel):
    title: str | None = Field(default=None, min_length=1)
    subject: str | None = Field(default=None, min_length=1)
    question_type: str | None = Field(default=None, min_length=1)
    difficulty: str | None = Field(default=None, min_length=1)
    stem: str | None = Field(default=None, min_length=1)
    options: list[str] | None = None
    answer: str | None = None
    analysis: str | None = None
    tags: list[str] | None = None

    @field_validator(
        "title",
        "subject",
        "question_type",
        "difficulty",
        "stem",
        "answer",
        "analysis",
        mode="before",
    )
    @classmethod
    def reject_explicit_null(cls, value: str | None, info: ValidationInfo) -> str:
        if value is None:
            raise ValueError(f"{info.field_name} may not be null")
        return value

    @field_validator("question_type")
    @classmethod
    def validate_question_type(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return _normalize_enum(value, QUESTION_TYPES, "question_type")

    @field_validator("difficulty")
    @classmethod
    def validate_difficulty(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return _normalize_enum(value, DIFFICULTIES, "difficulty")


class QuestionRead(BaseModel):
    id: int
    owner_id: int
    owner_name: str = ""
    owner_username: str = ""
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
