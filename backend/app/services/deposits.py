# backend/app/services/deposits.py
import uuid
from sqlalchemy.orm import Session
from decimal import Decimal

from app.models.user import User
from app.models.deposit_request import DepositRequest  # 파일명 맞게
from app.core.config import settings  # settings.USDT_ADMIN_ADDRESS, 등


def create_deposit_request(db: Session, user: User, data):
    if not settings.USDT_ADMIN_ADDRESS:
        # 환경변수 누락 시 명확한 에러
        raise ValueError("USDT_ADMIN_ADDRESS is not configured")

    # 고유 소수점 지문(간단 버전)
    amt = Decimal(str(data.amount_usdt))
    fingerprint = Decimal("0.000001")
    expected_amount = (amt + fingerprint).quantize(Decimal("0.000001"))

    req = DepositRequest(
        user_id=user.id,
        chain=data.chain,
        expected_amount=str(expected_amount),
        assigned_address=settings.USDT_ADMIN_ADDRESS,
        reference_code=str(uuid.uuid4())[:8],
        status="pending",
    )
    db.add(req)
    db.commit()
    db.refresh(req)
    return req


def get_user_deposits(db: Session, user: User):
    return (
        db.query(DepositRequest)
        .filter(DepositRequest.user_id == user.id)
        .order_by(DepositRequest.id.desc())
        .all()
    )


admin_addr = settings.USDT_ADMIN_ADDRESS
if not admin_addr:
    raise HTTPException(status_code=500, detail="USDT_ADMIN_ADDRESS is not configured")
