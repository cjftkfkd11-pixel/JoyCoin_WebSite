# backend/app/api/admin_deposits.py
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, List

from sqlalchemy.orm import joinedload

from sqlalchemy import func as sqlfunc

from app.core.db import get_db
from app.core.auth import get_current_admin
from app.models import DepositRequest, User, Point, ExchangeRate
from app.schemas.deposits import DepositRequestOut, AdminDepositRequestOut
from app.services.telegram import notify_deposit_approved

router = APIRouter(prefix="/admin/deposits", tags=["admin:deposits"])


# ---------- In Schemas ----------
class ApproveIn(BaseModel):
    actual_amount: Optional[float] = None
    admin_notes: Optional[str] = None


class RejectIn(BaseModel):
    admin_notes: Optional[str] = None


# ---------- List ----------
@router.get("", response_model=List[AdminDepositRequestOut])
def list_deposits(
    status: Optional[str] = Query(None, description="pending|approved|rejected"),
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    q = db.query(DepositRequest).options(joinedload(DepositRequest.user)).order_by(DepositRequest.created_at.desc())
    if status:
        q = q.filter(DepositRequest.status == status)
    return q.limit(200).all()


# ---------- Approve (상태 변경 + 유저 잔액 충전) ----------
@router.post("/{deposit_id}/approve", response_model=DepositRequestOut)
def approve_deposit(
    deposit_id: int,
    payload: ApproveIn,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    # 1. 입금 요청 존재 확인
    dr = db.query(DepositRequest).filter(DepositRequest.id == deposit_id).first()
    if not dr:
        raise HTTPException(404, "입금 요청(deposit_request)을 찾을 수 없습니다.")

    # 2. 이미 승인된 경우 중복 처리 방지
    if dr.status == "approved":
        return dr

    # 3. 대기 중인 상태인지 확인
    if dr.status != "pending":
        raise HTTPException(400, f"처리할 수 없는 상태입니다: {dr.status}")

    # 4. 입금 요청 정보 업데이트
    dr.actual_amount = payload.actual_amount if payload.actual_amount else dr.expected_amount
    dr.admin_notes = payload.admin_notes
    dr.admin_id = admin.id
    dr.status = "approved"
    dr.approved_at = datetime.utcnow()

    # 5. [중요] 유저 total_joy에 구매한 JOY 수량 추가
    user = db.query(User).filter(User.id == dr.user_id).first()
    if not user:
        raise HTTPException(404, "해당 입금을 신청한 유저를 찾을 수 없습니다.")
    user.total_joy = int(user.total_joy or 0) + int(dr.joy_amount or 0)

    # 6. 추천 보상: 남은 횟수가 있으면 결제 USDT의 N%를 포인트로 적립
    remaining = int(user.referral_reward_remaining or 0)
    if remaining > 0:
        # DB에서 추천 보너스 퍼센트 조회 (관리자 설정)
        rate = db.query(ExchangeRate).filter(ExchangeRate.is_active == True).first()
        bonus_pct = rate.referral_bonus_percent if rate else 10
        usdt_amount = float(dr.actual_amount or dr.expected_amount or 0)
        bonus_points = int(usdt_amount * bonus_pct / 100)
        if bonus_points > 0:
            # 현재 포인트 잔액 조회
            current_balance = db.query(
                sqlfunc.coalesce(sqlfunc.sum(Point.amount), 0)
            ).filter(Point.user_id == user.id).scalar()

            point_record = Point(
                user_id=user.id,
                amount=bonus_points,
                balance_after=int(current_balance) + bonus_points,
                type="referral_bonus",
                description=f"추천 보상 ({usdt_amount} USDT의 {bonus_pct}%)"
            )
            db.add(point_record)
            user.total_points = int(user.total_points or 0) + bonus_points
            user.referral_reward_remaining = remaining - 1

    db.commit()
    db.refresh(dr)

    # 텔레그램 알림 전송
    try:
        notify_deposit_approved(
            user_email=user.email,
            amount=dr.actual_amount,
            joy_amount=dr.joy_amount,
            deposit_id=dr.id
        )
    except Exception as e:
        print(f"텔레그램 알림 실패 (무시): {e}")

    return dr


# ---------- Reject ----------
@router.post("/{deposit_id}/reject", response_model=DepositRequestOut)
def reject_deposit(
    deposit_id: int,
    payload: RejectIn | None = None,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    dr = db.query(DepositRequest).filter(DepositRequest.id == deposit_id).first()
    if not dr:
        raise HTTPException(404, "입금 요청을 찾을 수 없습니다.")

    if dr.status == "approved":
        raise HTTPException(400, "이미 승인된 요청은 거절할 수 없습니다.")

    if dr.status == "rejected":
        return dr

    dr.status = "rejected"
    dr.admin_id = admin.id
    if payload and payload.admin_notes:
        dr.admin_notes = payload.admin_notes

    db.commit()
    db.refresh(dr)
    return dr


# ---------- 통계 ----------
@router.get("/stats")
def get_deposit_stats(
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    total_users = db.query(sqlfunc.count(User.id)).scalar()
    total_deposits = db.query(sqlfunc.count(DepositRequest.id)).scalar()
    total_approved_usdt = db.query(
        sqlfunc.coalesce(sqlfunc.sum(DepositRequest.actual_amount), 0)
    ).filter(DepositRequest.status == "approved").scalar()
    total_approved_joy = db.query(
        sqlfunc.coalesce(sqlfunc.sum(DepositRequest.joy_amount), 0)
    ).filter(DepositRequest.status == "approved").scalar()
    pending_count = db.query(sqlfunc.count(DepositRequest.id)).filter(DepositRequest.status == "pending").scalar()
    approved_count = db.query(sqlfunc.count(DepositRequest.id)).filter(DepositRequest.status == "approved").scalar()
    rejected_count = db.query(sqlfunc.count(DepositRequest.id)).filter(DepositRequest.status == "rejected").scalar()

    # 섹터별 통계
    sector_stats = db.query(
        User.sector_id,
        sqlfunc.count(DepositRequest.id).label("deposit_count"),
        sqlfunc.coalesce(sqlfunc.sum(DepositRequest.actual_amount), 0).label("total_usdt"),
    ).join(DepositRequest, DepositRequest.user_id == User.id).filter(
        DepositRequest.status == "approved"
    ).group_by(User.sector_id).all()

    return {
        "total_users": total_users,
        "total_deposits": total_deposits,
        "total_approved_usdt": float(total_approved_usdt),
        "total_approved_joy": int(total_approved_joy),
        "pending_count": pending_count,
        "approved_count": approved_count,
        "rejected_count": rejected_count,
        "sector_stats": [
            {"sector_id": s.sector_id, "deposit_count": s.deposit_count, "total_usdt": float(s.total_usdt)}
            for s in sector_stats
        ],
    }