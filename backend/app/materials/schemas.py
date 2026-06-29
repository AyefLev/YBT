from datetime import datetime

from pydantic import BaseModel, ConfigDict


class MaterialRead(BaseModel):
    id: int
    title: str
    subject: str
    purpose: str
    resource_scope: str = "personal"
    course_id: int | None = None
    chapter_id: int | None = None
    session_id: int | None = None
    knowledge_point_id: int | None = None
    chunk_strategy: str = "fixed"
    chunk_size: int = 800
    chunk_overlap: int = 80
    tags: list[str]
    file_name: str
    file_type: str
    file_path: str
    uploader_id: int
    uploader_name: str = ""
    uploader_username: str = ""
    parse_status: str
    parse_error: str | None
    created_at: datetime
    chunk_count: int

    model_config = ConfigDict(from_attributes=True)


class MaterialChunkRead(BaseModel):
    id: int
    material_id: int
    chunk_index: int
    content: str
    page_no: int | None
    slide_no: int | None
    token_count: int

    model_config = ConfigDict(from_attributes=True)


class MaterialParseStatusRead(BaseModel):
    material_id: int
    status: str
    detail: str
    error_message: str | None = None
    cache_hit: bool = False
    phase: str = ""
    current_page: int | None = None
    total_pages: int | None = None
    percent: int | None = None
