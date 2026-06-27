from fastapi import APIRouter, Depends
from sqlalchemy import desc, func, select, text
from sqlalchemy.orm import Session

from app.auth.models import User
from app.core.config import get_settings
from app.core.database import get_db
from app.core.deps import require_permission
from app.logs.models import JobLog, ModelLog, OperationLog
from app.logs.schemas import (
    DemoHealthRead,
    HealthComponentRead,
    JobLogRead,
    LogSummaryRead,
    ModelHealthRead,
    ModelLogRead,
    ObservabilityHealthRead,
    OperationLogRead,
    RecentErrorRead,
    SystemHealthRead,
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


def _model_health() -> ModelHealthRead:
    settings = get_settings()
    return ModelHealthRead(
        text_model=settings.llm_model,
        generate_model=settings.llm_generate_model,
        review_model=settings.llm_review_model,
        revise_model=settings.llm_revise_model,
        vision_model=settings.vision_llm_model or None,
        api_key_configured=bool(settings.llm_api_key),
        vision_api_key_configured=bool(settings.vision_llm_api_key),
        multi_agent_review=settings.llm_multi_agent_review,
        mock_on_failure=settings.llm_mock_on_failure,
    )


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
        average_latency_ms=int(average_latency),
        job_total=job_total,
        job_failed=job_failed,
        operation_total=operation_total,
        recent_errors=recent_errors[:5],
    )


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
        models=_model_health(),
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
