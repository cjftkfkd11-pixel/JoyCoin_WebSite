# backend/app/models/joy_withdrawal.py
from datetime import datetime
from sqlalchemy import String, Integer, DateTime, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.db import Base


class JoyWithdrawal(Base):
    __tablename__ = "joy_withdrawals"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    # 신청자
    user_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # 출금 JOY 수량
    amount: Mapped[int] = mapped_column(Integer, nullable=False)

    # 수령 지갑 주소
    wallet_address: Mapped[str] = mapped_column(String(255), nullable=False)

    # 체인
    chain: Mapped[str] = mapped_column(String(20), nullable=False)

    # 상태: pending / approved / rejected
    status: Mapped[str] = mapped_column(String(20), default="pending", nullable=False, index=True)

    # 처리한 관리자
    admin_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    # 관리자 메모
    admin_notes: Mapped[str | None] = mapped_column(String(500), nullable=True)

    # 처리 시각
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    # Relationships
    user: Mapped["User"] = relationship("User", foreign_keys=[user_id])

    def __repr__(self):
        return f"<JoyWithdrawal(id={self.id}, user_id={self.user_id}, amount={self.amount}, status={self.status})>"
