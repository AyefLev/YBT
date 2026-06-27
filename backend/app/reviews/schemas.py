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
