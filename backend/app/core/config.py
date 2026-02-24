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

    # 체인별 USDT 입금 주소
    USDT_ADMIN_ADDRESS: str | None = None          # Polygon/Ethereum (EVM 공용)
    USDT_ADMIN_ADDRESS_TRON: str | None = None      # TRON (TRC-20)

    # 이미 쓰고 있는 슈퍼관리자
    SUPER_ADMIN_EMAIL: str | None = None
    SUPER_ADMIN_PASSWORD: str | None = None

    # 쿠키 보안 (프로덕션 HTTPS 환경에서 True로 설정)
    COOKIE_SECURE: bool = False

    # 텔레그램 봇 설정
    TELEGRAM_BOT_TOKEN: str | None = None
    TELEGRAM_CHAT_ID: str | None = None

    # 블록체인 API 키
    POLYGONSCAN_API_KEY: str | None = None         # Etherscan V2 (Polygon + Ethereum)
    TRONGRID_API_KEY: str | None = None            # TronGrid (TRON)
    WALLET_POLL_INTERVAL_SECONDS: int = 60


settings = Settings()
