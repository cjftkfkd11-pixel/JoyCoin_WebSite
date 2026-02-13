# backend/app/services/deposits.py
from sqlalchemy.orm import Session
from decimal import Decimal

from app.models import User, DepositRequest, ExchangeRate
from app.core.config import settings
from app.services.telegram import notify_new_deposit_request


def _get_address_for_chain(chain: str) -> str:
    """체인에 맞는 입금 주소 반환"""
    if chain == "TRON":
        addr = settings.USDT_ADMIN_ADDRESS_TRON
        if not addr:
            raise ValueError("USDT_ADMIN_ADDRESS_TRON is not configured")
        return addr
    else:  # Polygon, Ethereum (EVM 공용)
        addr = settings.USDT_ADMIN_ADDRESS
        if not addr:
            raise ValueError("USDT_ADMIN_ADDRESS is not configured")
        return addr


def create_deposit_request(db: Session, user: User, data):
    assigned_address = _get_address_for_chain(data.chain)

    # USDT 금액
    amt = Decimal(str(data.amount_usdt))

    # DB에서 현재 환율 조회 (관리자가 설정)
    rate = db.query(ExchangeRate).filter(ExchangeRate.is_active == True).first()
    joy_per_usdt = float(rate.joy_per_usdt) if rate else 5.0
    joy_amount = int(float(amt) * joy_per_usdt)

    req = DepositRequest(
        user_id=user.id,
        chain=data.chain,
        expected_amount=float(amt),
        joy_amount=joy_amount,
        assigned_address=assigned_address,
        sender_name=user.username,
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
            joy_amount=joy_amount,
            chain=data.chain,
            deposit_id=req.id,
            wallet_address=user.wallet_address,
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
