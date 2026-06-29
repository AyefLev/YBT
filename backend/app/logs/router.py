from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Query
from sqlalchemy import desc, func, inspect, or_, select, text
from sqlalchemy.orm import Session

from app.auth.models import User
from app.ai.service import _provider_config_for_role
from app.core.config import get_settings
from app.core.database import get_db
from app.core.deps import require_permission
from app.demo.seed import seed_demo_data
from app.logs.models import JobLog, ModelLog, OperationLog
from app.logs.schemas import (
    DatabaseManagementRead,
    DatabaseTableRead,
    DatabaseVectorSearchHitRead,
    DatabaseVectorSearchRead,
    DatabaseVectorSearchRequest,
    DatabaseVectorStoreRead,
    DailyUsageRead,
    DemoHealthRead,
    DemoSeedResultRead,
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
from app.materials.models import MaterialChunk
from app.retrieval.service import search_chunks_cached
from app.retrieval.vector_store import check_vector_store_health, inspect_vector_store

router = APIRouter(prefix="/api/logs", tags=["logs"])


DATABASE_TABLES = [
    ("users", "用户", "账号权限", "账号、状态、申请审核信息"),
    ("roles", "角色", "账号权限", "角色与权限分组"),
    ("permissions", "权限", "账号权限", "系统权限代码"),
    ("courses", "课程", "教学组织", "教师或教管创建的课程"),
    ("chapters", "章节", "教学组织", "课程下的单元/章节"),
    ("lesson_sessions", "课次", "教学组织", "章节下的课时安排"),
    ("knowledge_points", "知识点", "教学组织", "与课程、章节、课次关联的知识点"),
    ("classrooms", "班级", "班级作业", "班级与邀请码"),
    ("classroom_enrollments", "班级成员", "班级作业", "学生加入班级记录"),
    ("assignments", "作业", "班级作业", "教师发布给班级的作业"),
    ("assignment_submissions", "作业提交", "班级作业", "学生提交与批改结果"),
    ("materials", "资料", "知识库", "公共或个人资料元数据"),
    ("material_chunks", "资料切片", "知识库", "资料解析后的检索切片"),
    ("course_material_links", "课程资料关联", "知识库", "课程与资料的关联"),
    ("lessons", "教案", "内容生产", "生成和保存的教案"),
    ("lesson_versions", "教案版本", "内容生产", "教案历史版本"),
    ("session_lesson_links", "课次教案关联", "内容生产", "课次与教案的关联"),
    ("exercises", "练习", "内容生产", "生成和保存的练习"),
    ("exercise_versions", "练习版本", "内容生产", "练习历史版本"),
    ("question_bank_items", "题库", "内容生产", "沉淀的问题答案对"),
    ("compliance_rules", "合规规则", "审核治理", "内容检查规则"),
    ("compliance_logs", "合规日志", "审核治理", "内容检查记录"),
    ("ai_provider_configs", "模型 API 配置", "系统配置", "各功能模型的接口配置"),
    ("operation_logs", "操作日志", "系统观测", "用户与系统操作记录"),
    ("model_logs", "模型日志", "系统观测", "模型调用、token 与费用"),
    ("job_logs", "任务日志", "系统观测", "异步/后台任务记录"),
    ("export_records", "导出记录", "系统观测", "文档与文件导出记录"),
]


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


def _database_tables(db: Session) -> list[DatabaseTableRead]:
    inspector = inspect(db.get_bind())
    existing_tables = set(inspector.get_table_names())
    tables: list[DatabaseTableRead] = []
    for name, label, category, note in DATABASE_TABLES:
        available = name in existing_tables
        row_count = 0
        if available:
            row_count = int(
                db.execute(text(f'SELECT COUNT(*) FROM "{name}"')).scalar_one()
            )
        tables.append(
            DatabaseTableRead(
                name=name,
                label=label,
                category=category,
                row_count=row_count,
                available=available,
                note=note,
            )
        )
    return tables


def _database_vector_store(db: Session) -> DatabaseVectorStoreRead:
    stats = inspect_vector_store()
    chunk_count = db.scalar(select(func.count(MaterialChunk.id))) or 0
    indexed_chunk_count = db.scalar(
        select(func.count(MaterialChunk.id)).where(MaterialChunk.future_vector_id.is_not(None))
    ) or 0
    return DatabaseVectorStoreRead(
        provider=stats.provider,
        collection=stats.collection,
        enabled=stats.enabled,
        status=stats.status,
        message=stats.message,
        points_count=stats.points_count,
        dimensions=stats.dimensions,
        distance=stats.distance,
        indexed_chunk_count=indexed_chunk_count,
        chunk_count=chunk_count,
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


def _like(value: str) -> str:
    return f"%{value.strip()}%"


def _daily_usage_rows(db: Session, *, days: int, group_by: str) -> list[DailyUsageRead]:
    start = datetime.now(timezone.utc) - timedelta(days=days - 1)
    rows = db.execute(
        select(ModelLog, User.username, User.display_name)
        .outerjoin(User, User.id == ModelLog.user_id)
        .where(ModelLog.created_at >= start)
        .order_by(ModelLog.created_at)
    ).all()
    grouped: dict[tuple[str, str, str, str], dict[str, object]] = {}
    for log, username, display_name in rows:
        day = log.created_at.date().isoformat()
        if group_by == "user":
            key = str(log.user_id or "system")
            label = display_name or username or (f"用户 {log.user_id}" if log.user_id else "系统任务")
        else:
            role = log.api_role or "default"
            key = f"{role}:{log.model}"
            label = f"{_role_label(role)} · {log.model or '未记录模型'}"
        currency = log.cost_currency or "CNY"
        bucket_key = (day, key, label, currency)
        bucket = grouped.setdefault(
            bucket_key,
            {
                "prompt_tokens": 0,
                "completion_tokens": 0,
                "estimated_cost": 0.0,
                "call_count": 0,
            },
        )
        bucket["prompt_tokens"] = int(bucket["prompt_tokens"]) + int(log.prompt_tokens or 0)
        bucket["completion_tokens"] = int(bucket["completion_tokens"]) + int(log.completion_tokens or 0)
        bucket["estimated_cost"] = float(bucket["estimated_cost"]) + float(log.estimated_cost or 0)
        bucket["call_count"] = int(bucket["call_count"]) + 1

    return [
        DailyUsageRead(
            day=day,
            group_key=key,
            group_label=label,
            prompt_tokens=int(values["prompt_tokens"]),
            completion_tokens=int(values["completion_tokens"]),
            total_tokens=int(values["prompt_tokens"]) + int(values["completion_tokens"]),
            estimated_cost=round(float(values["estimated_cost"]), 6),
            cost_currency=currency,
            call_count=int(values["call_count"]),
        )
        for (day, key, label, currency), values in sorted(grouped.items())
    ]


def _role_label(role: str) -> str:
    labels = {
        "generate": "生成",
        "review": "复核",
        "revise": "修订",
        "vision": "视觉",
        "embedding": "向量",
        "default": "默认",
    }
    return labels.get(role, role or "默认")


@router.get("/database", response_model=DatabaseManagementRead)
def get_database_management(
    current_user: User = Depends(require_permission("admin:content_manage")),
    db: Session = Depends(get_db),
) -> DatabaseManagementRead:
    _ = current_user
    health = _check_database(db)
    tables = _database_tables(db) if health.status == "healthy" else []
    total_rows = sum(table.row_count for table in tables if table.available)
    available_count = sum(1 for table in tables if table.available)
    return DatabaseManagementRead(
        status=health.status,
        kind=health.kind,
        table_count=len(tables),
        available_table_count=available_count,
        total_rows=total_rows,
        message=health.message,
        safety_notes=[
            "当前页面只提供只读统计和幂等基础样例同步。",
            "不会执行任意 SQL，也不会提供删除、清空、迁移等高风险入口。",
            "资料切片删除与向量库同步仍由资料管理流程负责。",
        ],
        vector_store=_database_vector_store(db),
        tables=tables,
    )


@router.post("/database/vector-search", response_model=DatabaseVectorSearchRead)
def search_database_vectors(
    payload: DatabaseVectorSearchRequest,
    current_user: User = Depends(require_permission("admin:content_manage")),
    db: Session = Depends(get_db),
) -> DatabaseVectorSearchRead:
    chunks, cache_hit, retrieval_mode = search_chunks_cached(
        db,
        query=payload.query,
        top_k=payload.top_k,
        material_ids=payload.material_ids,
        current_user=current_user,
    )
    return DatabaseVectorSearchRead(
        query=payload.query,
        retrieval_mode=retrieval_mode,
        cache_hit=cache_hit,
        hits=[
            DatabaseVectorSearchHitRead(
                id=chunk.id,
                material_id=chunk.material_id,
                material_title=chunk.material_title,
                content=chunk.content,
                score=chunk.score,
                page_no=chunk.page_no,
                slide_no=chunk.slide_no,
            )
            for chunk in chunks
        ],
    )


@router.post("/demo-seed", response_model=DemoSeedResultRead)
def seed_demo_database(
    current_user: User = Depends(require_permission("admin:content_manage")),
    db: Session = Depends(get_db),
) -> DemoSeedResultRead:
    _ = current_user
    result = seed_demo_data(db)
    db.commit()
    return DemoSeedResultRead(message="基础样例数据已同步，可重复执行。", **result)


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


@router.get("/usage-daily", response_model=list[DailyUsageRead])
def list_daily_usage(
    group_by: str = Query("model", pattern="^(model|user)$"),
    days: int = Query(30, ge=1, le=90),
    current_user: User = Depends(require_permission("log:view")),
    db: Session = Depends(get_db),
) -> list[DailyUsageRead]:
    _ = current_user
    return _daily_usage_rows(db, days=days, group_by=group_by)


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
    q: str | None = Query(None, max_length=200),
    action: str | None = Query(None, max_length=128),
    resource: str | None = Query(None, max_length=128),
    user_id: int | None = Query(None, ge=1),
    limit: int = Query(100, ge=1, le=300),
    current_user: User = Depends(require_permission("log:view")),
    db: Session = Depends(get_db),
) -> list[OperationLog]:
    _ = current_user
    statement = select(OperationLog)
    if q:
        pattern = _like(q)
        statement = statement.where(
            or_(
                OperationLog.action.ilike(pattern),
                OperationLog.resource.ilike(pattern),
                OperationLog.detail.ilike(pattern),
            )
        )
    if action:
        statement = statement.where(OperationLog.action.ilike(_like(action)))
    if resource:
        statement = statement.where(OperationLog.resource.ilike(_like(resource)))
    if user_id:
        statement = statement.where(OperationLog.user_id == user_id)
    return list(
        db.scalars(
            statement.order_by(desc(OperationLog.created_at), desc(OperationLog.id)).limit(limit)
        ).all()
    )


@router.get("/models", response_model=list[ModelLogRead])
def list_model_logs(
    q: str | None = Query(None, max_length=200),
    api_role: str | None = Query(None, max_length=32),
    model: str | None = Query(None, max_length=128),
    success: bool | None = Query(None),
    user_id: int | None = Query(None, ge=1),
    limit: int = Query(100, ge=1, le=300),
    current_user: User = Depends(require_permission("log:view")),
    db: Session = Depends(get_db),
) -> list[ModelLog]:
    _ = current_user
    statement = select(ModelLog)
    if q:
        pattern = _like(q)
        statement = statement.where(
            or_(
                ModelLog.task_type.ilike(pattern),
                ModelLog.provider.ilike(pattern),
                ModelLog.api_role.ilike(pattern),
                ModelLog.model.ilike(pattern),
                ModelLog.error_message.ilike(pattern),
                ModelLog.status.ilike(pattern),
            )
        )
    if api_role:
        statement = statement.where(ModelLog.api_role == api_role)
    if model:
        statement = statement.where(ModelLog.model.ilike(_like(model)))
    if success is not None:
        statement = statement.where(ModelLog.success.is_(success))
    if user_id:
        statement = statement.where(ModelLog.user_id == user_id)
    return list(
        db.scalars(
            statement.order_by(desc(ModelLog.created_at), desc(ModelLog.id)).limit(limit)
        ).all()
    )


@router.get("/jobs", response_model=list[JobLogRead])
def list_job_logs(
    q: str | None = Query(None, max_length=200),
    status: str | None = Query(None, max_length=32),
    job_type: str | None = Query(None, max_length=64),
    user_id: int | None = Query(None, ge=1),
    limit: int = Query(100, ge=1, le=300),
    current_user: User = Depends(require_permission("log:view")),
    db: Session = Depends(get_db),
) -> list[JobLog]:
    _ = current_user
    statement = select(JobLog)
    if q:
        pattern = _like(q)
        statement = statement.where(
            or_(
                JobLog.job_type.ilike(pattern),
                JobLog.status.ilike(pattern),
                JobLog.resource_type.ilike(pattern),
                JobLog.detail.ilike(pattern),
                JobLog.error_message.ilike(pattern),
            )
        )
    if status:
        statement = statement.where(JobLog.status == status)
    if job_type:
        statement = statement.where(JobLog.job_type.ilike(_like(job_type)))
    if user_id:
        statement = statement.where(JobLog.user_id == user_id)
    return list(
        db.scalars(
            statement.order_by(desc(JobLog.created_at), desc(JobLog.id)).limit(limit)
        ).all()
    )
