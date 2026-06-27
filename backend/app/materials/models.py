from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Material(Base):
    __tablename__ = "materials"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    title: Mapped[str] = mapped_column(String(255))
    subject: Mapped[str] = mapped_column(String(128), default="")
    purpose: Mapped[str] = mapped_column(String(128), default="")
    resource_scope: Mapped[str] = mapped_column(String(32), default="personal", index=True)
    course_id: Mapped[int | None] = mapped_column(ForeignKey("courses.id"), nullable=True, index=True)
    chapter_id: Mapped[int | None] = mapped_column(ForeignKey("chapters.id"), nullable=True, index=True)
    session_id: Mapped[int | None] = mapped_column(ForeignKey("lesson_sessions.id"), nullable=True, index=True)
    knowledge_point_id: Mapped[int | None] = mapped_column(ForeignKey("knowledge_points.id"), nullable=True, index=True)
    tags_json: Mapped[str] = mapped_column("tags", Text, default="[]")
    chunk_strategy: Mapped[str] = mapped_column(String(32), default="fixed")
    chunk_size: Mapped[int] = mapped_column(Integer, default=800)
    chunk_overlap: Mapped[int] = mapped_column(Integer, default=80)
    file_name: Mapped[str] = mapped_column(String(255))
    file_type: Mapped[str] = mapped_column(String(16), index=True)
    file_path: Mapped[str] = mapped_column(String(1024))
    uploader_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    parse_status: Mapped[str] = mapped_column(String(32), default="pending")
    parse_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )
    chunks: Mapped[list["MaterialChunk"]] = relationship(
        back_populates="material",
        cascade="all, delete-orphan",
    )
    uploader: Mapped["User"] = relationship(lazy="selectin")


class MaterialChunk(Base):
    __tablename__ = "material_chunks"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    material_id: Mapped[int] = mapped_column(ForeignKey("materials.id"), index=True)
    chunk_index: Mapped[int] = mapped_column(Integer)
    content: Mapped[str] = mapped_column(Text)
    page_no: Mapped[int | None] = mapped_column(Integer, nullable=True)
    slide_no: Mapped[int | None] = mapped_column(Integer, nullable=True)
    token_count: Mapped[int] = mapped_column(Integer)
    future_vector_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    future_embedding_model: Mapped[str | None] = mapped_column(String(255), nullable=True)
    material: Mapped[Material] = relationship(back_populates="chunks")
