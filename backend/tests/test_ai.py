import pytest


def _auth_headers(client, username: str = "ai_teacher") -> dict[str, str]:
    client.post(
        "/api/auth/register",
        json={
            "username": username,
            "email": f"{username}@example.com",
            "password": "secret-password",
            "display_name": "AI Teacher",
        },
    )
    login_response = client.post(
        "/api/auth/login",
        json={"username": username, "password": "secret-password"},
    )
    token = login_response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_exercise_prompt_constrains_comprehensive_question_format():
    from app.ai.prompts import build_exercise_prompt

    prompt = build_exercise_prompt(
        {
            "title": "课堂练习",
            "subject": "英语",
            "knowledge_point": "小作文书信格式",
            "question_type": "综合题",
            "difficulty": "中等",
            "count": 3,
        }
    )

    assert "综合题必须包含材料、情境、表格、公式或示意图之一" in prompt
    assert "不要把综合题拆成单选题" in prompt
    assert "[公式]" in prompt
    assert "[SVG]" in prompt


def test_exercise_prompt_requires_subject_and_knowledge_alignment():
    from app.ai.prompts import build_exercise_prompt

    prompt = build_exercise_prompt(
        {
            "title": "课堂练习",
            "subject": "数学",
            "knowledge_point": "矩阵乘法",
            "question_type": "综合题",
            "difficulty": "中等",
            "count": 3,
        }
    )

    assert "每道题必须紧扣表单中的学科和知识点" in prompt
    assert "数学题目必须体现数学概念、计算、推导或建模" in prompt
    assert "矩阵乘法" in prompt
    assert "不得生成与学科或知识点无关的题目" in prompt
    assert "不要禁止必要的公式、表格、示意图或题图" in prompt


def test_generated_math_text_normalization_removes_inline_latex_commands():
    from app.ai.formatting import normalize_generated_math_text

    raw = (
        r"设 \(A\) 为 \(m \times n\) 矩阵，证明 "
        r"\((AB)^{\mathrm{T}} = B^{\mathrm{T}}A^{\mathrm{T}}\)。"
        r"定义 \(\operatorname{tr}(X)=\sum_{i=1}^{p}x_{ii}\)。"
    )

    normalized = normalize_generated_math_text(raw)

    assert r"\(" not in normalized
    assert r"\times" not in normalized
    assert r"\mathrm" not in normalized
    assert r"\operatorname" not in normalized
    assert r"\sum" not in normalized
    assert "A 为 m × n 矩阵" in normalized
    assert "(AB)^T = B^TA^T" in normalized
    assert "tr(X)=Σ_i=1^px_ii" in normalized


def test_ai_capabilities_report_configured_models(client, monkeypatch):
    from app.core.config import get_settings

    monkeypatch.setenv("LLM_API_KEY", "test-key")
    monkeypatch.setenv("LLM_MODEL", "text-model")
    monkeypatch.setenv("VISION_LLM_API_KEY", "vision-key")
    monkeypatch.setenv("VISION_LLM_MODEL", "vision-model")
    monkeypatch.setenv("EMBEDDING_MODEL", "embedding-model")
    monkeypatch.setenv("LLM_MOCK_ON_FAILURE", "false")
    get_settings.cache_clear()

    response = client.get("/api/ai/capabilities")

    assert response.status_code == 200
    body = response.json()
    assert body["text_model"] == "text-model"
    assert body["text_configured"] is True
    assert body["vision_model"] == "vision-model"
    assert body["vision_configured"] is True
    assert body["embedding_configured"] is True
    assert body["mock_on_failure"] is False


def test_ai_capabilities_report_role_models_and_configured_flags(client, monkeypatch):
    from app.cache.client import clear_cache_backend
    from app.core.config import get_settings

    monkeypatch.setenv("LLM_API_KEY", "generate-key")
    monkeypatch.setenv("LLM_GENERATE_MODEL", "generate-model")
    monkeypatch.setenv("REVIEW_LLM_API_KEY", "review-key")
    monkeypatch.setenv("LLM_REVIEW_MODEL", "review-model")
    monkeypatch.setenv("REVISE_LLM_API_KEY", "revise-key")
    monkeypatch.setenv("LLM_REVISE_MODEL", "revise-model")
    get_settings.cache_clear()
    clear_cache_backend()

    response = client.get("/api/ai/capabilities")

    assert response.status_code == 200
    body = response.json()
    assert body["generate_model"] == "generate-model"
    assert body["generate_configured"] is True
    assert body["review_model"] == "review-model"
    assert body["review_configured"] is True
    assert body["revise_model"] == "revise-model"
    assert body["revise_configured"] is True


def test_ai_connectivity_reports_configured_roles_without_live_probe(client, monkeypatch):
    from app.cache.client import clear_cache_backend
    from app.core.config import get_settings

    monkeypatch.setenv("LLM_API_KEY", "generate-key")
    monkeypatch.setenv("LLM_GENERATE_MODEL", "generate-model")
    monkeypatch.setenv("REVIEW_LLM_API_KEY", "")
    monkeypatch.setenv("LLM_REVIEW_MODEL", "review-model")
    monkeypatch.setenv("REVISE_LLM_API_KEY", "revise-key")
    monkeypatch.setenv("LLM_REVISE_MODEL", "revise-model")
    get_settings.cache_clear()
    clear_cache_backend()

    response = client.get("/api/ai/connectivity")

    assert response.status_code == 200
    body = response.json()
    assert body["probe_enabled"] is False
    checks = {item["role"]: item for item in body["checks"]}
    assert checks["generate"]["configured"] is True
    assert checks["generate"]["status"] == "not_tested"
    assert checks["review"]["configured"] is True
    assert checks["review"]["status"] == "not_tested"
    assert checks["revise"]["configured"] is True
    assert checks["revise"]["status"] == "not_tested"
    assert checks["vision"]["configured"] is False
    assert checks["vision"]["status"] == "not_configured"
    assert "api_key" not in checks["generate"]


def test_ai_connectivity_live_probe_records_success_and_failure(client, monkeypatch):
    import httpx

    from app.cache.client import clear_cache_backend
    from app.core.config import get_settings

    calls: list[dict[str, object]] = []

    def fake_post(url, *, headers, json, timeout):
        calls.append(
            {
                "url": url,
                "authorization": headers["Authorization"],
                "model": json["model"],
            }
        )
        if "review.example" in url:
            return httpx.Response(
                500,
                request=httpx.Request("POST", url),
                json={"error": {"message": "review unavailable"}},
            )
        return httpx.Response(
            200,
            request=httpx.Request("POST", url),
            json={"choices": [{"message": {"content": "ok"}}]},
        )

    monkeypatch.setenv("LLM_API_KEY", "")
    monkeypatch.setenv("GENERATE_LLM_API_KEY", "generate-key")
    monkeypatch.setenv("LLM_BASE_URL", "https://generate.example/v1")
    monkeypatch.setenv("LLM_GENERATE_MODEL", "generate-model")
    monkeypatch.setenv("REVIEW_LLM_API_KEY", "review-key")
    monkeypatch.setenv("REVIEW_LLM_BASE_URL", "https://review.example/v1")
    monkeypatch.setenv("LLM_REVIEW_MODEL", "review-model")
    monkeypatch.setenv("REVISE_LLM_API_KEY", "")
    monkeypatch.setattr(httpx, "post", fake_post)
    get_settings.cache_clear()
    clear_cache_backend()

    response = client.get("/api/ai/connectivity?probe=true")

    assert response.status_code == 200
    body = response.json()
    checks = {item["role"]: item for item in body["checks"]}
    assert checks["generate"]["status"] == "success"
    assert checks["generate"]["latency_ms"] >= 0
    assert checks["review"]["status"] == "failed"
    assert "Server error" in checks["review"]["message"]
    assert checks["revise"]["status"] == "not_configured"
    assert calls[0]["url"] == "https://generate.example/v1/chat/completions"
    assert calls[0]["authorization"] == "Bearer generate-key"
    assert calls[0]["model"] == "generate-model"


def test_ai_connectivity_live_probe_uses_vision_provider(client, monkeypatch):
    import httpx

    from app.cache.client import clear_cache_backend
    from app.core.config import get_settings

    calls: list[dict[str, object]] = []

    def fake_post(url, *, headers, json, timeout):
        calls.append(
            {
                "url": url,
                "authorization": headers["Authorization"],
                "model": json["model"],
                "content": json["messages"][0]["content"],
            }
        )
        return httpx.Response(
            200,
            request=httpx.Request("POST", url),
            json={"choices": [{"message": {"content": "ok"}}]},
        )

    monkeypatch.setenv("LLM_API_KEY", "")
    monkeypatch.setenv("VISION_LLM_API_KEY", "vision-key")
    monkeypatch.setenv("VISION_LLM_BASE_URL", "https://vision.example/v1")
    monkeypatch.setenv("VISION_LLM_MODEL", "vision-model")
    monkeypatch.setattr(httpx, "post", fake_post)
    get_settings.cache_clear()
    clear_cache_backend()

    response = client.get("/api/ai/connectivity?probe=true")

    assert response.status_code == 200
    body = response.json()
    checks = {item["role"]: item for item in body["checks"]}
    assert checks["vision"]["status"] == "success"
    assert calls[0]["url"] == "https://vision.example/v1/chat/completions"
    assert calls[0]["authorization"] == "Bearer vision-key"
    assert calls[0]["model"] == "vision-model"
    assert calls[0]["content"][0]["type"] == "text"
    assert calls[0]["content"][1]["type"] == "image_url"
    assert calls[0]["content"][1]["image_url"]["url"].startswith("data:image/png;base64,")


def test_vision_analysis_endpoint_uses_configured_vision_model(client, monkeypatch):
    import httpx

    from app.cache.client import clear_cache_backend
    from app.core.config import get_settings
    from app.core.database import get_session_local
    from app.logs.models import ModelLog

    captured: dict[str, object] = {}

    def fake_post(url, *, headers, json, timeout):
        captured["url"] = url
        captured["authorization"] = headers["Authorization"]
        captured["model"] = json["model"]
        captured["content"] = json["messages"][0]["content"]
        return httpx.Response(
            200,
            request=httpx.Request("POST", url),
            json={
                "choices": [{"message": {"content": "The image shows a plotted curve."}}],
                "usage": {"prompt_tokens": 5, "completion_tokens": 7},
            },
        )

    monkeypatch.setenv("VISION_LLM_API_KEY", "vision-key")
    monkeypatch.setenv("VISION_LLM_BASE_URL", "https://vision.example/v1")
    monkeypatch.setenv("VISION_LLM_MODEL", "vision-model")
    monkeypatch.setattr(httpx, "post", fake_post)
    get_settings.cache_clear()
    clear_cache_backend()
    headers = _auth_headers(client, username="ai_vision_teacher")

    response = client.post(
        "/api/ai/vision/analyze",
        headers=headers,
        data={"prompt": "Describe this teaching image."},
        files={"file": ("plot.png", b"\x89PNG\r\n\x1a\nimage-bytes", "image/png")},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["content"] == "The image shows a plotted curve."
    assert body["provider_status"]["provider"] == "real"
    assert body["provider_status"]["model"] == "vision-model"
    assert captured["url"] == "https://vision.example/v1/chat/completions"
    assert captured["authorization"] == "Bearer vision-key"
    assert captured["content"][0]["text"] == "Describe this teaching image."

    session_local = get_session_local()
    with session_local() as db:
        log = db.query(ModelLog).filter(ModelLog.task_type == "vision").one()

    assert log.model == "vision-model"
    assert log.prompt_tokens == 5
    assert log.completion_tokens == 7


def test_generate_text_without_key_raises_when_mock_fallback_disabled(client, monkeypatch):
    from app.ai.service import generate_text
    from app.core.config import get_settings
    from app.core.database import get_session_local
    from app.logs.models import ModelLog

    monkeypatch.setenv("LLM_API_KEY", "")
    monkeypatch.setenv("LLM_MOCK_ON_FAILURE", "false")
    get_settings.cache_clear()

    session_local = get_session_local()
    with session_local() as db:
        with pytest.raises(RuntimeError, match="LLM_API_KEY is not configured"):
            generate_text(db, "lesson", "请生成一节课程")
        log = db.query(ModelLog).one()

    assert log.task_type == "lesson"
    assert log.provider == "real"
    assert log.fallback_used is False
    assert log.success is False


def test_review_generation_uses_review_provider_credentials(client, monkeypatch):
    import httpx

    from app.ai.service import review_generated_content
    from app.core.config import get_settings
    from app.core.database import get_session_local

    captured: dict[str, object] = {}

    def fake_post(url, *, headers, json, timeout):
        captured["url"] = url
        captured["authorization"] = headers["Authorization"]
        captured["model"] = json["model"]
        return httpx.Response(
            200,
            request=httpx.Request("POST", url),
            json={
                "choices": [
                    {
                        "message": {
                            "content": "Status: passed\nSuggestions: 内容可用。"
                        }
                    }
                ],
                "usage": {"prompt_tokens": 3, "completion_tokens": 4},
            },
        )

    monkeypatch.setenv("LLM_API_KEY", "generate-key")
    monkeypatch.setenv("LLM_BASE_URL", "https://generate.example/v1")
    monkeypatch.setenv("REVIEW_LLM_API_KEY", "review-key")
    monkeypatch.setenv("REVIEW_LLM_BASE_URL", "https://review.example/v1")
    monkeypatch.setenv("LLM_REVIEW_MODEL", "review-model")
    monkeypatch.setenv("LLM_MULTI_AGENT_REVIEW", "true")
    monkeypatch.setattr(httpx, "post", fake_post)
    get_settings.cache_clear()

    session_local = get_session_local()
    with session_local() as db:
        review = review_generated_content(db, task_type="exercise", content="课堂练习")

    assert review.enabled is True
    assert review.reviewer_model == "review-model"
    assert captured["url"] == "https://review.example/v1/chat/completions"
    assert captured["authorization"] == "Bearer review-key"
    assert captured["model"] == "review-model"


def test_review_generation_preserves_content_when_reviewer_times_out(client, monkeypatch):
    import httpx

    from app.ai.service import review_generated_content
    from app.core.config import get_settings
    from app.core.database import get_session_local

    def fake_post(url, *, headers, json, timeout):
        raise httpx.ReadTimeout(
            "review timed out",
            request=httpx.Request("POST", url),
        )

    monkeypatch.setenv("LLM_API_KEY", "generate-key")
    monkeypatch.setenv("REVIEW_LLM_API_KEY", "review-key")
    monkeypatch.setenv("REVIEW_LLM_BASE_URL", "https://review.example/v1")
    monkeypatch.setenv("LLM_REVIEW_MODEL", "review-model")
    monkeypatch.setenv("LLM_MULTI_AGENT_REVIEW", "true")
    monkeypatch.setenv("LLM_MOCK_ON_FAILURE", "false")
    monkeypatch.setattr(httpx, "post", fake_post)
    get_settings.cache_clear()

    session_local = get_session_local()
    with session_local() as db:
        review = review_generated_content(
            db,
            task_type="exercise",
            content="Generated exercise content.",
        )

    assert review.enabled is True
    assert review.status == "failed"
    assert review.reviewer_model == "review-model"
    assert review.revised_content is None
    assert review.raw_review == ""
    assert review.warnings == ["Reviewer request failed. Generated content was preserved."]
    assert review.suggestions == ["Retry the review later."]


def test_review_generation_calls_revise_provider_when_warnings_present(client, monkeypatch):
    import httpx

    from app.ai.service import review_generated_content
    from app.core.config import get_settings
    from app.core.database import get_session_local

    calls: list[dict[str, object]] = []

    def fake_post(url, *, headers, json, timeout):
        calls.append(
            {
                "url": url,
                "authorization": headers["Authorization"],
                "model": json["model"],
                "prompt": json["messages"][0]["content"],
            }
        )
        if "review.example" in url:
            content = "Status: warning\nWarnings: 题型不匹配\nSuggestions: 改成综合题"
        else:
            content = "修订后的综合题内容"
        return httpx.Response(
            200,
            request=httpx.Request("POST", url),
            json={
                "choices": [{"message": {"content": content}}],
                "usage": {"prompt_tokens": 3, "completion_tokens": 4},
            },
        )

    monkeypatch.setenv("LLM_API_KEY", "generate-key")
    monkeypatch.setenv("LLM_BASE_URL", "https://generate.example/v1")
    monkeypatch.setenv("REVIEW_LLM_API_KEY", "review-key")
    monkeypatch.setenv("REVIEW_LLM_BASE_URL", "https://review.example/v1")
    monkeypatch.setenv("LLM_REVIEW_MODEL", "review-model")
    monkeypatch.setenv("REVISE_LLM_API_KEY", "revise-key")
    monkeypatch.setenv("REVISE_LLM_BASE_URL", "https://revise.example/v1")
    monkeypatch.setenv("LLM_REVISE_MODEL", "revise-model")
    monkeypatch.setenv("LLM_MULTI_AGENT_REVIEW", "true")
    monkeypatch.setattr(httpx, "post", fake_post)
    get_settings.cache_clear()

    session_local = get_session_local()
    with session_local() as db:
        review = review_generated_content(db, task_type="exercise", content="原始综合题内容")

    assert review.status == "warning"
    assert review.revised_content == "修订后的综合题内容"
    assert len(calls) == 2
    assert calls[0]["url"] == "https://review.example/v1/chat/completions"
    assert calls[0]["authorization"] == "Bearer review-key"
    assert calls[0]["model"] == "review-model"
    assert calls[1]["url"] == "https://revise.example/v1/chat/completions"
    assert calls[1]["authorization"] == "Bearer revise-key"
    assert calls[1]["model"] == "revise-model"
    assert "Warnings: 题型不匹配" in str(calls[1]["prompt"])


def test_review_generation_preserves_content_when_revision_times_out(client, monkeypatch):
    import httpx

    from app.ai.service import review_generated_content
    from app.core.config import get_settings
    from app.core.database import get_session_local

    def fake_post(url, *, headers, json, timeout):
        if "review.example" in url:
            return httpx.Response(
                200,
                request=httpx.Request("POST", url),
                json={
                    "choices": [
                        {
                            "message": {
                                "content": (
                                    "Warnings: Answer needs clarification\n"
                                    "Suggestions: Add a clearer explanation"
                                )
                            }
                        }
                    ],
                },
            )
        raise httpx.ReadTimeout(
            "revision timed out",
            request=httpx.Request("POST", url),
        )

    monkeypatch.setenv("LLM_API_KEY", "generate-key")
    monkeypatch.setenv("REVIEW_LLM_API_KEY", "review-key")
    monkeypatch.setenv("REVIEW_LLM_BASE_URL", "https://review.example/v1")
    monkeypatch.setenv("LLM_REVIEW_MODEL", "review-model")
    monkeypatch.setenv("REVISE_LLM_API_KEY", "revise-key")
    monkeypatch.setenv("REVISE_LLM_BASE_URL", "https://revise.example/v1")
    monkeypatch.setenv("LLM_REVISE_MODEL", "revise-model")
    monkeypatch.setenv("LLM_MULTI_AGENT_REVIEW", "true")
    monkeypatch.setenv("LLM_MOCK_ON_FAILURE", "false")
    monkeypatch.setattr(httpx, "post", fake_post)
    get_settings.cache_clear()

    session_local = get_session_local()
    with session_local() as db:
        review = review_generated_content(
            db,
            task_type="exercise",
            content="Generated exercise content.",
        )

    assert review.status == "warning"
    assert review.revised_content is None
    assert review.warnings == ["Warnings: Answer needs clarification"]
    assert review.suggestions == [
        "Suggestions: Add a clearer explanation",
        "Automatic revision failed; original content was preserved.",
    ]


def test_generate_text_can_use_explicit_mock_fallback_for_lesson_and_logs(client, monkeypatch):
    from app.ai.service import generate_text
    from app.core.config import get_settings
    from app.core.database import get_session_local
    from app.logs.models import ModelLog

    monkeypatch.setenv("LLM_API_KEY", "")
    monkeypatch.setenv("LLM_MOCK_ON_FAILURE", "true")
    get_settings.cache_clear()

    session_local = get_session_local()
    with session_local() as db:
        result = generate_text(db, "lesson", "请生成一节课程")
        log = db.query(ModelLog).one()

    assert result.content
    assert "教学目标" in result.content
    assert result.provider == "mock"
    assert result.model == "mock-generator"
    assert result.fallback_used is True
    assert log.task_type == "lesson"
    assert log.provider == "mock"
    assert log.fallback_used is True
    assert log.success is True


def test_generate_text_can_use_explicit_mock_fallback_for_exercise(client, monkeypatch):
    from app.ai.service import generate_text
    from app.core.config import get_settings
    from app.core.database import get_session_local

    monkeypatch.setenv("LLM_API_KEY", "")
    monkeypatch.setenv("LLM_MOCK_ON_FAILURE", "true")
    get_settings.cache_clear()

    session_local = get_session_local()
    with session_local() as db:
        result = generate_text(db, "exercise", "请生成练习题")

    assert result.provider == "mock"
    assert result.fallback_used is True
    assert "答案" in result.content


def test_generate_text_does_not_commit_pending_caller_changes(client, monkeypatch):
    from app.ai.service import generate_text
    from app.core.config import get_settings
    from app.core.database import get_session_local
    from app.logs.models import OperationLog

    monkeypatch.setenv("LLM_API_KEY", "")
    monkeypatch.setenv("LLM_MOCK_ON_FAILURE", "true")
    get_settings.cache_clear()

    session_local = get_session_local()
    with session_local() as db:
        db.add(OperationLog(action="pending-ai-transaction-boundary"))
        generate_text(db, "lesson", "请生成一节课程")
        db.rollback()

    with session_local() as db:
        persisted = (
            db.query(OperationLog)
            .filter(OperationLog.action == "pending-ai-transaction-boundary")
            .first()
        )

    assert persisted is None


def test_init_db_migrates_old_model_logs_table_for_ai_logging(monkeypatch, tmp_path):
    from sqlalchemy import create_engine, inspect, text

    from app.auth import models as auth_models  # noqa: F401
    from app.ai.service import generate_text
    from app.core.config import get_settings
    from app.core.database import clear_database_caches, get_session_local, init_db
    from app.logs import models as logs_models  # noqa: F401
    from app.logs.models import ModelLog

    database_url = f"sqlite:///{tmp_path / 'legacy.db'}"
    engine = create_engine(database_url)
    with engine.begin() as connection:
        connection.execute(
            text(
                """
                CREATE TABLE model_logs (
                    id INTEGER PRIMARY KEY,
                    user_id INTEGER NULL,
                    provider VARCHAR(64) NOT NULL,
                    model VARCHAR(128) NOT NULL,
                    prompt_tokens INTEGER NULL,
                    completion_tokens INTEGER NULL,
                    status VARCHAR(32) NOT NULL,
                    error TEXT NULL,
                    created_at DATETIME NULL
                )
                """
            )
        )
    engine.dispose()

    monkeypatch.setenv("LLM_API_KEY", "")
    monkeypatch.setenv("LLM_MOCK_ON_FAILURE", "true")
    get_settings.cache_clear()
    clear_database_caches()

    init_db(database_url)

    migrated_engine = create_engine(database_url)
    columns = {
        column["name"] for column in inspect(migrated_engine).get_columns("model_logs")
    }
    migrated_engine.dispose()

    assert {
        "task_type",
        "latency_ms",
        "success",
        "fallback_used",
        "error_message",
    }.issubset(columns)

    session_local = get_session_local(database_url)
    with session_local() as db:
        result = generate_text(db, "lesson", "请生成一节课程")
        log = db.query(ModelLog).one()

    assert result.provider == "mock"
    assert log.task_type == "lesson"
    assert log.fallback_used is True

    get_settings.cache_clear()
    clear_database_caches()
