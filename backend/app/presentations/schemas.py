from pydantic import BaseModel, Field

from app.ai.schemas import AIResult


class PresentationGenerateRequest(BaseModel):
    template_id: int | None = None
    style: str = ""
    include_exercises: bool = True
    slide_count: int | None = Field(default=None, ge=1, le=30)
    description: str = Field(default="", max_length=2000)


class PresentationSlideRead(BaseModel):
    slide_no: int
    title: str
    bullets: list[str] = Field(default_factory=list)
    speaker_notes: str = ""
    visual_prompt: str = ""


class PresentationGenerateResponse(BaseModel):
    lesson_id: int
    status: str
    queued: bool
    message: str
    slides: list[PresentationSlideRead] = Field(default_factory=list)
    provider_status: AIResult | None = None
    export_id: int | None = None
    download_url: str | None = None
    filename: str | None = None
