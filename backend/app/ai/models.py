from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class AIProviderConfig(Base):
    __tablename__ = "ai_provider_configs"
    __table_args__ = (
        UniqueConstraint("role", name="uq_ai_provider_config_role"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    role: Mapped[str] = mapped_column(String(32), index=True)
    base_url: Mapped[str] = mapped_column(String(1024), default="")
    api_key: Mapped[str] = mapped_column(Text, default="")
    model: Mapped[str] = mapped_column(String(255), default="")
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        onupdate=utc_now,
    )
