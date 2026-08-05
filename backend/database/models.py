from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import DateTime, Float, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from .database import Base


class PacenoteFeedback(Base):
    __tablename__ = "pacenote_feedback"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    radius: Mapped[float] = mapped_column(Float, index=True)
    heading_change: Mapped[float] = mapped_column(Float)
    length: Mapped[float] = mapped_column(Float)
    original_classification: Mapped[int] = mapped_column(Integer)
    user_classification: Mapped[int] = mapped_column(Integer)
    driver_id: Mapped[str] = mapped_column(String(100), default="default", index=True)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )
