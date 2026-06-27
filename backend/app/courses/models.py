from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class Course(Base):
    __tablename__ = "courses"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    title: Mapped[str] = mapped_column(String(255))
    subject: Mapped[str] = mapped_column(String(128))
    exam_type: Mapped[str] = mapped_column(String(128))
    description: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(32), default="draft", index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        onupdate=utc_now,
    )
    chapters: Mapped[list["Chapter"]] = relationship(
        back_populates="course",
        cascade="all, delete-orphan",
        order_by="(Chapter.order_index, Chapter.id)",
    )
    knowledge_points: Mapped[list["KnowledgePoint"]] = relationship(
        back_populates="course",
        cascade="all, delete-orphan",
        order_by="KnowledgePoint.id",
    )
    material_links: Mapped[list["CourseMaterialLink"]] = relationship(
        back_populates="course",
        cascade="all, delete-orphan",
        order_by="CourseMaterialLink.id",
    )


class Chapter(Base):
    __tablename__ = "chapters"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    course_id: Mapped[int] = mapped_column(ForeignKey("courses.id"), index=True)
    title: Mapped[str] = mapped_column(String(255))
    summary: Mapped[str] = mapped_column(Text, default="")
    order_index: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        onupdate=utc_now,
    )
    course: Mapped[Course] = relationship(back_populates="chapters")
    sessions: Mapped[list["LessonSession"]] = relationship(
        back_populates="chapter",
        cascade="all, delete-orphan",
        order_by="(LessonSession.order_index, LessonSession.id)",
    )
    knowledge_points: Mapped[list["KnowledgePoint"]] = relationship(
        back_populates="chapter",
    )


class LessonSession(Base):
    __tablename__ = "lesson_sessions"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    course_id: Mapped[int] = mapped_column(ForeignKey("courses.id"), index=True)
    chapter_id: Mapped[int] = mapped_column(ForeignKey("chapters.id"), index=True)
    title: Mapped[str] = mapped_column(String(255))
    duration_minutes: Mapped[int] = mapped_column(Integer)
    teaching_goal: Mapped[str] = mapped_column(Text, default="")
    order_index: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        onupdate=utc_now,
    )
    chapter: Mapped[Chapter] = relationship(back_populates="sessions")
    lesson_links: Mapped[list["SessionLessonLink"]] = relationship(
        back_populates="session",
        cascade="all, delete-orphan",
        order_by="SessionLessonLink.id",
    )
    knowledge_points: Mapped[list["KnowledgePoint"]] = relationship(
        back_populates="session",
    )


class KnowledgePoint(Base):
    __tablename__ = "knowledge_points"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    course_id: Mapped[int] = mapped_column(ForeignKey("courses.id"), index=True)
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
    name: Mapped[str] = mapped_column(String(255))
    description: Mapped[str] = mapped_column(Text, default="")
    difficulty: Mapped[str] = mapped_column(String(64), default="")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        onupdate=utc_now,
    )
    course: Mapped[Course] = relationship(back_populates="knowledge_points")
    chapter: Mapped[Chapter | None] = relationship(back_populates="knowledge_points")
    session: Mapped[LessonSession | None] = relationship(back_populates="knowledge_points")


class CourseMaterialLink(Base):
    __tablename__ = "course_material_links"
    __table_args__ = (
        UniqueConstraint("course_id", "material_id", name="uq_course_material_link"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    course_id: Mapped[int] = mapped_column(ForeignKey("courses.id"), index=True)
    material_id: Mapped[int] = mapped_column(ForeignKey("materials.id"), index=True)
    usage_note: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
    )
    course: Mapped[Course] = relationship(back_populates="material_links")


class SessionLessonLink(Base):
    __tablename__ = "session_lesson_links"
    __table_args__ = (
        UniqueConstraint("session_id", "lesson_id", name="uq_session_lesson_link"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    session_id: Mapped[int] = mapped_column(ForeignKey("lesson_sessions.id"), index=True)
    lesson_id: Mapped[int] = mapped_column(ForeignKey("lessons.id"), index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
    )
    session: Mapped[LessonSession] = relationship(back_populates="lesson_links")
