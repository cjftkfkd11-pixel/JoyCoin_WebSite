# backend/app/services/deposits.py
from sqlalchemy.orm import Session
from decimal import Decimal

from app.models import User, DepositRequest
from app.core.config import settings
from app.services.telegram import notify_new_deposit_request


def create_deposit_request(db: Session, user: User, data):
    if not settings.USDT_ADMIN_ADDRESS:
        raise ValueError("USDT_ADMIN_ADDRESS is not configured")

    # USDT 금액
    amt = Decimal(str(data.amount_usdt))

    req = DepositRequest(
        user_id=user.id,
        chain=data.chain,
        expected_amount=float(amt),
        assigned_address=settings.USDT_ADMIN_ADDRESS,
        status="pending",
    )
    db.add(req)
    db.commit()
    db.refresh(req)

    # 텔레그램 알림 전송 (비동기적으로 실패해도 입금 요청은 생성됨)
    try:
        notify_new_deposit_request(
            user_email=user.email,
            amount=float(amt),
            chain=data.chain,
            deposit_id=req.id
        )
    except Exception as e:
        print(f"텔레그램 알림 실패 (무시): {e}")

    return req


def get_user_deposits(db: Session, user: User):
    return (
        db.query(DepositRequest)
        .filter(DepositRequest.user_id == user.id)
        .order_by(DepositRequest.id.desc())
        .all()
    )
