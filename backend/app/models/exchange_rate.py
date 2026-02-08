# backend/app/models/exchange_rate.py
from datetime import datetime
from sqlalchemy import Integer, DateTime, Numeric, Boolean, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.db import Base


class ExchangeRate(Base):
    __tablename__ = "exchange_rates"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    
    # JOY/KRW 환율 (1 JOY = ? KRW)
    joy_to_krw: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    
    # USDT/KRW 환율 (1 USDT = ? KRW)
    usdt_to_krw: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    
    # 1 USDT = ? JOY (관리자 조정 가능, 나중에 거래소 상장 시 실시간으로 전환)
    joy_per_usdt: Mapped[float] = mapped_column(Numeric(10, 2), default=5.0, nullable=False)

    # 추천인 보너스 포인트
    referral_bonus_points: Mapped[int] = mapped_column(Integer, default=100, nullable=False)

    # 현재 활성화된 환율인지
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    
    # 등록한 관리자
    updated_by: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True
    )
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )
    
    # Relationships
    admin: Mapped["User"] = relationship("User", backref="exchange_rate_updates")

    def __repr__(self):
        return f"<ExchangeRate(id={self.id}, joy_to_krw={self.joy_to_krw}, usdt_to_krw={self.usdt_to_krw})>"
