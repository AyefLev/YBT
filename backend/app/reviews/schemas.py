from datetime import datetime

from pydantic import BaseModel, Field


class ReviewActionRequest(BaseModel):
    comment: str = ""


class ReviewableRead(BaseModel):
    resource_type: str
    resource_id: int
    title: str
    owner_id: int
    owner_name: str = ""
    owner_username: str = ""
    status: str
    subject: str | None = None
    detail: dict[str, object] = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime
