from pydantic import BaseModel, Field


class RetrievalSearchRequest(BaseModel):
    query: str = Field(min_length=1)
    top_k: int = Field(default=5, ge=1, le=50)
    material_ids: list[int] = []


class RetrievedChunk(BaseModel):
    id: int
    material_id: int
    material_title: str
    source: str
    content: str
    page_no: int | None
    slide_no: int | None
    score: float


class RetrievalSearchResponse(BaseModel):
    chunks: list[RetrievedChunk]
    cache_hit: bool = False
    retrieval_mode: str = "lexical"
