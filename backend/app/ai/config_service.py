from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ai.config_schemas import AIProviderConfigRead, AIProviderConfigUpdate
from app.ai.models import AIProviderConfig

CONFIG_ROLES = ("generate", "review", "revise", "vision", "embedding")


def list_ai_provider_configs(db: Session) -> list[AIProviderConfigRead]:
    existing = {
        config.role: config
        for config in db.scalars(select(AIProviderConfig)).all()
    }
    return [
        ai_provider_config_to_read(existing.get(role), role=role)
        for role in CONFIG_ROLES
    ]


def upsert_ai_provider_config(
    db: Session,
    *,
    role: str,
    payload: AIProviderConfigUpdate,
) -> AIProviderConfig:
    normalized_role = _normalize_role(role)
    config = db.scalar(select(AIProviderConfig).where(AIProviderConfig.role == normalized_role))
    if config is None:
        config = AIProviderConfig(role=normalized_role)
        db.add(config)

    updates = payload.model_dump(exclude_unset=True)
    if "base_url" in updates and updates["base_url"] is not None:
        config.base_url = updates["base_url"].strip()
    if "model" in updates and updates["model"] is not None:
        config.model = updates["model"].strip()
    if "prompt_price_per_1k" in updates and updates["prompt_price_per_1k"] is not None:
        config.prompt_price_per_1k = float(updates["prompt_price_per_1k"])
    if "completion_price_per_1k" in updates and updates["completion_price_per_1k"] is not None:
        config.completion_price_per_1k = float(updates["completion_price_per_1k"])
    if "currency" in updates and updates["currency"] is not None:
        config.currency = updates["currency"].strip().upper() or "CNY"
    if "enabled" in updates and updates["enabled"] is not None:
        config.enabled = bool(updates["enabled"])
    if payload.clear_api_key:
        config.api_key = ""
    elif payload.api_key is not None:
        config.api_key = payload.api_key.strip()

    db.flush()
    return config


def get_ai_provider_config(db: Session, *, role: str) -> AIProviderConfig | None:
    return db.scalar(select(AIProviderConfig).where(AIProviderConfig.role == _normalize_role(role)))


def ai_provider_config_to_read(
    config: AIProviderConfig | None,
    *,
    role: str | None = None,
) -> AIProviderConfigRead:
    api_key = config.api_key if config else ""
    return AIProviderConfigRead(
        role=config.role if config else _normalize_role(role or "generate"),
        base_url=config.base_url if config else "",
        model=config.model if config else "",
        prompt_price_per_1k=config.prompt_price_per_1k if config else 0.0,
        completion_price_per_1k=config.completion_price_per_1k if config else 0.0,
        currency=config.currency if config else "CNY",
        enabled=config.enabled if config else False,
        api_key_configured=bool(api_key),
        api_key_preview=_preview_api_key(api_key),
        updated_at=config.updated_at if config else None,
    )


def _normalize_role(role: str) -> str:
    normalized = role.strip().lower()
    if normalized not in CONFIG_ROLES:
        raise ValueError(f"Unsupported AI provider role: {role}")
    return normalized


def _preview_api_key(api_key: str) -> str:
    if not api_key:
        return ""
    if len(api_key) <= 8:
        return "****"
    return f"{api_key[:4]}...{api_key[-4:]}"
