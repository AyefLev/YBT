from pydantic import BaseModel


class PresentationGenerateRequest(BaseModel):
    template_id: int | None = None
    style: str = ""
    include_exercises: bool = True


class PresentationGenerateResponse(BaseModel):
    lesson_id: int
    status: str
    queued: bool
    message: str
