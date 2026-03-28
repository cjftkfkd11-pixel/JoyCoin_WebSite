# backend/app/api/points.py
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from pydantic import BaseModel, Field
from typing import Optional, List

from app.core.db import get_db
from app.core.auth import get_current_user, get_current_admin
from app.models import User, Point, PointWithdrawal

router = APIRouter(prefix="/points", tags=["points"])


# ---------- Schemas ----------
class WithdrawalRequestIn(BaseModel):
    amount: int = Field(..., gt=0, description="전환할 JOY 포인트")
    # method: "joy" 고정 (JOY 코인으로 전환), 기존 bank/usdt 호환 유지
    method: str = Field(default="joy", description="전환 방식 (joy)")
    # account_info: 회원 지갑 주소 자동 사용 (프론트에서 전달)
    account_info: str = Field(default="", max_length=255, description="수령 지갑 주소")


class WithdrawalOut(BaseModel):
    id: int
    amount: int
    method: str
    account_info: str
    status: str
    admin_notes: Optional[str] = None
    processed_at: Optional[datetime] = None
    created_at: datetime

    model_config = dict(from_attributes=True)


class PointHistoryOut(BaseModel):
    id: int
    amount: int
    balance_after: int
    type: str
    description: str
    created_at: datetime

    model_config = dict(from_attributes=True)


# ---------- 내 포인트 조회 ----------
@router.get("/my")
def get_my_points(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    # 현재 포인트 잔액
    balance = db.query(func.coalesce(func.sum(Point.amount), 0)).filter(
        Point.user_id == user.id
    ).scalar()

    # 포인트 내역
    history = db.query(Point).filter(Point.user_id == user.id).order_by(Point.id.desc()).limit(50).all()

    return {
        "balance": balance,
        "history": history,
    }


# ---------- 포인트 출금 신청 ----------
@router.post("/withdraw", response_model=WithdrawalOut)
def request_withdrawal(
    data: WithdrawalRequestIn,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    # 현재 포인트 잔액 확인
    balance = db.query(func.coalesce(func.sum(Point.amount), 0)).filter(
        Point.user_id == user.id
    ).scalar()

    if data.amount > balance:
        raise HTTPException(400, f"JOY 포인트가 부족합니다. 현재: {balance}")

    # 대기 중인 전환 신청이 있는지 확인
    pending = db.query(PointWithdrawal).filter(
        PointWithdrawal.user_id == user.id,
        PointWithdrawal.status == "pending"
    ).first()
    if pending:
        raise HTTPException(400, "이미 대기 중인 전환 신청이 있습니다.")

    # 지갑 주소: 전달된 값 또는 사용자 등록 지갑
    wallet = data.account_info.strip() if data.account_info.strip() else (user.wallet_address or "")
    if not wallet or len(wallet) < 6:
        raise HTTPException(400, "유효한 지갑 주소가 없습니다. 마이페이지에서 지갑 주소를 등록해주세요.")

    # 전환 신청 생성
    withdrawal = PointWithdrawal(
        user_id=user.id,
        amount=data.amount,
        method="joy",
        account_info=wallet,
        status="pending",
    )
    db.add(withdrawal)

    # 포인트 차감 기록
    point_record = Point(
        user_id=user.id,
        amount=-data.amount,
        balance_after=balance - data.amount,
        type="withdraw_pending",
        description=f"JOY 코인 전환 신청: {data.amount} 포인트",
    )
    db.add(point_record)

    db.commit()
    db.refresh(withdrawal)
    return withdrawal


# ---------- 내 출금 내역 ----------
@router.get("/withdrawals", response_model=List[WithdrawalOut])
def get_my_withdrawals(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return db.query(PointWithdrawal).filter(
        PointWithdrawal.user_id == user.id
    ).order_by(PointWithdrawal.id.desc()).limit(50).all()


# ========== Admin APIs ==========

class AdminWithdrawalOut(BaseModel):
    id: int
    user_id: int
    user_email: str
    amount: int
    method: str
    account_info: str
    status: str
    admin_notes: Optional[str] = None
    processed_at: Optional[datetime] = None
    created_at: datetime


@router.get("/admin/withdrawals")
def admin_list_withdrawals(
    status: Optional[str] = None,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    q = db.query(PointWithdrawal).order_by(PointWithdrawal.created_at.desc())
    if status:
        q = q.filter(PointWithdrawal.status == status)

    withdrawals = q.limit(200).all()

    result = []
    for w in withdrawals:
        user = db.query(User).filter(User.id == w.user_id).first()
        result.append({
            "id": w.id,
            "user_id": w.user_id,
            "user_email": user.email if user else "unknown",
            "amount": w.amount,
            "method": w.method,
            "account_info": w.account_info,
            "status": w.status,
            "admin_notes": w.admin_notes,
            "processed_at": w.processed_at,
            "created_at": w.created_at,
        })
    return result


class ApproveWithdrawalIn(BaseModel):
    admin_notes: Optional[str] = None


@router.post("/admin/withdrawals/{withdrawal_id}/approve")
def admin_approve_withdrawal(
    withdrawal_id: int,
    payload: ApproveWithdrawalIn = None,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    w = db.query(PointWithdrawal).filter(PointWithdrawal.id == withdrawal_id).first()
    if not w:
        raise HTTPException(404, "출금 신청을 찾을 수 없습니다.")

    if w.status != "pending":
        raise HTTPException(400, f"처리할 수 없는 상태입니다: {w.status}")

    w.status = "approved"
    w.admin_id = admin.id
    w.processed_at = datetime.utcnow()
    if payload and payload.admin_notes:
        w.admin_notes = payload.admin_notes

    db.commit()
    return {"message": "출금 승인 완료", "id": w.id}


@router.post("/admin/withdrawals/{withdrawal_id}/reject")
def admin_reject_withdrawal(
    withdrawal_id: int,
    payload: ApproveWithdrawalIn = None,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    w = db.query(PointWithdrawal).filter(PointWithdrawal.id == withdrawal_id).first()
    if not w:
        raise HTTPException(404, "출금 신청을 찾을 수 없습니다.")

    if w.status != "pending":
        raise HTTPException(400, f"처리할 수 없는 상태입니다: {w.status}")

    # 포인트 환불
    user = db.query(User).filter(User.id == w.user_id).first()
    if user:
        current_balance = db.query(func.coalesce(func.sum(Point.amount), 0)).filter(
            Point.user_id == user.id
        ).scalar()

        refund_point = Point(
            user_id=user.id,
            amount=w.amount,
            balance_after=current_balance + w.amount,
            type="withdraw_refund",
            description=f"전환 거절로 인한 환불: {w.amount} JOY 포인트",
        )
        db.add(refund_point)

    w.status = "rejected"
    w.admin_id = admin.id
    w.processed_at = datetime.utcnow()
    if payload and payload.admin_notes:
        w.admin_notes = payload.admin_notes

    db.commit()
    return {"message": "출금 거절 완료 (포인트 환불됨)", "id": w.id}
