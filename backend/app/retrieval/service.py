import hashlib
import json

from sqlalchemy.orm import Session

from app.auth.models import User
from app.cache.service import get_cache
from app.materials.models import Material, MaterialChunk
from app.retrieval.schemas import RetrievedChunk
from app.retrieval.vector_store import VectorSearchHit, search_vectors


def search_chunks(
    db: Session,
    *,
    query: str,
    top_k: int,
    material_ids: list[int],
    current_user: User,
) -> list[RetrievedChunk]:
    chunks, _ = search_chunks_with_mode(
        db,
        query=query,
        top_k=top_k,
        material_ids=material_ids,
        current_user=current_user,
    )
    return chunks


def search_chunks_with_mode(
    db: Session,
    *,
    query: str,
    top_k: int,
    material_ids: list[int],
    current_user: User,
) -> tuple[list[RetrievedChunk], str]:
    try:
        vector_hits = search_vectors(
            db=db,
            query=query,
            top_k=top_k,
            material_ids=material_ids,
            current_user=current_user,
        )
        vector_chunks = _chunks_from_vector_hits(
            db,
            hits=vector_hits,
            material_ids=material_ids,
            current_user=current_user,
        )
        if vector_chunks:
            return vector_chunks, "vector"
    except Exception:
        pass

    return _search_chunks_lexical(
        db,
        query=query,
        top_k=top_k,
        material_ids=material_ids,
        current_user=current_user,
    ), "lexical"


def _search_chunks_lexical(
    db: Session,
    *,
    query: str,
    top_k: int,
    material_ids: list[int],
    current_user: User,
) -> list[RetrievedChunk]:
    db_query = db.query(MaterialChunk).join(Material)
    db_query = _apply_material_access_filter(db_query, current_user=current_user)
    if material_ids:
        db_query = db_query.filter(MaterialChunk.material_id.in_(material_ids))

    ranked: list[tuple[float, MaterialChunk]] = []
    for chunk in db_query.all():
        score = _score(query, chunk.content)
        if score > 0:
            ranked.append((score, chunk))

    ranked.sort(key=lambda item: (-item[0], item[1].id))
    return [
        RetrievedChunk(
            id=chunk.id,
            material_id=chunk.material_id,
            material_title=chunk.material.title,
            source=chunk.material.title,
            content=chunk.content,
            page_no=chunk.page_no,
            slide_no=chunk.slide_no,
            score=score,
        )
        for score, chunk in ranked[:top_k]
    ]


def _chunks_from_vector_hits(
    db: Session,
    *,
    hits: list[VectorSearchHit],
    material_ids: list[int],
    current_user: User,
) -> list[RetrievedChunk]:
    if not hits:
        return []

    hit_scores = {hit.chunk_id: hit.score for hit in hits}
    chunk_ids = list(hit_scores)
    db_query = db.query(MaterialChunk).join(Material)
    db_query = _apply_material_access_filter(db_query, current_user=current_user)
    db_query = db_query.filter(MaterialChunk.id.in_(chunk_ids))
    if material_ids:
        db_query = db_query.filter(MaterialChunk.material_id.in_(material_ids))

    chunks_by_id = {chunk.id: chunk for chunk in db_query.all()}
    chunks: list[RetrievedChunk] = []
    for hit in hits:
        chunk = chunks_by_id.get(hit.chunk_id)
        if chunk is None:
            continue
        chunks.append(
            RetrievedChunk(
                id=chunk.id,
                material_id=chunk.material_id,
                material_title=chunk.material.title,
                source=chunk.material.title,
                content=chunk.content,
                page_no=chunk.page_no,
                slide_no=chunk.slide_no,
                score=hit.score,
            )
        )
    return chunks


def search_chunks_cached(
    db: Session,
    *,
    query: str,
    top_k: int,
    material_ids: list[int],
    current_user: User,
) -> tuple[list[RetrievedChunk], bool, str]:
    cache_key = _retrieval_cache_key(
        user_id=current_user.id,
        query=query,
        top_k=top_k,
        material_ids=material_ids,
    )
    cache = get_cache()
    cached = cache.get(cache_key)
    if cached:
        try:
            payload = json.loads(cached)
        except json.JSONDecodeError:
            payload = None
        if isinstance(payload, list):
            return [RetrievedChunk.model_validate(item) for item in payload], True, "cache"
        if isinstance(payload, dict):
            raw_chunks = payload.get("chunks") or []
            if isinstance(raw_chunks, list):
                return (
                    [RetrievedChunk.model_validate(item) for item in raw_chunks],
                    True,
                    str(payload.get("retrieval_mode") or "cache"),
                )

    chunks, retrieval_mode = search_chunks_with_mode(
        db,
        query=query,
        top_k=top_k,
        material_ids=material_ids,
        current_user=current_user,
    )
    cache.set(
        cache_key,
        json.dumps(
            {
                "chunks": [chunk.model_dump() for chunk in chunks],
                "retrieval_mode": retrieval_mode,
            },
            ensure_ascii=False,
        ),
        ttl_seconds=120,
    )
    return chunks, False, retrieval_mode


def _retrieval_cache_key(
    *,
    user_id: int,
    query: str,
    top_k: int,
    material_ids: list[int],
) -> str:
    normalized_payload = {
        "user_id": user_id,
        "query": _normalize(query),
        "top_k": top_k,
        "material_ids": sorted(set(material_ids)),
    }
    digest = hashlib.sha256(
        json.dumps(normalized_payload, ensure_ascii=False, sort_keys=True).encode("utf-8")
    ).hexdigest()
    return f"retrieval:search:{digest}"


def _apply_material_access_filter(db_query, *, current_user: User):
    if (
        "material:view_all" in current_user.permission_codes
        or "material:manage_all" in current_user.permission_codes
    ):
        return db_query
    return db_query.filter(
        (Material.uploader_id == current_user.id)
        | (Material.resource_scope == "public")
    )


def _score(query: str, content: str) -> float:
    normalized_query = _normalize(query)
    normalized_content = _normalize(content)
    if not normalized_query or not normalized_content:
        return 0.0
    if normalized_query in normalized_content:
        return float(len(normalized_query) + 10)

    query_grams = _chinese_bigrams(normalized_query)
    content_grams = _chinese_bigrams(normalized_content)
    if not query_grams or not content_grams:
        return 0.0

    score = len(query_grams & content_grams) / len(query_grams)
    return score if score >= 0.25 else 0.0


def _normalize(value: str) -> str:
    return "".join(value.lower().split())


def _chinese_bigrams(value: str) -> set[str]:
    chinese_chars = [char for char in value if "\u4e00" <= char <= "\u9fff"]
    return {
        f"{chinese_chars[index]}{chinese_chars[index + 1]}"
        for index in range(len(chinese_chars) - 1)
    }
