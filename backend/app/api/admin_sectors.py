# backend/app/api/admin_sectors.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List

from app.core.db import get_db
from app.core.auth import get_current_admin
from app.models import User, Sector

router = APIRouter(prefix="/admin/sectors", tags=["admin:sectors"])


# ---------- Schemas ----------
class SectorOut(BaseModel):
    id: int
    name: str
    fee_percent: int

    model_config = dict(from_attributes=True)


class SectorFeeUpdate(BaseModel):
    fee_percent: int  # 5, 10, 15, 20


class SectorUpdateIn(BaseModel):
    name: str
    manager_email: str | None = None  # 매니저 이메일 변경 (선택)


class SectorManagerAssign(BaseModel):
    user_id: int
    sector_id: int


# ---------- 섹터 목록 (매니저 이메일 포함) ----------
@router.get("")
def list_sectors(
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    sectors = db.query(Sector).order_by(Sector.id).all()
    result = []
    for s in sectors:
        manager = db.query(User).filter(
            User.sector_id == s.id, User.role == "sector_manager"
        ).first()
        result.append({
            "id": s.id,
            "name": s.name,
            "fee_percent": s.fee_percent,
            "manager_email": manager.email if manager else None,
            "manager_id": manager.id if manager else None,
        })
    return result


# ---------- 섹터 Fee 변경 ----------
@router.put("/{sector_id}/fee", response_model=SectorOut)
def update_sector_fee(
    sector_id: int,
    payload: SectorFeeUpdate,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    if payload.fee_percent not in (0, 10, 20, 30, 40, 50):
        raise HTTPException(400, "fee_percent는 0, 10, 20, 30, 40, 50 중 하나여야 합니다.")

    sector = db.query(Sector).filter(Sector.id == sector_id).first()
    if not sector:
        raise HTTPException(404, "섹터를 찾을 수 없습니다.")

    sector.fee_percent = payload.fee_percent
    db.commit()
    db.refresh(sector)
    return sector


# ---------- 섹터 이름 + 매니저 이메일 변경 ----------
@router.put("/{sector_id}/update")
def update_sector(
    sector_id: int,
    payload: SectorUpdateIn,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    sector = db.query(Sector).filter(Sector.id == sector_id).first()
    if not sector:
        raise HTTPException(404, "섹터를 찾을 수 없습니다.")

    new_name = payload.name.strip()
    if not new_name:
        raise HTTPException(400, "섹터 이름을 입력해주세요.")
    if len(new_name) > 50:
        raise HTTPException(400, "섹터 이름은 50자 이내여야 합니다.")

    # 이름 중복 체크 (자기 자신 제외)
    dup = db.query(Sector).filter(Sector.name == new_name, Sector.id != sector_id).first()
    if dup:
        raise HTTPException(400, f"'{new_name}' 이름은 이미 사용 중입니다.")

    sector.name = new_name

    # 매니저 이메일 변경
    if payload.manager_email is not None:
        new_email = payload.manager_email.strip()
        if new_email:
            manager = db.query(User).filter(
                User.sector_id == sector_id, User.role == "sector_manager"
            ).first()
            if not manager:
                raise HTTPException(404, "이 섹터에 배정된 매니저가 없습니다.")
            # 이메일 중복 체크
            email_dup = db.query(User).filter(User.email == new_email, User.id != manager.id).first()
            if email_dup:
                raise HTTPException(400, f"'{new_email}' 이메일은 이미 사용 중입니다.")
            manager.email = new_email

    db.commit()
    db.refresh(sector)
    return {"id": sector.id, "name": sector.name, "message": "섹터가 업데이트되었습니다."}


# ---------- 섹터 매니저 배정 ----------
@router.post("/assign-manager")
def assign_sector_manager(
    payload: SectorManagerAssign,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    user = db.query(User).filter(User.id == payload.user_id).first()
    if not user:
        raise HTTPException(404, "유저를 찾을 수 없습니다.")

    sector = db.query(Sector).filter(Sector.id == payload.sector_id).first()
    if not sector:
        raise HTTPException(404, "섹터를 찾을 수 없습니다.")

    user.role = "sector_manager"
    user.sector_id = payload.sector_id
    db.commit()
    return {"message": f"{user.email}님이 섹터 {sector.name} 매니저로 배정되었습니다."}
