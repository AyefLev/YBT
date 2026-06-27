from __future__ import annotations

import hashlib
import math
import re
from typing import Any

import httpx
from sqlalchemy.orm import Session


DEFAULT_EMBEDDING_MODEL = "local-hash-embedding-v1"
DEFAULT_EMBEDDING_DIMENSIONS = 128


def embed_text(
    text: str,
    *,
    dimensions: int = DEFAULT_EMBEDDING_DIMENSIONS,
    db: Session | None = None,
) -> list[float]:
    if db is not None:
        api_vector = _embed_text_with_configured_api(text, dimensions=dimensions, db=db)
        if api_vector is not None:
            return api_vector

    """Build a deterministic local embedding for offline demos and tests."""
    if dimensions <= 0:
        raise ValueError("Embedding dimensions must be positive.")

    vector = [0.0] * dimensions
    tokens = _tokens(text)
    if not tokens:
        return vector

    for token in tokens:
        digest = hashlib.blake2b(token.encode("utf-8"), digest_size=8).digest()
        bucket = int.from_bytes(digest[:4], "big") % dimensions
        sign = 1.0 if digest[4] % 2 == 0 else -1.0
        weight = min(2.0, max(1.0, len(token) / 4))
        vector[bucket] += sign * weight

    norm = math.sqrt(sum(value * value for value in vector))
    if norm == 0:
        return vector
    return [value / norm for value in vector]


def _tokens(text: str) -> list[str]:
    compact = "".join(text.lower().split())
    tokens: list[str] = []

    chinese_chars = [char for char in compact if "\u4e00" <= char <= "\u9fff"]
    tokens.extend(chinese_chars)
    tokens.extend(
        f"{chinese_chars[index]}{chinese_chars[index + 1]}"
        for index in range(len(chinese_chars) - 1)
    )
    tokens.extend(
        f"{chinese_chars[index]}{chinese_chars[index + 1]}{chinese_chars[index + 2]}"
        for index in range(len(chinese_chars) - 2)
    )

    tokens.extend(re.findall(r"[a-z0-9]+", text.lower()))
    return tokens


def _embed_text_with_configured_api(
    text: str,
    *,
    dimensions: int,
    db: Session,
) -> list[float] | None:
    from app.ai.config_service import get_ai_provider_config
    from app.core.config import get_settings

    config = get_ai_provider_config(db, role="embedding")
    if config is None or not config.enabled or not config.api_key or not config.model:
        return None

    settings = get_settings()
    base_url = (config.base_url or settings.llm_base_url).rstrip("/")
    payload: dict[str, Any] = {
        "model": config.model,
        "input": text,
    }
    if dimensions > 0:
        payload["dimensions"] = dimensions

    response = httpx.post(
        f"{base_url}/embeddings",
        headers={"Authorization": f"Bearer {config.api_key}"},
        json=payload,
        timeout=settings.llm_timeout_seconds,
    )
    response.raise_for_status()
    data = response.json().get("data") or []
    if not data:
        raise RuntimeError("Embedding API response did not include data")
    vector = data[0].get("embedding")
    if not isinstance(vector, list):
        raise RuntimeError("Embedding API response did not include embedding vector")
    values = [float(item) for item in vector]
    if len(values) != dimensions:
        raise RuntimeError(
            f"Embedding dimensions mismatch: expected {dimensions}, got {len(values)}"
        )
    return values
