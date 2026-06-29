from datetime import datetime, timedelta, timezone


def _register_and_login(client, username: str) -> dict[str, str]:
    client.post(
        "/api/auth/register",
        json={
            "username": username,
            "email": f"{username}@example.com",
            "password": "secret-password",
            "display_name": username.title(),
        },
    )
    login_response = client.post(
        "/api/auth/login",
        json={"username": username, "password": "secret-password"},
    )
    token = login_response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def _admin_headers(client, username: str = "admin_user") -> dict[str, str]:
    from sqlalchemy import select

    from app.auth.models import Role, User
    from app.core.database import get_session_local

    headers = _register_and_login(client, username)
    session_local = get_session_local()
    with session_local() as db:
        user = db.scalar(select(User).where(User.username == username))
        admin_role = db.scalar(select(Role).where(Role.name == "admin"))
        user.roles = [admin_role]
        db.commit()
    return headers


def test_logs_endpoints_require_log_view_permission(client):
    headers = _register_and_login(client, "teacher_log_denied")

    operation_response = client.get("/api/logs/operations", headers=headers)
    model_response = client.get("/api/logs/models", headers=headers)

    assert operation_response.status_code == 403
    assert model_response.status_code == 403


def test_logs_endpoints_return_latest_100_newest_first(client):
    from app.core.database import get_session_local
    from app.logs.models import ModelLog, OperationLog

    headers = _admin_headers(client, "admin_log_reader")
    base_time = datetime(2026, 1, 1, tzinfo=timezone.utc)
    session_local = get_session_local()
    with session_local() as db:
        for index in range(101):
            created_at = base_time + timedelta(minutes=index)
            db.add(
                OperationLog(
                    action=f"operation-{index}",
                    resource="lesson",
                    detail=f"detail-{index}",
                    created_at=created_at,
                )
            )
            db.add(
                ModelLog(
                    task_type="lesson",
                    provider="mock",
                    model="mimo-v2.5-pro",
                    prompt_tokens=index,
                    completion_tokens=index + 1,
                    latency_ms=index + 2,
                    success=True,
                    fallback_used=False,
                    status="success",
                    created_at=created_at,
                )
            )
        db.commit()

    operation_response = client.get("/api/logs/operations", headers=headers)
    model_response = client.get("/api/logs/models", headers=headers)

    assert operation_response.status_code == 200
    operations = operation_response.json()
    assert len(operations) == 100
    assert operations[0]["action"] == "operation-100"
    assert operations[-1]["action"] == "operation-1"
    assert "operation-0" not in {operation["action"] for operation in operations}

    assert model_response.status_code == 200
    model_logs = model_response.json()
    assert len(model_logs) == 100
    assert model_logs[0]["prompt_tokens"] == 100
    assert model_logs[-1]["prompt_tokens"] == 1
    assert "created_at" in model_logs[0]


def test_admin_role_endpoints_manage_roles_and_validate_permission_codes(client):
    headers = _admin_headers(client, "admin_role_manager")

    roles_response = client.get("/api/admin/roles", headers=headers)
    assert roles_response.status_code == 200
    roles = roles_response.json()
    admin_role = next(role for role in roles if role["name"] == "admin")
    assert "admin:role_manage" in admin_role["permissions"]

    create_response = client.post(
        "/api/admin/roles",
        headers=headers,
        json={"name": "auditor", "permissions": ["log:view"]},
    )
    assert create_response.status_code == 201
    auditor = create_response.json()
    assert auditor["name"] == "auditor"
    assert auditor["permissions"] == ["log:view"]

    invalid_response = client.post(
        "/api/admin/roles",
        headers=headers,
        json={"name": "broken", "permissions": ["missing:code"]},
    )
    assert invalid_response.status_code == 400

    update_response = client.post(
        f"/api/admin/roles/{auditor['id']}/permissions",
        headers=headers,
        json={"permissions": ["lesson:create", "log:view"]},
    )
    assert update_response.status_code == 200
    assert update_response.json()["permissions"] == ["lesson:create", "log:view"]

    missing_response = client.post(
        "/api/admin/roles/99999/permissions",
        headers=headers,
        json={"permissions": ["log:view"]},
    )
    assert missing_response.status_code == 404


def test_admin_seeded_role_permission_updates_persist_across_role_listing(client):
    headers = _admin_headers(client, "admin_seeded_role_lister")

    roles_response = client.get("/api/admin/roles", headers=headers)
    assert roles_response.status_code == 200
    teaching_manager = next(
        role for role in roles_response.json() if role["name"] == "teaching_manager"
    )
    permissions_without_log_view = [
        permission
        for permission in teaching_manager["permissions"]
        if permission != "log:view"
    ]

    update_response = client.post(
        f"/api/admin/roles/{teaching_manager['id']}/permissions",
        headers=headers,
        json={"permissions": permissions_without_log_view},
    )
    assert update_response.status_code == 200
    assert "log:view" not in update_response.json()["permissions"]

    followup_response = client.get("/api/admin/roles", headers=headers)
    assert followup_response.status_code == 200
    updated_teaching_manager = next(
        role for role in followup_response.json() if role["name"] == "teaching_manager"
    )
    assert "log:view" not in updated_teaching_manager["permissions"]


def test_admin_seeded_role_permission_updates_apply_when_assigning_user_roles(client):
    headers = _admin_headers(client, "admin_seeded_role_assigner")
    _register_and_login(client, "managed_seeded_teacher")

    roles_response = client.get("/api/admin/roles", headers=headers)
    assert roles_response.status_code == 200
    teaching_manager = next(
        role for role in roles_response.json() if role["name"] == "teaching_manager"
    )
    permissions_without_log_view = [
        permission
        for permission in teaching_manager["permissions"]
        if permission != "log:view"
    ]

    update_response = client.post(
        f"/api/admin/roles/{teaching_manager['id']}/permissions",
        headers=headers,
        json={"permissions": permissions_without_log_view},
    )
    assert update_response.status_code == 200

    users_response = client.get("/api/admin/users", headers=headers)
    assert users_response.status_code == 200
    managed_user = next(
        user for user in users_response.json() if user["username"] == "managed_seeded_teacher"
    )

    update_user_response = client.post(
        f"/api/admin/users/{managed_user['id']}/roles",
        headers=headers,
        json={"roles": ["teaching_manager"]},
    )
    assert update_user_response.status_code == 200
    updated_user = update_user_response.json()
    assert updated_user["roles"] == ["teaching_manager"]
    assert "log:view" not in updated_user["permissions"]


def test_admin_user_endpoints_manage_user_roles(client):
    headers = _admin_headers(client, "admin_user_manager")
    _register_and_login(client, "managed_teacher")

    users_response = client.get("/api/admin/users", headers=headers)
    assert users_response.status_code == 200
    users = users_response.json()
    managed_user = next(user for user in users if user["username"] == "managed_teacher")
    assert managed_user["roles"] == ["teacher"]
    assert "lesson:create" in managed_user["permissions"]

    update_response = client.post(
        f"/api/admin/users/{managed_user['id']}/roles",
        headers=headers,
        json={"roles": ["teaching_manager"]},
    )
    assert update_response.status_code == 200
    updated_user = update_response.json()
    assert updated_user["roles"] == ["teaching_manager"]
    assert "log:view" not in updated_user["permissions"]

    invalid_role_response = client.post(
        f"/api/admin/users/{managed_user['id']}/roles",
        headers=headers,
        json={"roles": ["missing-role"]},
    )
    assert invalid_role_response.status_code == 400

    missing_user_response = client.post(
        "/api/admin/users/99999/roles",
        headers=headers,
        json={"roles": ["teacher"]},
    )
    assert missing_user_response.status_code == 404


def test_admin_endpoints_require_admin_permissions(client):
    headers = _register_and_login(client, "teacher_admin_denied")

    roles_response = client.get("/api/admin/roles", headers=headers)
    users_response = client.get("/api/admin/users", headers=headers)

    assert roles_response.status_code == 403
    assert users_response.status_code == 403


def test_phase2_job_logs_endpoint_requires_log_view_and_returns_newest_first(client):
    from app.core.database import get_session_local
    from app.logs.models import JobLog

    denied_headers = _register_and_login(client, "teacher_job_log_denied")
    assert client.get("/api/logs/jobs", headers=denied_headers).status_code == 403

    admin_headers = _admin_headers(client, "admin_job_log_reader")
    session_local = get_session_local()
    with session_local() as db:
        db.add(
            JobLog(
                job_type="material_parse",
                status="succeeded",
                resource_type="material",
                resource_id=1,
                user_id=None,
                detail="older",
                duration_ms=10,
            )
        )
        db.add(
            JobLog(
                job_type="material_parse",
                status="failed",
                resource_type="material",
                resource_id=2,
                user_id=None,
                detail="newer",
                error_message="parse failed",
                duration_ms=20,
            )
        )
        db.commit()

    response = client.get("/api/logs/jobs", headers=admin_headers)

    assert response.status_code == 200
    logs = response.json()
    assert [log["resource_id"] for log in logs[:2]] == [2, 1]
    assert logs[0]["job_type"] == "material_parse"
    assert logs[0]["status"] == "failed"
    assert logs[0]["error_message"] == "parse failed"
    assert logs[0]["duration_ms"] == 20


def test_logs_summary_reports_model_and_job_observability_metrics(client):
    from app.core.database import get_session_local
    from app.logs.models import JobLog, ModelLog, OperationLog

    headers = _admin_headers(client, "admin_log_summary_reader")
    session_local = get_session_local()
    with session_local() as db:
        db.add_all(
            [
                ModelLog(
                    task_type="exercise",
                    provider="real",
                    model="mimo-v2.5-pro",
                    latency_ms=1000,
                    success=True,
                    fallback_used=False,
                    status="success",
                ),
                ModelLog(
                    task_type="exercise_review",
                    provider="mock",
                    model="mock-generator",
                    latency_ms=2000,
                    success=True,
                    fallback_used=True,
                    status="success",
                ),
                ModelLog(
                    task_type="exercise_revise",
                    provider="real",
                    model="deepseek-v4-pro",
                    latency_ms=3000,
                    success=False,
                    fallback_used=False,
                    status="error",
                    error_message="timeout",
                ),
                JobLog(job_type="material_parse", status="failed", error_message="parse failed"),
                OperationLog(action="exercise:create", resource="exercise"),
            ]
        )
        db.commit()

    response = client.get("/api/logs/summary", headers=headers)

    assert response.status_code == 200
    body = response.json()
    assert body["model_total"] == 3
    assert body["model_success"] == 2
    assert body["model_failed"] == 1
    assert body["mock_fallbacks"] == 1
    assert body["average_latency_ms"] == 2000
    assert body["job_failed"] == 1
    assert body["operation_total"] == 1
    assert body["recent_errors"][0]["message"] == "timeout"


def test_logs_filters_and_daily_usage_reports_grouped_usage(client):
    from app.core.database import get_session_local
    from app.logs.models import JobLog, ModelLog, OperationLog

    headers = _admin_headers(client, "admin_log_filter_reader")
    session_local = get_session_local()
    created_at = datetime.now(timezone.utc)
    with session_local() as db:
        db.add_all(
            [
                ModelLog(
                    user_id=1,
                    task_type="exercise",
                    provider="real",
                    api_role="generate",
                    api_base_url="https://api.example/v1",
                    model="deepseek-v4-pro",
                    prompt_tokens=100,
                    completion_tokens=50,
                    estimated_cost=0.03,
                    cost_currency="CNY",
                    latency_ms=800,
                    success=True,
                    fallback_used=False,
                    status="success",
                    created_at=created_at,
                ),
                ModelLog(
                    user_id=1,
                    task_type="exercise_review",
                    provider="real",
                    api_role="review",
                    api_base_url="https://api.example/v1",
                    model="audit-model",
                    prompt_tokens=80,
                    completion_tokens=20,
                    estimated_cost=0.02,
                    cost_currency="CNY",
                    latency_ms=900,
                    success=False,
                    fallback_used=False,
                    status="error",
                    error_message="rate limit",
                    created_at=created_at,
                ),
                JobLog(
                    job_type="material_parse",
                    status="failed",
                    resource_type="material",
                    resource_id=10,
                    user_id=1,
                    error_message="parse failed",
                    created_at=created_at,
                ),
                OperationLog(
                    user_id=1,
                    action="lesson:update",
                    resource="lesson",
                    detail="updated lesson title",
                    created_at=created_at,
                ),
            ]
        )
        db.commit()

    failed_models = client.get("/api/logs/models?success=false&q=rate", headers=headers)
    failed_jobs = client.get("/api/logs/jobs?status=failed&q=parse", headers=headers)
    operations = client.get("/api/logs/operations?q=lesson", headers=headers)
    daily = client.get("/api/logs/usage-daily?group_by=model&days=7", headers=headers)

    assert failed_models.status_code == 200
    assert [log["model"] for log in failed_models.json()] == ["audit-model"]
    assert failed_jobs.status_code == 200
    assert failed_jobs.json()[0]["job_type"] == "material_parse"
    assert operations.status_code == 200
    assert operations.json()[0]["action"] == "lesson:update"
    assert daily.status_code == 200
    rows = daily.json()
    assert any(row["group_key"] == "generate:deepseek-v4-pro" for row in rows)
    assert any(row["total_tokens"] == 150 for row in rows)


def test_logs_health_reports_demo_readiness_without_exposing_secrets(client):
    from app.core.database import get_session_local
    from app.ai.models import AIProviderConfig
    from app.logs.models import JobLog, ModelLog

    headers = _admin_headers(client, "admin_health_reader")
    session_local = get_session_local()
    with session_local() as db:
        db.add(
            AIProviderConfig(
                role="generate",
                base_url="https://db-model.example/v1",
                api_key="db-generate-key",
                model="db-generate-model",
                enabled=True,
            )
        )
        db.add_all(
            [
                ModelLog(
                    task_type="exercise",
                    provider="real",
                    model="mimo-v2.5-pro",
                    latency_ms=100,
                    success=True,
                    fallback_used=False,
                    status="success",
                ),
                JobLog(job_type="material_parse", status="succeeded", duration_ms=30),
            ]
        )
        db.commit()

    response = client.get("/api/logs/health", headers=headers)

    assert response.status_code == 200
    body = response.json()
    assert body["overall_status"] == "healthy"
    assert body["database"]["status"] == "healthy"
    assert body["database"]["kind"] == "sqlite"
    assert body["cache"]["status"] == "healthy"
    assert body["cache"]["kind"] == "memory"
    assert body["vector_store"]["status"] == "healthy"
    assert body["vector_store"]["kind"] == "disabled"
    assert body["models"]["text_model"] == "db-generate-model"
    assert body["models"]["generate_model"] == "db-generate-model"
    assert body["models"]["generate_configured"] is True
    assert body["models"]["api_key_configured"] is True
    assert "api_key" not in body["models"]
    assert body["observability"]["model_total"] == 1
    assert body["observability"]["job_total"] == 1
    assert body["demo"]["docker_ready_items"] == [
        "gateway",
        "frontend",
        "backend-api",
        "worker",
        "database",
        "cache",
        "vector-db",
        "observability",
    ]


def test_database_management_requires_content_admin_permission(client):
    headers = _register_and_login(client, "teacher_database_denied")

    read_response = client.get("/api/logs/database", headers=headers)
    seed_response = client.post("/api/logs/demo-seed", headers=headers)

    assert read_response.status_code == 403
    assert seed_response.status_code == 403


def test_database_management_reports_whitelisted_table_counts(client):
    headers = _admin_headers(client, "admin_database_reader")

    response = client.get("/api/logs/database", headers=headers)

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "healthy"
    assert body["kind"] == "sqlite"
    assert body["available_table_count"] == body["table_count"]
    assert body["total_rows"] >= 1
    assert any("不会执行任意 SQL" in note for note in body["safety_notes"])
    assert body["vector_store"]["provider"] == "disabled"
    assert body["vector_store"]["status"] == "disabled"
    assert body["vector_store"]["chunk_count"] == 0

    tables = {table["name"]: table for table in body["tables"]}
    assert tables["users"]["label"] == "用户"
    assert tables["users"]["row_count"] >= 1
    assert tables["materials"]["category"] == "知识库"
    assert tables["model_logs"]["category"] == "系统观测"


def test_demo_seed_endpoint_initializes_idempotent_demo_data(client):
    headers = _admin_headers(client, "admin_demo_seeder")

    first_response = client.post("/api/logs/demo-seed", headers=headers)
    second_response = client.post("/api/logs/demo-seed", headers=headers)

    assert first_response.status_code == 200
    assert second_response.status_code == 200
    first = first_response.json()
    second = second_response.json()
    assert first["username"] == "demo_admin"
    assert first["password"] == "Demo123456"
    assert first["manager_username"] == "demo_manager"
    assert first["course_id"] == second["course_id"]
    assert first["question_id"] == second["question_id"]

    database_response = client.get("/api/logs/database", headers=headers)
    tables = {table["name"]: table for table in database_response.json()["tables"]}
    assert tables["courses"]["row_count"] >= 1
    assert tables["material_chunks"]["row_count"] >= 1
    assert tables["question_bank_items"]["row_count"] >= 1

    search_response = client.post(
        "/api/logs/database/vector-search",
        headers=headers,
        json={"query": "矩阵乘法", "top_k": 3},
    )
    assert search_response.status_code == 200
    search_body = search_response.json()
    assert search_body["retrieval_mode"] == "lexical"
    assert search_body["hits"][0]["material_title"] == "矩阵乘法讲义片段"
