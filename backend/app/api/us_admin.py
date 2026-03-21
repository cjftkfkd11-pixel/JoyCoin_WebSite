# backend/app/api/us_admin.py
from datetime import datetime
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func as sqlfunc
from pydantic import BaseModel

from app.core.db import get_db
from app.core.auth import get_current_us_admin, get_current_admin
from app.models import User, DepositRequest, UsdtWithdrawal, ExchangeRate
from app.services.telegram import notify_usdt_withdrawal_request


def _get_display_ratio(db: Session) -> float:
    """관리자가 설정한 USDT 표시 비율 (0.0 ~ 1.0), 기본 0.5"""
    rate = db.query(ExchangeRate).filter(ExchangeRate.is_active == True).first()
    pct = rate.usdt_display_percent if rate else 50
    return pct / 100.0

router = APIRouter(prefix="/us-admin", tags=["us-admin"])


# ── 공통 통계 (슈퍼어드민 + 미국어드민 공유) ──
@router.get("/stats")
def get_usdt_stats(
    db: Session = Depends(get_db),
    admin=Depends(get_current_us_admin),
):
    """총 USDT 수령액, 확정 출금액, 잔여 USDT"""
    ratio = _get_display_ratio(db)

    total_received_actual = float(db.query(
        sqlfunc.coalesce(sqlfunc.sum(DepositRequest.actual_amount), 0)
    ).filter(DepositRequest.status == "approved").scalar())

    total_withdrawn = float(db.query(
        sqlfunc.coalesce(sqlfunc.sum(UsdtWithdrawal.amount), 0)
    ).filter(UsdtWithdrawal.status == "confirmed").scalar())

    pending_withdrawal = float(db.query(
        sqlfunc.coalesce(sqlfunc.sum(UsdtWithdrawal.amount), 0)
    ).filter(UsdtWithdrawal.status == "pending").scalar())

    displayed_received = total_received_actual * ratio

    return {
        "total_received_usdt": displayed_received,
        "total_withdrawn_usdt": total_withdrawn,
        "pending_withdrawal_usdt": pending_withdrawal,
        "available_usdt": displayed_received - total_withdrawn - pending_withdrawal,
    }


# ── 미국어드민: USDT 출금 신청 ──
class WithdrawIn(BaseModel):
    amount: float
    note: Optional[str] = None


@router.post("/withdraw-request")
def request_usdt_withdrawal(
    data: WithdrawIn,
    db: Session = Depends(get_db),
    admin=Depends(get_current_us_admin),
):
    if data.amount <= 0:
        raise HTTPException(400, "출금 금액은 0보다 커야 합니다.")

    # 현재 가용 USDT 계산 (관리자 설정 비율만 가용)
    ratio = _get_display_ratio(db)

    total_received_actual = float(db.query(
        sqlfunc.coalesce(sqlfunc.sum(DepositRequest.actual_amount), 0)
    ).filter(DepositRequest.status == "approved").scalar())

    total_withdrawn = float(db.query(
        sqlfunc.coalesce(sqlfunc.sum(UsdtWithdrawal.amount), 0)
    ).filter(UsdtWithdrawal.status == "confirmed").scalar())

    pending = float(db.query(
        sqlfunc.coalesce(sqlfunc.sum(UsdtWithdrawal.amount), 0)
    ).filter(UsdtWithdrawal.status == "pending").scalar())

    available = total_received_actual * ratio - total_withdrawn - pending

    if data.amount > available:
        raise HTTPException(400, f"가용 USDT({available:.2f})가 부족합니다.")

    withdrawal = UsdtWithdrawal(
        requested_by=admin.id,
        amount=data.amount,
        note=data.note,
        status="pending",
    )
    db.add(withdrawal)
    db.commit()
    db.refresh(withdrawal)

    try:
        notify_usdt_withdrawal_request(
            requester_email=admin.email,
            amount=data.amount,
            note=data.note,
            withdrawal_id=withdrawal.id,
            total_usdt=total_received_actual,
        )
    except Exception as e:
        print(f"텔레그램 알림 실패 (무시): {e}")

    return {"id": withdrawal.id, "amount": withdrawal.amount, "status": withdrawal.status}


# ── 미국어드민: 출금 신청 내역 조회 ──
@router.get("/withdraw-requests")
def list_withdrawal_requests(
    db: Session = Depends(get_db),
    admin=Depends(get_current_us_admin),
):
    items = db.query(UsdtWithdrawal).order_by(UsdtWithdrawal.created_at.desc()).limit(100).all()
    return [
        {
            "id": w.id,
            "amount": float(w.amount),
            "note": w.note,
            "status": w.status,
            "admin_notes": w.admin_notes,
            "requester_email": w.requester.email if w.requester else None,
            "created_at": w.created_at.isoformat(),
            "confirmed_at": w.confirmed_at.isoformat() if w.confirmed_at else None,
        }
        for w in items
    ]


# ── 슈퍼어드민: 출금 확정 / 거절 ──
class ConfirmIn(BaseModel):
    admin_notes: Optional[str] = None


@router.post("/withdraw-requests/{withdrawal_id}/confirm")
def confirm_withdrawal(
    withdrawal_id: int,
    payload: ConfirmIn,
    db: Session = Depends(get_db),
    admin=Depends(get_current_admin),  # 슈퍼어드민만
):
    w = db.query(UsdtWithdrawal).filter(UsdtWithdrawal.id == withdrawal_id).first()
    if not w:
        raise HTTPException(404, "출금 요청을 찾을 수 없습니다.")
    if w.status != "pending":
        raise HTTPException(400, f"처리할 수 없는 상태입니다: {w.status}")

    w.status = "confirmed"
    w.confirmed_by = admin.id
    w.confirmed_at = datetime.utcnow()
    w.admin_notes = payload.admin_notes
    db.commit()
    return {"id": w.id, "status": w.status}


@router.post("/withdraw-requests/{withdrawal_id}/reject")
def reject_withdrawal(
    withdrawal_id: int,
    payload: ConfirmIn,
    db: Session = Depends(get_db),
    admin=Depends(get_current_admin),  # 슈퍼어드민만
):
    w = db.query(UsdtWithdrawal).filter(UsdtWithdrawal.id == withdrawal_id).first()
    if not w:
        raise HTTPException(404, "출금 요청을 찾을 수 없습니다.")
    if w.status != "pending":
        raise HTTPException(400, f"처리할 수 없는 상태입니다: {w.status}")

    w.status = "rejected"
    w.confirmed_by = admin.id
    w.confirmed_at = datetime.utcnow()
    w.admin_notes = payload.admin_notes
    db.commit()
    return {"id": w.id, "status": w.status}
