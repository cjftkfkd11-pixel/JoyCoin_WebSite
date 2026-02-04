# backend/app/api/admin_settings.py
from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.core.auth import get_current_admin
from app.core.config import settings
from app.models import User

router = APIRouter(prefix="/admin/settings", tags=["admin:settings"])


class SettingsResponse(BaseModel):
    usdt_address: str
    telegram_enabled: bool


@router.get("", response_model=SettingsResponse)
def get_settings(
    admin: User = Depends(get_current_admin),
):
    """
    현재 시스템 설정 조회 (읽기 전용)
    실제 값 변경은 .env 파일을 수정해야 합니다.
    """
    return SettingsResponse(
        usdt_address=settings.USDT_ADMIN_ADDRESS or "설정되지 않음",
        telegram_enabled=bool(settings.TELEGRAM_BOT_TOKEN and settings.TELEGRAM_CHAT_ID)
    )
