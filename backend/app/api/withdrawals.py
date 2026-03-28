# backend/app/api/withdrawals.py
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from pydantic import BaseModel
from typing import List

from app.core.db import get_db
from app.core.auth import get_current_user
from app.models import User
from app.models.joy_withdrawal import JoyWithdrawal
from app.services.telegram import notify_withdrawal_request

router = APIRouter(prefix="/withdrawals", tags=["withdrawals"])

# ──────────────────────────────────────────────
# 수령(Claim) 제한 설정
# ──────────────────────────────────────────────
CLAIM_MIN_AMOUNT = 200          # 최소 수령 수량 (JOY)
CLAIM_OPEN_HOUR = 10            # 수령 가능 시작 시간 (KST)
CLAIM_CLOSE_HOUR = 17           # 수령 가능 종료 시간 (KST)
CLAIM_MAX_PER_DAY = 1           # 하루 최대 수령 신청 횟수

# KST 타임존 (UTC+9)
KST = timezone(timedelta(hours=9))


class WithdrawalIn(BaseModel):
    amount: int
    wallet_address: str
    chain: str


class WithdrawalOut(BaseModel):
    id: int
    amount: int
    wallet_address: str
    chain: str
    status: str
    admin_notes: str | None = None
    created_at: str

    class Config:
        from_attributes = True


@router.post("/request", response_model=WithdrawalOut)
def request_withdrawal(
    data: WithdrawalIn,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    # ── 운영시간 검증 (KST 10:00 ~ 17:00) ──
    now_kst = datetime.now(KST)
    if now_kst.hour < CLAIM_OPEN_HOUR or now_kst.hour >= CLAIM_CLOSE_HOUR:
        raise HTTPException(
            400,
            f"수령 가능 시간은 {CLAIM_OPEN_HOUR}:00 ~ {CLAIM_CLOSE_HOUR}:00 (KST)입니다. "
            f"현재 시간: {now_kst.strftime('%H:%M')} KST"
        )

    # ── 최소 수령 수량 검증 ──
    if data.amount < CLAIM_MIN_AMOUNT:
        raise HTTPException(400, f"최소 수령 수량은 {CLAIM_MIN_AMOUNT:,} JOY입니다.")

    # ── 하루 1번 제한 검증 ──
    today_start_kst = now_kst.replace(hour=0, minute=0, second=0, microsecond=0)
    today_start_utc = today_start_kst.astimezone(timezone.utc).replace(tzinfo=None)

    today_count = db.query(func.count(JoyWithdrawal.id)).filter(
        JoyWithdrawal.user_id == user.id,
        JoyWithdrawal.created_at >= today_start_utc,
    ).scalar()

    if today_count >= CLAIM_MAX_PER_DAY:
        raise HTTPException(400, "오늘은 이미 수령 신청을 하셨습니다. 내일 다시 신청해주세요.")

    # ── 수량 검증 ──
    if data.amount > int(user.total_joy or 0):
        raise HTTPException(400, f"보유 JOY({int(user.total_joy or 0):,})가 부족합니다.")

    if not data.wallet_address or len(data.wallet_address.strip()) < 6:
        raise HTTPException(400, "유효한 지갑 주소를 입력해주세요.")

    valid_chains = ["Solana"]
    if data.chain not in valid_chains:
        raise HTTPException(400, f"지원하지 않는 체인입니다. ({', '.join(valid_chains)})")

    # JOY 차감
    user.total_joy = int(user.total_joy or 0) - data.amount

    # 수령 요청 생성
    withdrawal = JoyWithdrawal(
        user_id=user.id,
        amount=data.amount,
        wallet_address=data.wallet_address.strip(),
        chain=data.chain,
        status="pending",
    )
    db.add(withdrawal)
    db.commit()
    db.refresh(withdrawal)

    # 텔레그램 알림
    try:
        notify_withdrawal_request(
            user_email=user.email,
            amount=data.amount,
            wallet_address=data.wallet_address.strip(),
            chain=data.chain,
            withdrawal_id=withdrawal.id,
        )
    except Exception as e:
        print(f"텔레그램 알림 실패 (무시): {e}")

    return WithdrawalOut(
        id=withdrawal.id,
        amount=withdrawal.amount,
        wallet_address=withdrawal.wallet_address,
        chain=withdrawal.chain,
        status=withdrawal.status,
        admin_notes=withdrawal.admin_notes,
        created_at=withdrawal.created_at.isoformat(),
    )


# ── 수령 가능 상태 조회 API (프론트에서 사용) ──
@router.get("/claim-status")
def get_claim_status(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """현재 수령 가능 여부를 반환 (운영시간, 오늘 신청 횟수)"""
    now_kst = datetime.now(KST)
    is_open = CLAIM_OPEN_HOUR <= now_kst.hour < CLAIM_CLOSE_HOUR

    today_start_kst = now_kst.replace(hour=0, minute=0, second=0, microsecond=0)
    today_start_utc = today_start_kst.astimezone(timezone.utc).replace(tzinfo=None)

    today_count = db.query(func.count(JoyWithdrawal.id)).filter(
        JoyWithdrawal.user_id == user.id,
        JoyWithdrawal.created_at >= today_start_utc,
    ).scalar()

    return {
        "is_open": is_open,
        "current_time_kst": now_kst.strftime("%H:%M"),
        "open_hour": CLAIM_OPEN_HOUR,
        "close_hour": CLAIM_CLOSE_HOUR,
        "today_count": today_count,
        "max_per_day": CLAIM_MAX_PER_DAY,
        "can_claim": is_open and today_count < CLAIM_MAX_PER_DAY,
        "min_amount": CLAIM_MIN_AMOUNT,
    }


@router.get("/my", response_model=List[WithdrawalOut])
def my_withdrawals(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    items = (
        db.query(JoyWithdrawal)
        .filter(JoyWithdrawal.user_id == user.id)
        .order_by(JoyWithdrawal.id.desc())
        .all()
    )
    return [
        WithdrawalOut(
            id=w.id,
            amount=w.amount,
            wallet_address=w.wallet_address,
            chain=w.chain,
            status=w.status,
            admin_notes=w.admin_notes,
            created_at=w.created_at.isoformat(),
        )
        for w in items
    ]
