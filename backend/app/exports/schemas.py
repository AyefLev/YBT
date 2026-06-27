from datetime import datetime

from pydantic import BaseModel, Field


class ExportResponse(BaseModel):
    file_path: str


class ExportRecordRead(BaseModel):
    id: int
    resource_type: str
    resource_id: int
    file_path: str
    exported_by: int
    created_at: datetime


class QuestionPackageExportRequest(BaseModel):
    question_ids: list[int] = Field(min_length=1)
