from datetime import datetime

from pydantic import BaseModel, ConfigDict


class OperationLogRead(BaseModel):
    id: int
    user_id: int | None
    action: str
    resource: str | None
    detail: str | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ModelLogRead(BaseModel):
    id: int
    user_id: int | None
    task_type: str | None
    provider: str
    model: str
    prompt_tokens: int | None
    completion_tokens: int | None
    latency_ms: int | None
    success: bool
    fallback_used: bool
    error_message: str | None
    status: str
    error: str | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class JobLogRead(BaseModel):
    id: int
    job_type: str
    status: str
    resource_type: str | None
    resource_id: int | None
    user_id: int | None
    detail: str | None
    error_message: str | None
    duration_ms: int | None
    started_at: datetime | None
    finished_at: datetime | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class RecentErrorRead(BaseModel):
    source: str
    task_type: str | None = None
    message: str
    created_at: datetime


class LogSummaryRead(BaseModel):
    model_total: int
    model_success: int
    model_failed: int
    mock_fallbacks: int
    average_latency_ms: int
    job_total: int
    job_failed: int
    operation_total: int
    recent_errors: list[RecentErrorRead]


class HealthComponentRead(BaseModel):
    status: str
    kind: str
    message: str = ""


class ModelHealthRead(BaseModel):
    text_model: str
    generate_model: str
    review_model: str
    revise_model: str
    vision_model: str | None
    api_key_configured: bool
    vision_api_key_configured: bool
    multi_agent_review: bool
    mock_on_failure: bool


class ObservabilityHealthRead(BaseModel):
    model_total: int
    model_failed: int
    job_total: int
    job_failed: int
    operation_total: int


class DemoHealthRead(BaseModel):
    docker_ready_items: list[str]
    suggested_next_action: str


class SystemHealthRead(BaseModel):
    overall_status: str
    database: HealthComponentRead
    cache: HealthComponentRead
    vector_store: HealthComponentRead
    models: ModelHealthRead
    observability: ObservabilityHealthRead
    demo: DemoHealthRead
