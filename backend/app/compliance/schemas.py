from pydantic import BaseModel, Field


class ComplianceCheckRequest(BaseModel):
    content_type: str = Field(min_length=1)
    content: str = Field(min_length=1)
    content_id: str | None = None


class ComplianceCheckResponse(BaseModel):
    risk_level: str
    matched_terms: list[str]
    suggestions: list[str]
