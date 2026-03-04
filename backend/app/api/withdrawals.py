# backend/app/api/withdrawals.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List

from app.core.db import get_db
from app.core.auth import get_current_user
from app.models import User
from app.models.joy_withdrawal import JoyWithdrawal
from app.services.telegram import notify_withdrawal_request

router = APIRouter(prefix="/withdrawals", tags=["withdrawals"])


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
    # 수량 검증
    if data.amount <= 0:
        raise HTTPException(400, "출금 수량은 1 이상이어야 합니다.")

    if data.amount > int(user.total_joy or 0):
        raise HTTPException(400, f"보유 JOY({int(user.total_joy or 0):,})가 부족합니다.")

    if not data.wallet_address or len(data.wallet_address.strip()) < 6:
        raise HTTPException(400, "유효한 지갑 주소를 입력해주세요.")

    valid_chains = ["Polygon", "Ethereum", "TRON"]
    if data.chain not in valid_chains:
        raise HTTPException(400, f"지원하지 않는 체인입니다. ({', '.join(valid_chains)})")

    # JOY 차감
    user.total_joy = int(user.total_joy or 0) - data.amount

    # 출금 요청 생성
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
