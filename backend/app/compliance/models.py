from datetime import datetime, timezone

from sqlalchemy import DateTime, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class ComplianceRule(Base):
    __tablename__ = "compliance_rules"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    category: Mapped[str] = mapped_column(String(64))
    label: Mapped[str] = mapped_column(String(128))
    pattern: Mapped[str] = mapped_column(String(255))
    risk_level: Mapped[str] = mapped_column(String(32))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )


class ComplianceLog(Base):
    __tablename__ = "compliance_logs"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    content_type: Mapped[str] = mapped_column(String(64))
    content_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    risk_level: Mapped[str] = mapped_column(String(32))
    matched_terms: Mapped[str] = mapped_column(Text, default="[]")
    suggestions: Mapped[str] = mapped_column(Text, default="[]")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )
