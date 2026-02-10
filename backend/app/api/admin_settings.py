# backend/app/api/admin_settings.py
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.auth import get_current_admin
from app.core.config import settings
from app.core.db import get_db
from app.models import User, ExchangeRate

router = APIRouter(prefix="/admin/settings", tags=["admin:settings"])


class SettingsResponse(BaseModel):
    usdt_address: str
    telegram_enabled: bool
    referral_bonus_percent: int
    joy_per_usdt: float


@router.get("", response_model=SettingsResponse)
def get_settings(
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    rate = db.query(ExchangeRate).filter(ExchangeRate.is_active == True).first()
    return SettingsResponse(
        usdt_address=settings.USDT_ADMIN_ADDRESS or "설정되지 않음",
        telegram_enabled=bool(settings.TELEGRAM_BOT_TOKEN and settings.TELEGRAM_CHAT_ID),
        referral_bonus_percent=rate.referral_bonus_percent if rate else 10,
        joy_per_usdt=float(rate.joy_per_usdt) if rate else 5.0,
    )


class ReferralBonusUpdate(BaseModel):
    referral_bonus_percent: int


@router.put("/referral-bonus")
def update_referral_bonus(
    data: ReferralBonusUpdate,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    if data.referral_bonus_percent < 0 or data.referral_bonus_percent > 100:
        raise HTTPException(400, "퍼센트는 0~100 사이여야 합니다")
    rate = db.query(ExchangeRate).filter(ExchangeRate.is_active == True).first()
    if not rate:
        raise HTTPException(404, "환율 설정을 찾을 수 없습니다")
    rate.referral_bonus_percent = data.referral_bonus_percent
    db.commit()
    return {"ok": True, "referral_bonus_percent": rate.referral_bonus_percent}


class ExchangeRateUpdate(BaseModel):
    joy_per_usdt: float


@router.put("/exchange-rate")
def update_exchange_rate(
    data: ExchangeRateUpdate,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    if data.joy_per_usdt <= 0:
        raise HTTPException(400, "환율은 0보다 커야 합니다")
    rate = db.query(ExchangeRate).filter(ExchangeRate.is_active == True).first()
    if not rate:
        raise HTTPException(404, "환율 설정을 찾을 수 없습니다")
    rate.joy_per_usdt = data.joy_per_usdt
    # KRW 환율 자동 계산 (1 JOY = ? KRW)
    usdt_to_krw = float(rate.usdt_to_krw) or 1300.0
    rate.joy_to_krw = round(usdt_to_krw / data.joy_per_usdt, 2)
    db.commit()
    return {
        "ok": True,
        "joy_per_usdt": float(rate.joy_per_usdt),
        "joy_to_krw": float(rate.joy_to_krw),
    }
