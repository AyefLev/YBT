from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ClassroomCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    description: str = ""
    course_id: int | None = None


class ClassroomUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None
    course_id: int | None = None
    status: str | None = None


class ClassroomJoinRequest(BaseModel):
    invite_code: str = Field(min_length=3, max_length=32)


class ClassroomRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    teacher_id: int
    teacher_name: str = ""
    teacher_username: str = ""
    course_id: int | None
    name: str
    description: str
    invite_code: str
    status: str
    student_count: int = 0
    assignment_count: int = 0
    created_at: datetime
    updated_at: datetime


class ClassroomStudentRead(BaseModel):
    id: int
    username: str
    email: str
    display_name: str
    enrollment_status: str
    joined_at: datetime


class AssignmentCreateRequest(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    description: str = ""
    instructions: str = ""
    exercise_id: int | None = None
    material_id: int | None = None
    due_at: datetime | None = None
    status: str = "published"


class AssignmentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    classroom_id: int
    title: str
    description: str
    instructions: str
    exercise_id: int | None
    material_id: int | None
    due_at: datetime | None
    status: str
    submission_status: str | None = None
    score: int | None = None
    feedback: str = ""
    created_at: datetime
    updated_at: datetime


class AssignmentSubmitRequest(BaseModel):
    content: str = Field(min_length=1)


class SubmissionGradeRequest(BaseModel):
    score: int = Field(ge=0, le=100)
    feedback: str = ""


class AssignmentSubmissionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    assignment_id: int
    student_id: int
    student_name: str = ""
    content: str
    status: str
    score: int | None
    feedback: str
    submitted_at: datetime
    graded_at: datetime | None
