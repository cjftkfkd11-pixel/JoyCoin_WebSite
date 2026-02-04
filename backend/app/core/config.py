# backend/app/core/config.py
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    APP_ENV: str = "dev"
    DB_URL: str
    JWT_SECRET: str
    JWT_EXPIRE_MIN: int = 20
    CORS_ORIGINS: str = "http://localhost:3000"

    # ✅ 누락된 환경변수들 정의
    USDT_ADMIN_ADDRESS: str | None = None

    # 이미 쓰고 있는 슈퍼관리자
    SUPER_ADMIN_EMAIL: str | None = None
    SUPER_ADMIN_PASSWORD: str | None = None

    # 텔레그램 봇 설정
    TELEGRAM_BOT_TOKEN: str | None = None
    TELEGRAM_CHAT_ID: str | None = None


settings = Settings()
