# backend/app/api/admin_users.py
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.auth import get_current_admin
from app.core.enums import UserRole
from app.models import User

router = APIRouter(prefix="/admin/users", tags=["admin:users"])


@router.get("")
def list_users(
    q: str | None = None,
    role: str | None = None,
    db: Session = Depends(get_db),
    admin=Depends(get_current_admin),
):
    qry = db.query(User)
    if q:
        qry = qry.filter(
            (User.email.ilike(f"%{q}%")) | (User.username.ilike(f"%{q}%"))
        )
    if role:
        qry = qry.filter(User.role == role)
    items = qry.order_by(User.created_at.desc()).limit(200).all()
    return {
        "items": [
            {
                "id": u.id,
                "email": u.email,
                "username": u.username,
                "role": u.role,
                "total_joy": u.total_joy or 0,
                "is_banned": u.is_banned,
                "sector_id": u.sector_id,
                "created_at": u.created_at.isoformat() if u.created_at else None,
            }
            for u in items
        ]
    }


@router.post("/{user_id}/ban")
def ban_user(
    user_id: int,
    db: Session = Depends(get_db),
    admin=Depends(get_current_admin),
):
    user = db.query(User).get(user_id)
    if not user:
        raise HTTPException(404, "user not found")
    if user.role == "admin":
        raise HTTPException(400, "관리자는 차단할 수 없습니다")
    user.is_banned = True
    db.commit()
    return {"ok": True, "message": "차단 완료", "user_id": user.id}


@router.post("/{user_id}/unban")
def unban_user(
    user_id: int,
    db: Session = Depends(get_db),
    admin=Depends(get_current_admin),
):
    user = db.query(User).get(user_id)
    if not user:
        raise HTTPException(404, "user not found")
    user.is_banned = False
    db.commit()
    return {"ok": True, "message": "차단 해제 완료", "user_id": user.id}


@router.post("/{user_id}/promote")
def promote_user_to_admin(
    user_id: int,
    db: Session = Depends(get_db),
    admin=Depends(get_current_admin),
):
    user = db.query(User).get(user_id)
    if not user:
        raise HTTPException(404, "user not found")
    if user.role == "admin":
        return {"ok": True, "message": "already admin", "user_id": user.id}
    user.role = UserRole.ADMIN.value
    db.commit()
    return {"ok": True, "message": "관리자로 승격 완료", "user_id": user.id}


@router.post("/{user_id}/demote")
def demote_user(
    user_id: int,
    db: Session = Depends(get_db),
    admin=Depends(get_current_admin),
):
    user = db.query(User).get(user_id)
    if not user:
        raise HTTPException(404, "user not found")
    if user.id == admin.id:
        raise HTTPException(400, "자기 자신은 강등할 수 없습니다")
    user.role = UserRole.USER.value
    db.commit()
    return {"ok": True, "message": "일반 유저로 변경 완료", "user_id": user.id}


@router.post("/{user_id}/demote-sector-manager")
def demote_sector_manager(
    user_id: int,
    db: Session = Depends(get_db),
    admin=Depends(get_current_admin),
):
    """섹터 매니저를 일반 유저로 강등"""
    user = db.query(User).get(user_id)
    if not user:
        raise HTTPException(404, "user not found")
    if user.role != "sector_manager":
        raise HTTPException(400, "섹터 매니저가 아닙니다")
    user.role = UserRole.USER.value
    db.commit()
    return {"ok": True, "message": "일반 유저로 강등 완료", "user_id": user.id}
