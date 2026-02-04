# backend/app/models/user.py
from datetime import datetime
from sqlalchemy import String, Integer, DateTime, Boolean, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship, validates
from app.core.db import Base
from app.core.enums import UserRole
import secrets
import string
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.models.center import Center
    from app.models.purchase import Purchase
    from app.models.deposit_request import DepositRequest
    from app.models.point import Point
    from app.models.referral import Referral


def generate_referral_code() -> str:
    """
    추천인 코드 자동 생성
    형식: JOY + 5자리 영숫자 대문자
    예시: JOY7K2M9, JOYA3X5T
    """
    chars = string.ascii_uppercase + string.digits
    random_part = ''.join(secrets.choice(chars) for _ in range(5))
    return f"JOY{random_part}"


class User(Base):
    __tablename__ = "users"

    # 기본 정보
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    username: Mapped[str] = mapped_column(String(100), nullable=False)
    
    # 추천인 시스템
    referral_code: Mapped[str] = mapped_column(
        String(20), 
        unique=True, 
        index=True, 
        nullable=False,
        default=generate_referral_code  # 자동 생성
    )
    referred_by: Mapped[int | None] = mapped_column(
        Integer, 
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )
    
    # 센터 (선택사항)
    center_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("centers.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )
    
    # 권한 및 상태
    role: Mapped[str] = mapped_column(String(16), default=UserRole.USER.value, nullable=False)
    is_email_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_banned: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # 잔액
    total_joy: Mapped[int] = mapped_column(Integer, default=0, nullable=False)  # 누적 JOY
    total_points: Mapped[int] = mapped_column(Integer, default=0, nullable=False)  # 포인트 잔액

    # 추천 보상 관련
    referral_reward_remaining: Mapped[int] = mapped_column(Integer, default=0, nullable=False)  # 남은 추천 보상 횟수
    
    # 타임스탬프
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        server_default=func.now(),
        nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False
    )
    
    # Relationships
    # 나를 추천한 사람 (역참조)
    referrer: Mapped["User"] = relationship(
        "User",
        remote_side=[id],
        foreign_keys=[referred_by],
        backref="referred_users"  # 역: 내가 추천한 사람들 목록
    )
    
    # 내 센터
    center: Mapped["Center"] = relationship("Center", back_populates="users")
    
    # 내 구매 내역
    purchases: Mapped[list["Purchase"]] = relationship("Purchase", back_populates="user")
    
    # 내 입금 요청
    deposit_requests: Mapped[list["DepositRequest"]] = relationship(
        "DepositRequest",
        foreign_keys="[DepositRequest.user_id]",
        back_populates="user"
    )
    
    # 내 포인트 내역
    point_history: Mapped[list["Point"]] = relationship("Point", back_populates="user")
    
    # 추천인으로서의 내역 (내가 추천한 사람들)
    referrals_as_referrer: Mapped[list["Referral"]] = relationship(
        "Referral",
        foreign_keys="[Referral.referrer_id]",
        back_populates="referrer"
    )
    
    # 추천받은 사람으로서의 내역
    referrals_as_referred: Mapped[list["Referral"]] = relationship(
        "Referral",
        foreign_keys="[Referral.referred_id]",
        back_populates="referred"
    )

    @validates('role')
    def validate_role(self, key, value):
        """C4: Role 값이 유효한지 검증"""
        valid_roles = [r.value for r in UserRole]
        if value not in valid_roles:
            raise ValueError(f"유효하지 않은 role 값입니다: {value}. 허용값: {valid_roles}")
        return value

    def __repr__(self):
        return f"<User(id={self.id}, email={self.email}, referral_code={self.referral_code})>"
