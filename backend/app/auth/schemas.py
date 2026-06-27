from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

USER_ROLE_CHOICES = {"teacher", "student"}
ACCOUNT_STATUSES = {"approved", "pending", "rejected"}


class UserRegister(BaseModel):
    username: str = Field(min_length=1, max_length=64)
    email: EmailStr
    password: str = Field(min_length=8)
    display_name: str = Field(min_length=1, max_length=128)
    role: str = "teacher"
    apply_for_teacher_review: bool = False
    application_note: str = ""

    @field_validator("role")
    @classmethod
    def validate_role(cls, value: str) -> str:
        normalized = value.strip().lower()
        if normalized not in USER_ROLE_CHOICES:
            raise ValueError("role must be teacher or student")
        return normalized


class UserLogin(BaseModel):
    username: str
    password: str


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserRead(BaseModel):
    id: int
    username: str
    email: EmailStr
    display_name: str
    is_active: bool
    requested_role: str = "teacher"
    account_status: str = "approved"
    review_note: str = ""
    reviewed_by_id: int | None = None
    reviewed_at: datetime | None = None
    roles: list[str]
    permissions: list[str] = []

    model_config = ConfigDict(from_attributes=True)


class UserCreate(BaseModel):
    username: str = Field(min_length=1, max_length=64)
    email: EmailStr
    password: str = Field(min_length=8)
    display_name: str = Field(min_length=1, max_length=128)
    roles: list[str] = Field(default_factory=lambda: ["student"])
    is_active: bool = True
    account_status: str = "approved"
    requested_role: str = "student"

    @field_validator("account_status")
    @classmethod
    def validate_account_status(cls, value: str) -> str:
        normalized = value.strip().lower()
        if normalized not in ACCOUNT_STATUSES:
            raise ValueError("account_status must be approved, pending, or rejected")
        return normalized


class UserUpdate(BaseModel):
    email: EmailStr | None = None
    display_name: str | None = Field(default=None, min_length=1, max_length=128)
    is_active: bool | None = None
    account_status: str | None = None
    requested_role: str | None = None
    review_note: str | None = None

    @field_validator("account_status")
    @classmethod
    def validate_optional_account_status(cls, value: str | None) -> str | None:
        if value is None:
            return value
        normalized = value.strip().lower()
        if normalized not in ACCOUNT_STATUSES:
            raise ValueError("account_status must be approved, pending, or rejected")
        return normalized


class TeacherReviewRequest(BaseModel):
    note: str = ""
