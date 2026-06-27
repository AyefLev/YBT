from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import httpx
from sqlalchemy.orm import Session

from app.ai.embeddings import embed_text
from app.auth.models import User
from app.core.config import Settings, get_settings
from app.materials.models import Material, MaterialChunk


@dataclass(frozen=True)
class VectorSearchHit:
    chunk_id: int
    score: float


@dataclass(frozen=True)
class VectorIndexResult:
    indexed_count: int
    provider: str
    collection: str
    enabled: bool
    message: str = ""


class VectorStoreError(RuntimeError):
    pass


def is_vector_store_configured(settings: Settings | None = None) -> bool:
    active_settings = settings or get_settings()
    return (
        active_settings.vector_store_provider.lower().strip() == "qdrant"
        and bool(active_settings.qdrant_url.strip())
    )


def index_material_vectors(db: Session, *, material: Material) -> VectorIndexResult:
    settings = get_settings()
    if not is_vector_store_configured(settings):
        return VectorIndexResult(
            indexed_count=0,
            provider=settings.vector_store_provider,
            collection=settings.qdrant_collection,
            enabled=False,
            message="Vector store is disabled; lexical retrieval fallback remains active.",
        )

    chunks = (
        db.query(MaterialChunk)
        .filter(MaterialChunk.material_id == material.id)
        .order_by(MaterialChunk.chunk_index, MaterialChunk.id)
        .all()
    )
    if not chunks:
        delete_material_vectors(material_id=material.id)
        return VectorIndexResult(
            indexed_count=0,
            provider="qdrant",
            collection=settings.qdrant_collection,
            enabled=True,
            message="No chunks to index.",
        )

    _ensure_collection(settings)
    delete_material_vectors(material_id=material.id)
    points = []
    for chunk in chunks:
        vector_id = int(chunk.id)
        points.append(
            {
                "id": vector_id,
                "vector": embed_text(
                    chunk.content,
                    dimensions=settings.embedding_dimensions,
                ),
                "payload": {
                    "chunk_id": chunk.id,
                    "material_id": chunk.material_id,
                    "owner_id": material.uploader_id,
                    "resource_scope": material.resource_scope,
                    "material_title": material.title,
                    "chunk_index": chunk.chunk_index,
                    "embedding_model": settings.embedding_model,
                },
            }
        )
        chunk.future_vector_id = str(vector_id)
        chunk.future_embedding_model = settings.embedding_model

    _request(
        "PUT",
        f"/collections/{settings.qdrant_collection}/points",
        settings=settings,
        params={"wait": "true"},
        json={"points": points},
    )
    db.flush()
    return VectorIndexResult(
        indexed_count=len(points),
        provider="qdrant",
        collection=settings.qdrant_collection,
        enabled=True,
        message=f"Indexed {len(points)} chunks.",
    )


def delete_material_vectors(*, material_id: int) -> None:
    settings = get_settings()
    if not is_vector_store_configured(settings):
        return

    try:
        _ensure_collection(settings)
        _request(
            "POST",
            f"/collections/{settings.qdrant_collection}/points/delete",
            settings=settings,
            params={"wait": "true"},
            json={
                "filter": {
                    "must": [
                        {
                            "key": "material_id",
                            "match": {"value": material_id},
                        }
                    ]
                }
            },
        )
    except Exception:
        # Deleting a material should not be blocked by a degraded vector store.
        return


def search_vectors(
    *,
    query: str,
    top_k: int,
    material_ids: list[int],
    current_user: User,
) -> list[VectorSearchHit]:
    settings = get_settings()
    if not is_vector_store_configured(settings):
        raise VectorStoreError("Vector store is not configured.")

    _ensure_collection(settings)
    must_filters: list[dict[str, Any]] = []
    if material_ids:
        must_filters.append(
            {
                "key": "material_id",
                "match": {"any": sorted(set(material_ids))},
            }
        )

    vector_filter: dict[str, Any] = {"must": must_filters}
    if (
        "material:view_all" not in current_user.permission_codes
        and "material:manage_all" not in current_user.permission_codes
    ):
        vector_filter["should"] = [
            {
                "key": "owner_id",
                "match": {"value": current_user.id},
            },
            {
                "key": "resource_scope",
                "match": {"value": "public"},
            },
        ]

    payload = {
        "vector": embed_text(query, dimensions=settings.embedding_dimensions),
        "limit": top_k,
        "with_payload": True,
        "with_vector": False,
        "filter": vector_filter,
    }
    response = _request(
        "POST",
        f"/collections/{settings.qdrant_collection}/points/search",
        settings=settings,
        json=payload,
    )
    raw_hits = response.get("result") or []
    hits: list[VectorSearchHit] = []
    for item in raw_hits:
        payload = item.get("payload") or {}
        chunk_id = payload.get("chunk_id") or item.get("id")
        if chunk_id is None:
            continue
        hits.append(VectorSearchHit(chunk_id=int(chunk_id), score=float(item.get("score") or 0)))
    return hits


def check_vector_store_health() -> VectorIndexResult:
    settings = get_settings()
    if not is_vector_store_configured(settings):
        return VectorIndexResult(
            indexed_count=0,
            provider=settings.vector_store_provider,
            collection=settings.qdrant_collection,
            enabled=False,
            message="未配置向量数据库，知识库检索将自动回退关键词检索。",
        )

    _ensure_collection(settings)
    return VectorIndexResult(
        indexed_count=0,
        provider="qdrant",
        collection=settings.qdrant_collection,
        enabled=True,
        message="Qdrant 向量数据库连接正常。",
    )


def _ensure_collection(settings: Settings) -> None:
    collection = settings.qdrant_collection
    response = _request(
        "GET",
        f"/collections/{collection}",
        settings=settings,
        raise_for_status=False,
    )
    if response.get("status_code") == 200:
        return
    if response.get("status_code") not in {404, 409}:
        raise VectorStoreError(str(response))

    create_response = _request(
        "PUT",
        f"/collections/{collection}",
        settings=settings,
        raise_for_status=False,
        json={
            "vectors": {
                "size": settings.embedding_dimensions,
                "distance": "Cosine",
            }
        },
    )
    if create_response.get("status_code") not in {200, 201, 409}:
        raise VectorStoreError(str(create_response))


def _request(
    method: str,
    path: str,
    *,
    settings: Settings,
    raise_for_status: bool = True,
    **kwargs: Any,
) -> dict[str, Any]:
    url = f"{settings.qdrant_url.rstrip('/')}{path}"
    try:
        response = httpx.request(
            method,
            url,
            timeout=settings.qdrant_timeout_seconds,
            **kwargs,
        )
    except httpx.HTTPError as exc:
        raise VectorStoreError(str(exc)) from exc

    if raise_for_status:
        try:
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            raise VectorStoreError(str(exc)) from exc
    if not response.content:
        return {"status_code": response.status_code}
    payload = response.json()
    if isinstance(payload, dict):
        payload.setdefault("status_code", response.status_code)
        return payload
    return {"status_code": response.status_code, "result": payload}
