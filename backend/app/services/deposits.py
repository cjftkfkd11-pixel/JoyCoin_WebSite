# backend/app/services/deposits.py
import random
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


def _generate_unique_decimal(db: Session, base_amount: float, chain: str) -> float:
    """
    고유 소수점 금액 생성.
    같은 체인의 pending 요청에서 사용 중인 소수점을 피해 0.01~0.99 중 하나 선택.
    예: base_amount=200 → 200.37
    """
    # 현재 같은 체인의 pending 요청에서 사용 중인 소수점 목록 조회
    pending_amounts = db.query(DepositRequest.expected_amount).filter(
        DepositRequest.chain == chain,
        DepositRequest.status == "pending",
    ).all()

    used_decimals = set()
    for (amt,) in pending_amounts:
        frac = round(float(amt) % 1, 2)
        if frac > 0:
            used_decimals.add(frac)

    # 0.01 ~ 0.99 중 미사용 선택
    available = [round(i / 100, 2) for i in range(1, 100) if round(i / 100, 2) not in used_decimals]

    if not available:
        # 극히 드문 케이스: 99개 모두 사용 중 → 0.001~0.009 추가 범위
        available = [round(i / 1000, 3) for i in range(1, 10)]

    decimal_part = random.choice(available)
    return round(base_amount + decimal_part, 2)


def create_deposit_request(db: Session, user: User, data):
    assigned_address = _get_address_for_chain(data.chain)

    # USDT 금액 (base)
    base_amt = float(data.amount_usdt)

    # DB에서 현재 환율 조회 (관리자가 설정)
    rate = db.query(ExchangeRate).filter(ExchangeRate.is_active == True).first()
    joy_per_usdt = float(rate.joy_per_usdt) if rate else 5.0

    # JOY는 원래 base 금액 기준으로 계산 (소수점 식별자 제외)
    joy_amount = int(base_amt * joy_per_usdt)

    # 고유 소수점 금액 생성 (200 → 200.37)
    unique_amount = _generate_unique_decimal(db, base_amt, data.chain)

    req = DepositRequest(
        user_id=user.id,
        chain=data.chain,
        expected_amount=unique_amount,
        joy_amount=joy_amount,
        assigned_address=assigned_address,
        sender_name=user.username,
        status="pending",
        joy_credited=True,
    )
    db.add(req)

    # JOY 즉시 선지급 (USDT 입금 확인 전 선충전)
    user.total_joy = int(user.total_joy or 0) + joy_amount

    db.commit()
    db.refresh(req)

    # 텔레그램 알림 전송
    try:
        notify_new_deposit_request(
            user_email=user.email,
            amount=unique_amount,
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
