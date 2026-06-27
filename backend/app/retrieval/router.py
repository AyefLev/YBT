from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.auth.models import User
from app.core.database import get_db
from app.core.deps import get_current_user
from app.retrieval.schemas import RetrievalSearchRequest, RetrievalSearchResponse
from app.retrieval.service import search_chunks_cached

router = APIRouter(prefix="/api/retrieval", tags=["retrieval"])


@router.post("/search", response_model=RetrievalSearchResponse)
def search_materials(
    payload: RetrievalSearchRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> RetrievalSearchResponse:
    _ = current_user
    chunks, cache_hit, retrieval_mode = search_chunks_cached(
        db,
        query=payload.query,
        top_k=payload.top_k,
        material_ids=payload.material_ids,
        current_user=current_user,
    )
    return RetrievalSearchResponse(
        chunks=chunks,
        cache_hit=cache_hit,
        retrieval_mode=retrieval_mode,
    )
