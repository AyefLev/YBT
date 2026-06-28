from pydantic import BaseModel


class AIResult(BaseModel):
    content: str
    provider: str
    model: str
    fallback_used: bool
    error_message: str | None = None


class AIReview(BaseModel):
    enabled: bool
    status: str
    reviewer_model: str
    warnings: list[str]
    suggestions: list[str]
    raw_review: str
    revised_content: str | None = None


class ModelCapabilityResponse(BaseModel):
    text_model: str
    text_configured: bool
    generate_model: str
    generate_configured: bool
    review_model: str
    review_configured: bool
    revise_model: str
    revise_configured: bool
    vision_model: str
    vision_configured: bool
    embedding_model: str
    embedding_configured: bool
    mock_on_failure: bool
    multi_agent_review: bool


class ModelConnectivityCheck(BaseModel):
    role: str
    model: str
    configured: bool
    status: str
    latency_ms: int | None = None
    message: str = ""


class ModelConnectivityResponse(BaseModel):
    probe_enabled: bool
    checks: list[ModelConnectivityCheck]


class VisionAnalysisResponse(BaseModel):
    content: str
    provider_status: AIResult
