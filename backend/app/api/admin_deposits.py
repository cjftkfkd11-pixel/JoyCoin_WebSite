# backend/app/api/admin_deposits.py
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, List

from app.core.db import get_db
from app.core.auth import get_current_admin
from app.models.deposit_request import DepositRequest
from app.schemas.deposits import DepositRequestOut

router = APIRouter(prefix="/admin/deposits", tags=["admin:deposits"])


# ---------- In Schemas ----------
class ConfirmIn(BaseModel):
    tx_hash: Optional[str] = None
    from_address: Optional[str] = None
    detected_amount: Optional[float] = None  # 없으면 expected_amount로 대체


class RejectIn(BaseModel):
    reason: Optional[str] = None


class MarkCreditedIn(BaseModel):
    joy_tx_hash: Optional[str] = None  # 컬럼 없으면 저장은 생략(주석 참고)


# ---------- List ----------
@router.get("", response_model=List[DepositRequestOut])
def list_deposits(
    status: Optional[str] = Query(
        None, description="pending|confirmed|credited|rejected|review_required"
    ),
    db: Session = Depends(get_db),
    admin=Depends(get_current_admin),
):
    q = db.query(DepositRequest).order_by(DepositRequest.created_at.desc())
    if status:
        q = q.filter(DepositRequest.status == status)
    return q.limit(200).all()


# ---------- Confirm ----------
@router.post("/{deposit_id}/confirm", response_model=DepositRequestOut)
def confirm_deposit(
    deposit_id: int,
    payload: ConfirmIn,
    db: Session = Depends(get_db),
    admin=Depends(get_current_admin),
):
    dr = db.query(DepositRequest).filter(DepositRequest.id == deposit_id).first()
    if not dr:
        raise HTTPException(404, "deposit_request not found")

    # idempotent
    if dr.status in ("confirmed", "credited", "rejected"):
        return dr

    if dr.status not in ("pending", "review_required"):
        raise HTTPException(400, f"invalid state: {dr.status}")

    # 실제 값이 오면 적용, 아니면 expected_amount로 대체
    dr.tx_hash = payload.tx_hash or dr.tx_hash
    dr.from_address = payload.from_address or dr.from_address
    dr.detected_amount = (
        payload.detected_amount
        if payload.detected_amount is not None
        else dr.expected_amount
    )

    dr.status = "confirmed"
    dr.confirmed_at = datetime.utcnow()

    db.commit()
    db.refresh(dr)
    return dr


# ---------- Move to Review Queue ----------
@router.post("/{deposit_id}/review", response_model=DepositRequestOut)
def move_to_review_queue(
    deposit_id: int,
    db: Session = Depends(get_db),
    admin=Depends(get_current_admin),
):
    dr = db.query(DepositRequest).filter(DepositRequest.id == deposit_id).first()
    if not dr:
        raise HTTPException(404, "deposit_request not found")

    if dr.status == "review_required":
        return dr

    # 이미 최종상태면 리턴
    if dr.status in ("credited", "rejected"):
        return dr

    dr.status = "review_required"
    db.commit()
    db.refresh(dr)
    return dr


# ---------- Mark Credited (JOY 송금 완료 표시) ----------
@router.post("/{deposit_id}/mark-credited", response_model=DepositRequestOut)
def mark_credited(
    deposit_id: int,
    payload: MarkCreditedIn | None = None,
    db: Session = Depends(get_db),
    admin=Depends(get_current_admin),
):
    dr = db.query(DepositRequest).filter(DepositRequest.id == deposit_id).first()
    if not dr:
        raise HTTPException(404, "deposit_request not found")

    if dr.status != "confirmed":
        raise HTTPException(400, f"invalid state: {dr.status}")

    # TODO: ourcoin_tx_hash 컬럼 만들면 여기에 payload.joy_tx_hash 저장 가능
    dr.status = "credited"
    db.commit()
    db.refresh(dr)
    return dr


# ---------- Reject ----------
@router.post("/{deposit_id}/reject", response_model=DepositRequestOut)
def reject_deposit(
    deposit_id: int,
    payload: RejectIn | None = None,
    db: Session = Depends(get_db),
    admin=Depends(get_current_admin),
):
    dr = db.query(DepositRequest).filter(DepositRequest.id == deposit_id).first()
    if not dr:
        raise HTTPException(404, "deposit_request not found")

    if dr.status == "credited":
        raise HTTPException(400, "already credited")

    if dr.status == "rejected":
        return dr

    dr.status = "rejected"
    db.commit()
    db.refresh(dr)
    return dr
