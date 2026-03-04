# backend/app/api/admin_withdrawals.py
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, joinedload
from pydantic import BaseModel
from typing import Optional, List

from app.core.db import get_db
from app.core.auth import get_current_admin
from app.models import User
from app.models.joy_withdrawal import JoyWithdrawal
from app.services.telegram import notify_withdrawal_approved

router = APIRouter(prefix="/admin/withdrawals", tags=["admin:withdrawals"])


class WithdrawalAdminOut(BaseModel):
    id: int
    amount: int
    wallet_address: str
    chain: str
    status: str
    admin_notes: str | None = None
    created_at: str
    processed_at: str | None = None
    user: dict

    class Config:
        from_attributes = True


class ApproveIn(BaseModel):
    admin_notes: Optional[str] = None


class RejectIn(BaseModel):
    admin_notes: Optional[str] = None


def _to_out(w: JoyWithdrawal) -> WithdrawalAdminOut:
    return WithdrawalAdminOut(
        id=w.id,
        amount=w.amount,
        wallet_address=w.wallet_address,
        chain=w.chain,
        status=w.status,
        admin_notes=w.admin_notes,
        created_at=w.created_at.isoformat(),
        processed_at=w.processed_at.isoformat() if w.processed_at else None,
        user={"id": w.user.id, "email": w.user.email, "username": w.user.username} if w.user else {},
    )


@router.get("", response_model=List[WithdrawalAdminOut])
def list_withdrawals(
    status: Optional[str] = Query(None, description="pending|approved|rejected"),
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    q = (
        db.query(JoyWithdrawal)
        .options(joinedload(JoyWithdrawal.user))
        .order_by(JoyWithdrawal.created_at.desc())
    )
    if status:
        q = q.filter(JoyWithdrawal.status == status)
    return [_to_out(w) for w in q.limit(200).all()]


@router.post("/{withdrawal_id}/approve", response_model=WithdrawalAdminOut)
def approve_withdrawal(
    withdrawal_id: int,
    payload: ApproveIn,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    w = db.query(JoyWithdrawal).options(joinedload(JoyWithdrawal.user)).filter(JoyWithdrawal.id == withdrawal_id).first()
    if not w:
        raise HTTPException(404, "출금 요청을 찾을 수 없습니다.")
    if w.status == "approved":
        return _to_out(w)
    if w.status != "pending":
        raise HTTPException(400, f"처리할 수 없는 상태입니다: {w.status}")

    w.status = "approved"
    w.admin_id = admin.id
    w.admin_notes = payload.admin_notes
    w.processed_at = datetime.utcnow()
    db.commit()
    db.refresh(w)

    # 텔레그램 알림
    try:
        notify_withdrawal_approved(
            user_email=w.user.email if w.user else "unknown",
            amount=w.amount,
            wallet_address=w.wallet_address,
            chain=w.chain,
            withdrawal_id=w.id,
        )
    except Exception as e:
        print(f"텔레그램 알림 실패 (무시): {e}")

    return _to_out(w)


@router.post("/{withdrawal_id}/reject", response_model=WithdrawalAdminOut)
def reject_withdrawal(
    withdrawal_id: int,
    payload: RejectIn,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    w = db.query(JoyWithdrawal).options(joinedload(JoyWithdrawal.user)).filter(JoyWithdrawal.id == withdrawal_id).first()
    if not w:
        raise HTTPException(404, "출금 요청을 찾을 수 없습니다.")
    if w.status == "rejected":
        return _to_out(w)
    if w.status != "pending":
        raise HTTPException(400, f"처리할 수 없는 상태입니다: {w.status}")

    # 거절 시 JOY 복구
    user = db.query(User).filter(User.id == w.user_id).first()
    if user:
        user.total_joy = int(user.total_joy or 0) + w.amount

    w.status = "rejected"
    w.admin_id = admin.id
    w.admin_notes = payload.admin_notes
    w.processed_at = datetime.utcnow()
    db.commit()
    db.refresh(w)

    return _to_out(w)
