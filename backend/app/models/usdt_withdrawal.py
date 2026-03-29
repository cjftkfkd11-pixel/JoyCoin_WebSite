# backend/app/models/usdt_withdrawal.py
from datetime import datetime
from sqlalchemy import Integer, String, Numeric, DateTime, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.db import Base
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.models.user import User


class UsdtWithdrawal(Base):
    __tablename__ = "usdt_withdrawals"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    requested_by: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    amount: Mapped[float] = mapped_column(Numeric(14, 2), nullable=False)
    note: Mapped[str | None] = mapped_column(String(500), nullable=True)
    to_address: Mapped[str | None] = mapped_column(String(255), nullable=True)  # 수신 지갑주소

    # 슈퍼어드민 확정
    status: Mapped[str] = mapped_column(String(20), default="pending", nullable=False)  # pending / confirmed / rejected
    confirmed_by: Mapped[int | None] = mapped_column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    admin_notes: Mapped[str | None] = mapped_column(String(500), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    requester: Mapped["User"] = relationship("User", foreign_keys=[requested_by])
    confirmer: Mapped["User"] = relationship("User", foreign_keys=[confirmed_by])
