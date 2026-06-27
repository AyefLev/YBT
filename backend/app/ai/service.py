from time import perf_counter
from typing import Any

import httpx
from sqlalchemy.orm import Session

from app.ai.mock import mock_generate
from app.ai.prompts import build_revise_prompt, build_review_prompt
from app.ai.schemas import AIResult, AIReview, ModelConnectivityCheck
from app.ai.config_service import get_ai_provider_config
from app.ai.embeddings import embed_text
from app.core.config import get_settings
from app.logs.models import ModelLog


class ProviderConfig:
    def __init__(
        self,
        *,
        role: str,
        base_url: str,
        api_key: str,
        model: str,
        prompt_price_per_1k: float = 0.0,
        completion_price_per_1k: float = 0.0,
        currency: str = "CNY",
    ) -> None:
        self.role = role
        self.base_url = base_url
        self.api_key = api_key
        self.model = model
        self.prompt_price_per_1k = prompt_price_per_1k
        self.completion_price_per_1k = completion_price_per_1k
        self.currency = currency or "CNY"


def generate_text(
    db: Session,
    task_type: str,
    prompt: str,
    *,
    model: str | None = None,
    user_id: int | None = None,
) -> AIResult:
    settings = get_settings()
    provider_config = _provider_config_for_task(settings, task_type, model=model, db=db)
    selected_model = provider_config.model
    started = perf_counter()

    try:
        if not provider_config.api_key:
            raise RuntimeError(f"{_provider_key_name(task_type)} is not configured")

        response_payload = _call_real_provider(settings, provider_config, prompt)
        content = _extract_content(response_payload)
        usage = response_payload.get("usage", {})
        result = AIResult(
            content=content,
            provider="real",
            model=selected_model,
            fallback_used=False,
        )
        _write_model_log(
            db=db,
            task_type=task_type,
            result=result,
            latency_ms=_elapsed_ms(started),
            success=True,
            prompt_tokens=usage.get("prompt_tokens"),
            completion_tokens=usage.get("completion_tokens"),
            user_id=user_id,
            provider_config=provider_config,
        )
        return result
    except Exception as exc:
        if not settings.llm_mock_on_failure:
            _write_model_log(
                db=db,
                task_type=task_type,
                result=AIResult(
                    content="",
                    provider="real",
                    model=selected_model,
                    fallback_used=False,
                    error_message=str(exc),
                ),
                latency_ms=_elapsed_ms(started),
                success=False,
                user_id=user_id,
                provider_config=provider_config,
            )
            raise

        result = AIResult(
            content=mock_generate(task_type, prompt),
            provider="mock",
            model="mock-generator",
            fallback_used=True,
            error_message=str(exc),
        )
        _write_model_log(
            db=db,
            task_type=task_type,
            result=result,
            latency_ms=_elapsed_ms(started),
            success=True,
            user_id=user_id,
            provider_config=provider_config,
        )
        return result


def review_generated_content(
    db: Session,
    *,
    task_type: str,
    content: str,
    enabled: bool | None = None,
    auto_revise: bool = True,
    user_id: int | None = None,
) -> AIReview:
    settings = get_settings()
    reviewer_model = _provider_config_for_role(settings, "review", db=db).model
    review_enabled = settings.llm_multi_agent_review if enabled is None else enabled
    if not review_enabled:
        return AIReview(
            enabled=False,
            status="skipped",
            reviewer_model=reviewer_model,
            warnings=[],
            suggestions=[],
            raw_review="",
        )

    prompt = build_review_prompt(task_type, content)
    result = generate_text(
        db,
        f"{task_type}_review",
        prompt,
        model=reviewer_model,
        user_id=user_id,
    )
    warnings, suggestions = _extract_review_items(result.content)
    status = "warning" if warnings else "passed"
    revised_content = None
    if warnings and auto_revise:
        revise_model = _provider_config_for_role(settings, "revise", db=db).model
        revise_prompt = build_revise_prompt(task_type, content, result.content)
        revise_result = generate_text(
            db,
            f"{task_type}_revise",
            revise_prompt,
            model=revise_model,
            user_id=user_id,
        )
        revised_content = revise_result.content

    return AIReview(
        enabled=True,
        status=status,
        reviewer_model=result.model,
        warnings=warnings,
        suggestions=suggestions or ["Reviewer did not report blocking issues."],
        raw_review=result.content,
        revised_content=revised_content,
    )


def check_model_connectivity(
    role: str,
    *,
    db: Session | None = None,
    probe: bool = False,
) -> ModelConnectivityCheck:
    settings = get_settings()
    task_type = _role_task_type(role)
    if role == "vision":
        provider_config = _provider_config_for_role(settings, "vision", db=db)
        configured = bool(provider_config.api_key and provider_config.model)
        return ModelConnectivityCheck(
            role=role,
            model=provider_config.model,
            configured=configured,
            status="not_tested" if configured else "not_configured",
            message=(
                "视觉模型已配置，当前版本仅做配置检查。"
                if configured
                else "VISION_LLM_API_KEY 或 VISION_LLM_MODEL 未配置。"
            ),
        )
    if role == "embedding":
        provider_config = _provider_config_for_role(settings, "embedding", db=db)
        configured = bool(provider_config.model)
        if not probe:
            return ModelConnectivityCheck(
                role=role,
                model=provider_config.model,
                configured=configured,
                status="not_tested",
                message="向量模型使用本地离线模式，或由管理员配置 API 后启用。",
            )
        started = perf_counter()
        try:
            embed_text("连通性检测", dimensions=settings.embedding_dimensions, db=db)
        except Exception as exc:
            return ModelConnectivityCheck(
                role=role,
                model=provider_config.model,
                configured=configured,
                status="failed",
                latency_ms=_elapsed_ms(started),
                message=str(exc),
            )
        return ModelConnectivityCheck(
            role=role,
            model=provider_config.model,
            configured=configured,
            status="success",
            latency_ms=_elapsed_ms(started),
            message="向量模型可用。",
        )

    provider_config = _provider_config_for_task(settings, task_type, db=db)
    configured = bool(provider_config.api_key)
    if not configured:
        return ModelConnectivityCheck(
            role=role,
            model=provider_config.model,
            configured=False,
            status="not_configured",
            message=f"{_provider_key_name(task_type)} is not configured",
        )
    if not probe:
        return ModelConnectivityCheck(
            role=role,
            model=provider_config.model,
            configured=True,
            status="not_tested",
            message="已配置，尚未发起真实请求。",
        )

    started = perf_counter()
    try:
        _call_real_provider(settings, provider_config, "请只回复 ok，用于 API 连通性检测。")
    except Exception as exc:
        return ModelConnectivityCheck(
            role=role,
            model=provider_config.model,
            configured=True,
            status="failed",
            latency_ms=_elapsed_ms(started),
            message=str(exc),
        )
    return ModelConnectivityCheck(
        role=role,
        model=provider_config.model,
        configured=True,
        status="success",
        latency_ms=_elapsed_ms(started),
        message="真实模型 API 请求成功。",
    )


def _call_real_provider(settings: Any, provider_config: ProviderConfig, prompt: str) -> dict[str, Any]:
    url = f"{provider_config.base_url.rstrip('/')}/chat/completions"
    response = httpx.post(
        url,
        headers={"Authorization": f"Bearer {provider_config.api_key}"},
        json={
            "model": provider_config.model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.7,
        },
        timeout=settings.llm_timeout_seconds,
    )
    response.raise_for_status()
    return response.json()


def _provider_config_for_task(
    settings: Any,
    task_type: str,
    *,
    model: str | None = None,
    db: Session | None = None,
) -> ProviderConfig:
    role = _task_role(task_type)
    provider_config = _provider_config_for_role(settings, role, db=db)
    if model:
        provider_config.model = model
    return provider_config


def _provider_config_for_role(
    settings: Any,
    role: str,
    *,
    db: Session | None = None,
) -> ProviderConfig:
    db_config = get_ai_provider_config(db, role=role) if db is not None else None
    if db_config and db_config.enabled:
        return ProviderConfig(
            role=role,
            base_url=db_config.base_url or _settings_base_url(settings, role),
            api_key=db_config.api_key or _settings_api_key(settings, role),
            model=db_config.model or _settings_model(settings, role),
            prompt_price_per_1k=db_config.prompt_price_per_1k or 0.0,
            completion_price_per_1k=db_config.completion_price_per_1k or 0.0,
            currency=db_config.currency or "CNY",
        )

    if role == "review":
        return ProviderConfig(
            role=role,
            base_url=settings.review_llm_base_url or settings.llm_base_url,
            api_key=settings.review_llm_api_key or settings.llm_api_key,
            model=settings.llm_review_model or settings.llm_model,
        )
    if role == "revise":
        return ProviderConfig(
            role=role,
            base_url=settings.revise_llm_base_url or settings.llm_base_url,
            api_key=settings.revise_llm_api_key or settings.llm_api_key,
            model=settings.llm_revise_model or settings.llm_model,
        )
    if role == "vision":
        return ProviderConfig(
            role=role,
            base_url=settings.vision_llm_base_url or settings.llm_base_url,
            api_key=settings.vision_llm_api_key,
            model=settings.vision_llm_model,
        )
    if role == "embedding":
        return ProviderConfig(
            role=role,
            base_url=settings.llm_base_url,
            api_key="",
            model=settings.embedding_model,
        )
    return ProviderConfig(
        role=role,
        base_url=settings.generate_llm_base_url or settings.llm_base_url,
        api_key=settings.generate_llm_api_key or settings.llm_api_key,
        model=settings.llm_generate_model or settings.llm_model,
    )


def _settings_base_url(settings: Any, role: str) -> str:
    if role == "review":
        return settings.review_llm_base_url or settings.llm_base_url
    if role == "revise":
        return settings.revise_llm_base_url or settings.llm_base_url
    if role == "vision":
        return settings.vision_llm_base_url or settings.llm_base_url
    if role == "embedding":
        return settings.llm_base_url
    return settings.generate_llm_base_url or settings.llm_base_url


def _settings_api_key(settings: Any, role: str) -> str:
    if role == "review":
        return settings.review_llm_api_key or settings.llm_api_key
    if role == "revise":
        return settings.revise_llm_api_key or settings.llm_api_key
    if role == "vision":
        return settings.vision_llm_api_key
    if role == "embedding":
        return ""
    return settings.generate_llm_api_key or settings.llm_api_key


def _settings_model(settings: Any, role: str) -> str:
    if role == "review":
        return settings.llm_review_model or settings.llm_model
    if role == "revise":
        return settings.llm_revise_model or settings.llm_model
    if role == "vision":
        return settings.vision_llm_model
    if role == "embedding":
        return settings.embedding_model
    return settings.llm_generate_model or settings.llm_model


def _task_role(task_type: str) -> str:
    if task_type.endswith("_review") or task_type == "review":
        return "review"
    if task_type.endswith("_revise") or task_type == "revise":
        return "revise"
    return "generate"


def _role_task_type(role: str) -> str:
    if role == "review":
        return "exercise_review"
    if role == "revise":
        return "exercise_revise"
    return "exercise"


def _provider_key_name(task_type: str) -> str:
    role = _task_role(task_type)
    if role == "review":
        return "REVIEW_LLM_API_KEY or LLM_API_KEY"
    if role == "revise":
        return "REVISE_LLM_API_KEY or LLM_API_KEY"
    return "GENERATE_LLM_API_KEY or LLM_API_KEY"


def _extract_content(payload: dict[str, Any]) -> str:
    choices = payload.get("choices") or []
    if not choices:
        raise RuntimeError("LLM response did not include choices")

    message = choices[0].get("message") or {}
    content = message.get("content")
    if not content:
        raise RuntimeError("LLM response did not include content")
    return content


def _write_model_log(
    db: Session,
    task_type: str,
    result: AIResult,
    latency_ms: int,
    success: bool,
    prompt_tokens: int | None = None,
    completion_tokens: int | None = None,
    user_id: int | None = None,
    provider_config: ProviderConfig | None = None,
) -> None:
    estimated_cost = _estimate_cost(
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        provider_config=provider_config,
    )
    db.add(
        ModelLog(
            user_id=user_id,
            task_type=task_type,
            provider=result.provider,
            api_role=provider_config.role if provider_config else _task_role(task_type),
            api_base_url=provider_config.base_url if provider_config else "",
            model=result.model,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            estimated_cost=estimated_cost,
            cost_currency=provider_config.currency if provider_config else "CNY",
            latency_ms=latency_ms,
            success=success,
            fallback_used=result.fallback_used,
            error_message=result.error_message or "",
            status="success" if success else "error",
            error=result.error_message,
        )
    )
    db.flush()


def _estimate_cost(
    *,
    prompt_tokens: int | None,
    completion_tokens: int | None,
    provider_config: ProviderConfig | None,
) -> float:
    if provider_config is None:
        return 0.0
    prompt_cost = (prompt_tokens or 0) * provider_config.prompt_price_per_1k / 1000
    completion_cost = (completion_tokens or 0) * provider_config.completion_price_per_1k / 1000
    return round(prompt_cost + completion_cost, 6)


def _extract_review_items(raw_review: str) -> tuple[list[str], list[str]]:
    warnings: list[str] = []
    suggestions: list[str] = []
    for line in raw_review.splitlines():
        cleaned = line.strip(" -*\t")
        if not cleaned:
            continue
        lowered = cleaned.lower()
        if "warning" in lowered or "风险" in cleaned or "问题" in cleaned:
            warnings.append(cleaned)
        elif "suggest" in lowered or "建议" in cleaned or "改进" in cleaned:
            suggestions.append(cleaned)
    return warnings[:5], suggestions[:5]


def _elapsed_ms(started: float) -> int:
    return max(0, int((perf_counter() - started) * 1000))
