from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


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
    api_role: str = ""
    api_base_url: str = ""
    model: str
    prompt_tokens: int | None
    completion_tokens: int | None
    estimated_cost: float = 0.0
    cost_currency: str = "CNY"
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
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    estimated_cost: float
    cost_currency: str = "CNY"
    average_latency_ms: int
    job_total: int
    job_failed: int
    operation_total: int
    recent_errors: list[RecentErrorRead]


class TokenUsageRead(BaseModel):
    user_id: int | None
    username: str = ""
    display_name: str = ""
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    estimated_cost: float = 0.0
    cost_currency: str = "CNY"
    call_count: int


class ModelUsageRead(BaseModel):
    api_role: str
    api_base_url: str
    model: str
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    estimated_cost: float = 0.0
    cost_currency: str = "CNY"
    call_count: int


class DailyUsageRead(BaseModel):
    day: str
    group_key: str
    group_label: str
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    estimated_cost: float = 0.0
    cost_currency: str = "CNY"
    call_count: int


class HealthComponentRead(BaseModel):
    status: str
    kind: str
    message: str = ""


class ModelHealthRead(BaseModel):
    text_model: str
    generate_model: str
    generate_configured: bool = False
    review_model: str
    review_configured: bool = False
    revise_model: str
    revise_configured: bool = False
    vision_model: str | None
    vision_configured: bool = False
    embedding_model: str
    embedding_configured: bool = False
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


class DatabaseTableRead(BaseModel):
    name: str
    label: str
    category: str
    row_count: int
    available: bool
    note: str = ""


class DatabaseVectorStoreRead(BaseModel):
    provider: str
    collection: str
    enabled: bool
    status: str
    message: str
    points_count: int = 0
    dimensions: int | None = None
    distance: str = ""
    indexed_chunk_count: int = 0
    chunk_count: int = 0


class DatabaseManagementRead(BaseModel):
    status: str
    kind: str
    table_count: int
    available_table_count: int
    total_rows: int
    message: str
    safety_notes: list[str]
    vector_store: DatabaseVectorStoreRead
    tables: list[DatabaseTableRead]


class DatabaseVectorSearchRequest(BaseModel):
    query: str = Field(min_length=1, max_length=500)
    top_k: int = Field(default=5, ge=1, le=20)
    material_ids: list[int] = []


class DatabaseVectorSearchHitRead(BaseModel):
    id: int
    material_id: int
    material_title: str
    content: str
    score: float
    page_no: int | None
    slide_no: int | None


class DatabaseVectorSearchRead(BaseModel):
    query: str
    retrieval_mode: str
    cache_hit: bool
    hits: list[DatabaseVectorSearchHitRead]


class DemoSeedResultRead(BaseModel):
    message: str
    username: str
    password: str
    manager_username: str
    manager_password: str
    admin_user_id: int
    teaching_user_id: int
    course_id: int
    chapter_id: int
    session_id: int
    knowledge_point_id: int
    material_id: int
    exercise_id: int
    question_id: int


class SystemHealthRead(BaseModel):
    overall_status: str
    database: HealthComponentRead
    cache: HealthComponentRead
    vector_store: HealthComponentRead
    models: ModelHealthRead
    observability: ObservabilityHealthRead
    demo: DemoHealthRead
