# backend/app/models/sector.py
from datetime import datetime
from sqlalchemy import String, Integer, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.db import Base


class Sector(Base):
    __tablename__ = "sectors"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)  # A, B, C, D, E (관리자가 변경 가능)
    fee_percent: Mapped[int] = mapped_column(Integer, default=5, nullable=False)  # 5, 10, 15, 20

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )

    # Relationships
    managers: Mapped[list["User"]] = relationship(
        "User",
        foreign_keys="[User.sector_id]",
        back_populates="sector"
    )

    def __repr__(self):
        return f"<Sector(id={self.id}, name={self.name}, fee={self.fee_percent}%)>"
