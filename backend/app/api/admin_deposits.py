# backend/app/api/admin_deposits.py
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, List

from sqlalchemy.orm import joinedload

from sqlalchemy import func as sqlfunc

from app.core.db import get_db
from app.core.auth import get_current_admin, get_current_any_admin
from app.models import DepositRequest, User, Point, ExchangeRate, Notification
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
    admin: User = Depends(get_current_any_admin),  # 슈퍼어드민 + 미국어드민 조회 가능
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
    already_credited = dr.joy_credited

    dr.actual_amount = payload.actual_amount if payload.actual_amount else (dr.actual_amount or dr.expected_amount)
    dr.admin_notes = payload.admin_notes
    dr.admin_id = admin.id
    dr.status = "approved"
    dr.approved_at = datetime.utcnow()
    dr.joy_credited = True

    # 5. [중요] actual_amount 기준으로 JOY 재계산 (부족 입금 대응)
    user = db.query(User).filter(User.id == dr.user_id).first()
    if not user:
        raise HTTPException(404, "해당 입금을 신청한 유저를 찾을 수 없습니다.")

    # 소수점 식별자 제거 후 정수 기준 JOY 계산
    actual = float(dr.actual_amount or dr.expected_amount)
    expected_base = int(float(dr.expected_amount))
    actual_base = int(actual)

    if actual_base < expected_base:
        # 부족 입금 → actual 기준으로 JOY 재계산
        rate = db.query(ExchangeRate).filter(ExchangeRate.is_active == True).first()
        joy_per_usdt = float(rate.joy_per_usdt) if rate else 5.0
        dr.joy_amount = int(actual_base * joy_per_usdt)

    # 이미 wallet_monitor가 자동 지급했으면 중복 지급 방지
    if not already_credited:
        user.total_joy = int(user.total_joy or 0) + int(dr.joy_amount or 0)

    # 6. 추천 보상: 구매자의 추천인(referred_by)에게 포인트 지급 (횟수 제한 없음)
    if user.referred_by:
        referrer = db.query(User).filter(User.id == user.referred_by).first()
        if referrer:
            rate_obj = db.query(ExchangeRate).filter(ExchangeRate.is_active == True).first()
            bonus_pct = rate_obj.referral_bonus_percent if rate_obj else 10
            usdt_amount = float(dr.actual_amount or dr.expected_amount or 0)
            bonus_points = int(usdt_amount * bonus_pct / 100)
            if bonus_points > 0:
                current_balance = db.query(
                    sqlfunc.coalesce(sqlfunc.sum(Point.amount), 0)
                ).filter(Point.user_id == referrer.id).scalar()

                point_record = Point(
                    user_id=referrer.id,
                    amount=bonus_points,
                    balance_after=int(current_balance) + bonus_points,
                    type="referral_bonus",
                    description=f"추천 보상: {user.email} 구매 ({usdt_amount} USDT의 {bonus_pct}%)"
                )
                db.add(point_record)
                referrer.total_points = int(referrer.total_points or 0) + bonus_points

    # 사용자 알림 생성 (승인)
    import json
    notif = Notification(
        user_id=user.id,
        title="deposit_approved",
        message=json.dumps({"amount": int(dr.actual_amount or dr.expected_amount), "joy": int(dr.joy_amount or 0)}),
        type="deposit_approved",
        is_read=False,
    )
    db.add(notif)
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
    reason = payload.admin_notes if payload and payload.admin_notes else "사유 없음"
    dr.admin_notes = reason

    # 사용자 알림 생성 (거절)
    import json
    notif = Notification(
        user_id=dr.user_id,
        title="deposit_rejected",
        message=json.dumps({"amount": float(dr.expected_amount), "reason": reason}),
        type="deposit_rejected",
        is_read=False,
    )
    db.add(notif)
    db.commit()
    db.refresh(dr)
    return dr


# ---------- 통계 ----------
@router.get("/stats")
def get_deposit_stats(
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_any_admin),
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