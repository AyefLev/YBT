from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Exercise(Base):
    __tablename__ = "exercises"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    course_id: Mapped[int | None] = mapped_column(ForeignKey("courses.id"), nullable=True, index=True)
    chapter_id: Mapped[int | None] = mapped_column(ForeignKey("chapters.id"), nullable=True, index=True)
    session_id: Mapped[int | None] = mapped_column(ForeignKey("lesson_sessions.id"), nullable=True, index=True)
    knowledge_point_id: Mapped[int | None] = mapped_column(ForeignKey("knowledge_points.id"), nullable=True, index=True)
    lesson_id: Mapped[int | None] = mapped_column(ForeignKey("lessons.id"), nullable=True, index=True)
    title: Mapped[str] = mapped_column(String(255))
    subject: Mapped[str] = mapped_column(String(128))
    knowledge_point: Mapped[str] = mapped_column(String(255))
    question_type: Mapped[str] = mapped_column(String(128))
    difficulty: Mapped[str] = mapped_column(String(64))
    material_ids_json: Mapped[str] = mapped_column(Text, default="[]")
    prompt_template: Mapped[str] = mapped_column(Text, default="")
    output_format: Mapped[str] = mapped_column(Text, default="")
    current_content: Mapped[str] = mapped_column(Text)
    compliance_level: Mapped[str] = mapped_column(String(32), default="unknown")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
    versions: Mapped[list["ExerciseVersion"]] = relationship(
        back_populates="exercise",
        cascade="all, delete-orphan",
        order_by="ExerciseVersion.version_no",
    )


class ExerciseVersion(Base):
    __tablename__ = "exercise_versions"
    __table_args__ = (
        UniqueConstraint("exercise_id", "version_no", name="uq_exercise_version_no"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    exercise_id: Mapped[int] = mapped_column(ForeignKey("exercises.id"), index=True)
    version_no: Mapped[int] = mapped_column(Integer)
    content: Mapped[str] = mapped_column(Text)
    change_note: Mapped[str] = mapped_column(String(255), default="")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )
    exercise: Mapped[Exercise] = relationship(back_populates="versions")
