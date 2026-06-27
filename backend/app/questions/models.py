from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class QuestionBankItem(Base):
    __tablename__ = "question_bank_items"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    course_id: Mapped[int | None] = mapped_column(
        ForeignKey("courses.id"),
        nullable=True,
        index=True,
    )
    chapter_id: Mapped[int | None] = mapped_column(
        ForeignKey("chapters.id"),
        nullable=True,
        index=True,
    )
    session_id: Mapped[int | None] = mapped_column(
        ForeignKey("lesson_sessions.id"),
        nullable=True,
        index=True,
    )
    knowledge_point_id: Mapped[int | None] = mapped_column(
        ForeignKey("knowledge_points.id"),
        nullable=True,
        index=True,
    )
    source_exercise_id: Mapped[int | None] = mapped_column(
        ForeignKey("exercises.id"),
        nullable=True,
    )
    source_material_id: Mapped[int | None] = mapped_column(
        ForeignKey("materials.id"),
        nullable=True,
    )
    title: Mapped[str] = mapped_column(String(255))
    subject: Mapped[str] = mapped_column(String(128), index=True)
    question_type: Mapped[str] = mapped_column(String(64), index=True)
    difficulty: Mapped[str] = mapped_column(String(64), index=True)
    stem: Mapped[str] = mapped_column(Text)
    options_json: Mapped[str] = mapped_column(Text, default="[]")
    answer: Mapped[str] = mapped_column(Text, default="")
    analysis: Mapped[str] = mapped_column(Text, default="")
    tags_json: Mapped[str] = mapped_column(Text, default="[]")
    status: Mapped[str] = mapped_column(String(32), default="draft", index=True)
    reviewer_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id"),
        nullable=True,
    )
    review_comment: Mapped[str] = mapped_column(Text, default="")
    reviewed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        onupdate=utc_now,
    )
