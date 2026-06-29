from fastapi import APIRouter, Depends
from sqlalchemy import desc, func, select, text
from sqlalchemy.orm import Session

from app.auth.models import User
from app.ai.service import _provider_config_for_role
from app.core.config import get_settings
from app.core.database import get_db
from app.core.deps import require_permission
from app.logs.models import JobLog, ModelLog, OperationLog
from app.logs.schemas import (
    DemoHealthRead,
    HealthComponentRead,
    JobLogRead,
    LogSummaryRead,
    ModelUsageRead,
    ModelHealthRead,
    ModelLogRead,
    ObservabilityHealthRead,
    OperationLogRead,
    RecentErrorRead,
    SystemHealthRead,
    TokenUsageRead,
)
from app.retrieval.vector_store import check_vector_store_health

router = APIRouter(prefix="/api/logs", tags=["logs"])


def _database_kind(database_url: str) -> str:
    if database_url.startswith("sqlite"):
        return "sqlite"
    if database_url.startswith("postgres"):
        return "postgresql"
    return database_url.split(":", maxsplit=1)[0] or "unknown"


def _check_database(db: Session) -> HealthComponentRead:
    try:
        db.execute(text("SELECT 1")).scalar_one()
    except Exception as exc:
        return HealthComponentRead(
            status="unhealthy",
            kind=_database_kind(get_settings().database_url),
            message=str(exc),
        )
    return HealthComponentRead(
        status="healthy",
        kind=_database_kind(get_settings().database_url),
        message="数据库连接正常",
    )


def _check_cache() -> HealthComponentRead:
    settings = get_settings()
    if not settings.redis_url:
        return HealthComponentRead(
            status="healthy",
            kind="memory",
            message="当前使用内存缓存；Docker 演示环境可配置 Redis。",
        )

    try:
        from redis import Redis

        client = Redis.from_url(
            settings.redis_url,
            decode_responses=True,
            socket_connect_timeout=1,
            socket_timeout=1,
        )
        client.ping()
    except Exception as exc:
        return HealthComponentRead(
            status="degraded",
            kind="redis",
            message=f"Redis 未连通：{exc}",
        )
    return HealthComponentRead(
        status="healthy",
        kind="redis",
        message="Redis 连接正常",
    )


def _check_vector_store() -> HealthComponentRead:
    try:
        result = check_vector_store_health()
    except Exception as exc:
        return HealthComponentRead(
            status="degraded",
            kind="qdrant",
            message=f"向量数据库未连通：{exc}",
        )
    if not result.enabled:
        return HealthComponentRead(
            status="healthy",
            kind=result.provider,
            message=result.message,
        )
    return HealthComponentRead(
        status="healthy",
        kind=f"{result.provider}:{result.collection}",
        message=result.message,
    )


def _overall_status(
    database: HealthComponentRead,
    cache: HealthComponentRead,
    vector_store: HealthComponentRead,
) -> str:
    if database.status == "unhealthy":
        return "unhealthy"
    if cache.status != "healthy" or vector_store.status != "healthy":
        return "degraded"
    return "healthy"


def _observability_health(db: Session) -> ObservabilityHealthRead:
    return ObservabilityHealthRead(
        model_total=db.scalar(select(func.count(ModelLog.id))) or 0,
        model_failed=db.scalar(select(func.count(ModelLog.id)).where(ModelLog.success.is_(False))) or 0,
        job_total=db.scalar(select(func.count(JobLog.id))) or 0,
        job_failed=db.scalar(select(func.count(JobLog.id)).where(JobLog.status == "failed")) or 0,
        operation_total=db.scalar(select(func.count(OperationLog.id))) or 0,
    )


def _model_health(db: Session) -> ModelHealthRead:
    settings = get_settings()
    generate_config = _provider_config_for_role(settings, "generate", db=db)
    review_config = _provider_config_for_role(settings, "review", db=db)
    revise_config = _provider_config_for_role(settings, "revise", db=db)
    vision_config = _provider_config_for_role(settings, "vision", db=db)
    embedding_config = _provider_config_for_role(settings, "embedding", db=db)
    text_configured = bool(
        generate_config.api_key
        or review_config.api_key
        or revise_config.api_key
    )
    return ModelHealthRead(
        text_model=generate_config.model,
        generate_model=generate_config.model,
        generate_configured=bool(generate_config.api_key and generate_config.model),
        review_model=review_config.model,
        review_configured=bool(review_config.api_key and review_config.model),
        revise_model=revise_config.model,
        revise_configured=bool(revise_config.api_key and revise_config.model),
        vision_model=vision_config.model or None,
        vision_configured=bool(vision_config.api_key and vision_config.model),
        embedding_model=embedding_config.model,
        embedding_configured=bool(embedding_config.model),
        api_key_configured=text_configured,
        vision_api_key_configured=bool(vision_config.api_key and vision_config.model),
        multi_agent_review=settings.llm_multi_agent_review,
        mock_on_failure=settings.llm_mock_on_failure,
    )


def _currency_label(db: Session, statement) -> str:
    currencies = [
        item
        for item in db.scalars(statement).all()
        if item
    ]
    if not currencies:
        return "CNY"
    return currencies[0] if len(set(currencies)) == 1 else "mixed"


@router.get("/summary", response_model=LogSummaryRead)
def get_log_summary(
    current_user: User = Depends(require_permission("log:view")),
    db: Session = Depends(get_db),
) -> LogSummaryRead:
    _ = current_user
    model_total = db.scalar(select(func.count(ModelLog.id))) or 0
    model_success = db.scalar(select(func.count(ModelLog.id)).where(ModelLog.success.is_(True))) or 0
    model_failed = db.scalar(select(func.count(ModelLog.id)).where(ModelLog.success.is_(False))) or 0
    mock_fallbacks = db.scalar(select(func.count(ModelLog.id)).where(ModelLog.fallback_used.is_(True))) or 0
    prompt_tokens = db.scalar(select(func.coalesce(func.sum(ModelLog.prompt_tokens), 0))) or 0
    completion_tokens = db.scalar(select(func.coalesce(func.sum(ModelLog.completion_tokens), 0))) or 0
    estimated_cost = db.scalar(select(func.coalesce(func.sum(ModelLog.estimated_cost), 0))) or 0
    cost_currency = _currency_label(db, select(ModelLog.cost_currency).distinct())
    average_latency = db.scalar(select(func.avg(ModelLog.latency_ms)).where(ModelLog.latency_ms.is_not(None))) or 0
    job_total = db.scalar(select(func.count(JobLog.id))) or 0
    job_failed = db.scalar(select(func.count(JobLog.id)).where(JobLog.status == "failed")) or 0
    operation_total = db.scalar(select(func.count(OperationLog.id))) or 0

    failed_model_logs = db.scalars(
        select(ModelLog)
        .where(ModelLog.success.is_(False))
        .order_by(desc(ModelLog.created_at), desc(ModelLog.id))
        .limit(5)
    ).all()
    failed_job_logs = db.scalars(
        select(JobLog)
        .where(JobLog.status == "failed")
        .order_by(desc(JobLog.created_at), desc(JobLog.id))
        .limit(5)
    ).all()
    recent_errors = [
        RecentErrorRead(
            source="model",
            task_type=log.task_type,
            message=log.error_message or log.error or "Model call failed",
            created_at=log.created_at,
        )
        for log in failed_model_logs
    ] + [
        RecentErrorRead(
            source="job",
            task_type=log.job_type,
            message=log.error_message or "Job failed",
            created_at=log.created_at,
        )
        for log in failed_job_logs
    ]
    recent_errors.sort(key=lambda item: item.created_at, reverse=True)

    return LogSummaryRead(
        model_total=model_total,
        model_success=model_success,
        model_failed=model_failed,
        mock_fallbacks=mock_fallbacks,
        prompt_tokens=int(prompt_tokens),
        completion_tokens=int(completion_tokens),
        total_tokens=int(prompt_tokens) + int(completion_tokens),
        estimated_cost=round(float(estimated_cost or 0), 6),
        cost_currency=cost_currency,
        average_latency_ms=int(average_latency),
        job_total=job_total,
        job_failed=job_failed,
        operation_total=operation_total,
        recent_errors=recent_errors[:5],
    )


@router.get("/token-usage", response_model=list[TokenUsageRead])
def list_token_usage(
    current_user: User = Depends(require_permission("log:view")),
    db: Session = Depends(get_db),
) -> list[TokenUsageRead]:
    _ = current_user
    prompt_sum = func.coalesce(func.sum(ModelLog.prompt_tokens), 0)
    completion_sum = func.coalesce(func.sum(ModelLog.completion_tokens), 0)
    cost_sum = func.coalesce(func.sum(ModelLog.estimated_cost), 0)
    currency_count = func.count(func.distinct(ModelLog.cost_currency))
    currency_value = func.min(ModelLog.cost_currency)
    rows = db.execute(
        select(
            ModelLog.user_id,
            User.username,
            User.display_name,
            prompt_sum.label("prompt_tokens"),
            completion_sum.label("completion_tokens"),
            cost_sum.label("estimated_cost"),
            currency_count.label("currency_count"),
            currency_value.label("cost_currency"),
            func.count(ModelLog.id).label("call_count"),
        )
        .outerjoin(User, User.id == ModelLog.user_id)
        .group_by(ModelLog.user_id, User.username, User.display_name)
        .order_by(desc(cost_sum), desc(prompt_sum + completion_sum), desc(func.count(ModelLog.id)))
        .limit(50)
    ).all()
    return [
        TokenUsageRead(
            user_id=row.user_id,
            username=row.username or "",
            display_name=row.display_name or "",
            prompt_tokens=int(row.prompt_tokens or 0),
            completion_tokens=int(row.completion_tokens or 0),
            total_tokens=int(row.prompt_tokens or 0) + int(row.completion_tokens or 0),
            estimated_cost=round(float(row.estimated_cost or 0), 6),
            cost_currency=row.cost_currency if int(row.currency_count or 0) <= 1 else "mixed",
            call_count=int(row.call_count or 0),
        )
        for row in rows
    ]


@router.get("/model-usage", response_model=list[ModelUsageRead])
def list_model_usage(
    current_user: User = Depends(require_permission("log:view")),
    db: Session = Depends(get_db),
) -> list[ModelUsageRead]:
    _ = current_user
    prompt_sum = func.coalesce(func.sum(ModelLog.prompt_tokens), 0)
    completion_sum = func.coalesce(func.sum(ModelLog.completion_tokens), 0)
    cost_sum = func.coalesce(func.sum(ModelLog.estimated_cost), 0)
    rows = db.execute(
        select(
            ModelLog.api_role,
            ModelLog.api_base_url,
            ModelLog.model,
            ModelLog.cost_currency,
            prompt_sum.label("prompt_tokens"),
            completion_sum.label("completion_tokens"),
            cost_sum.label("estimated_cost"),
            func.count(ModelLog.id).label("call_count"),
        )
        .group_by(ModelLog.api_role, ModelLog.api_base_url, ModelLog.model, ModelLog.cost_currency)
        .order_by(desc(cost_sum), desc(prompt_sum + completion_sum), desc(func.count(ModelLog.id)))
        .limit(50)
    ).all()
    return [
        ModelUsageRead(
            api_role=row.api_role or "",
            api_base_url=row.api_base_url or "",
            model=row.model or "",
            prompt_tokens=int(row.prompt_tokens or 0),
            completion_tokens=int(row.completion_tokens or 0),
            total_tokens=int(row.prompt_tokens or 0) + int(row.completion_tokens or 0),
            estimated_cost=round(float(row.estimated_cost or 0), 6),
            cost_currency=row.cost_currency or "CNY",
            call_count=int(row.call_count or 0),
        )
        for row in rows
    ]


@router.get("/health", response_model=SystemHealthRead)
def get_system_health(
    current_user: User = Depends(require_permission("log:view")),
    db: Session = Depends(get_db),
) -> SystemHealthRead:
    _ = current_user
    database = _check_database(db)
    cache = _check_cache()
    vector_store = _check_vector_store()
    return SystemHealthRead(
        overall_status=_overall_status(database, cache, vector_store),
        database=database,
        cache=cache,
        vector_store=vector_store,
        models=_model_health(db),
        observability=_observability_health(db),
        demo=DemoHealthRead(
            docker_ready_items=[
                "gateway",
                "frontend",
                "backend-api",
                "worker",
                "database",
                "cache",
                "vector-db",
                "observability",
            ],
            suggested_next_action="演示前先执行 docker compose exec backend python scripts/seed_demo_data.py 初始化样例数据。",
        ),
    )


@router.get("/operations", response_model=list[OperationLogRead])
def list_operation_logs(
    current_user: User = Depends(require_permission("log:view")),
    db: Session = Depends(get_db),
) -> list[OperationLog]:
    _ = current_user
    return list(
        db.scalars(
            select(OperationLog)
            .order_by(desc(OperationLog.created_at), desc(OperationLog.id))
            .limit(100)
        ).all()
    )


@router.get("/models", response_model=list[ModelLogRead])
def list_model_logs(
    current_user: User = Depends(require_permission("log:view")),
    db: Session = Depends(get_db),
) -> list[ModelLog]:
    _ = current_user
    return list(
        db.scalars(
            select(ModelLog)
            .order_by(desc(ModelLog.created_at), desc(ModelLog.id))
            .limit(100)
        ).all()
    )


@router.get("/jobs", response_model=list[JobLogRead])
def list_job_logs(
    current_user: User = Depends(require_permission("log:view")),
    db: Session = Depends(get_db),
) -> list[JobLog]:
    _ = current_user
    return list(
        db.scalars(
            select(JobLog)
            .order_by(desc(JobLog.created_at), desc(JobLog.id))
            .limit(100)
        ).all()
    )
