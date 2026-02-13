# backend/app/main.py
import os
import logging
from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from starlette.requests import Request
from starlette.responses import JSONResponse

from app.core.db import Base, engine, get_db
from app.api.auth import router as auth_router
from app.api.deposits import router as deposits_router
from app.api.admin_deposits import router as admin_deposits_router
from app.api.admin_users import router as admin_users_router
from app.api.admin_settings import router as admin_settings_router
from app.api.admin_sectors import router as admin_sectors_router
from app.api.sector_dashboard import router as sector_dashboard_router
from app.api.centers import router as centers_router
from app.api.products import router as products_router
from app.api.notifications import router as notifications_router

from sqlalchemy.orm import Session
from sqlalchemy import inspect, text
from app.core.config import settings
from app.core.security import hash_password
from app.core.enums import UserRole

# 새로운 모델 import
from app.models import (
    User, Center, Sector, Referral, Product, Purchase,
    DepositRequest, Point, ExchangeRate, Notification
)
from app.models.user import generate_recovery_code

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="JoyCoin Website API")

origins = [o.strip() for o in os.getenv("CORS_ORIGINS", "http://localhost:3000").split(",")]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)


def _cors_headers(request: Request) -> dict:
    return {
        "Access-Control-Allow-Origin": request.headers.get("origin") or (origins[0] if origins else "*"),
        "Access-Control-Allow-Credentials": "true",
        "Access-Control-Allow-Methods": "*",
        "Access-Control-Allow-Headers": "*",
    }


@app.exception_handler(HTTPException)
def http_exception_with_cors(request: Request, exc: HTTPException):
    """HTTPException 응답에도 CORS 헤더 보장 (브라우저에서 400/422 등 메시지 확인 가능)."""
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
        headers=_cors_headers(request),
    )


@app.exception_handler(Exception)
def add_cors_on_exception(request: Request, exc: Exception):
    """500 등 예외 시에도 CORS 헤더를 붙여 브라우저가 CORS 에러 대신 실제 에러를 보이게 함."""
    logger.exception("Unhandled exception: %s", exc)
    return JSONResponse(
        status_code=500,
        content={"detail": str(exc) or "Internal Server Error"},
        headers=_cors_headers(request),
    )

static_dir = "app/static"
os.makedirs(static_dir, exist_ok=True)
app.mount("/static", StaticFiles(directory=static_dir), name="static")


@app.on_event("startup")
def on_startup():
    logger.info("Creating tables...")
    Base.metadata.create_all(bind=engine)
    ensure_schema_compatibility()

    logger.info("Seeding super admin...")
    seed_super_admin()

    logger.info("Seeding initial data...")
    seed_initial_data()

    logger.info("Generating recovery codes for existing users...")
    generate_recovery_codes()

    # 지갑 모니터링 백그라운드 스레드 시작 (Polygon/Ethereum/TRON)
    has_evm = settings.USDT_ADMIN_ADDRESS and settings.POLYGONSCAN_API_KEY
    has_tron = settings.USDT_ADMIN_ADDRESS_TRON
    if has_evm or has_tron:
        import threading
        from app.services.wallet_monitor import wallet_monitor_loop
        chains = []
        if has_evm:
            chains.extend(["Polygon", "Ethereum"])
        if has_tron:
            chains.append("TRON")
        monitor_thread = threading.Thread(target=wallet_monitor_loop, daemon=True)
        monitor_thread.start()
        logger.info(f"Wallet monitor started for: {', '.join(chains)}")
    else:
        logger.warning("Wallet monitor NOT started - no chain addresses configured")

    logger.info("Application startup complete.")


def ensure_schema_compatibility():
    """
    Lightweight schema backfill for environments that start with an existing DB
    but no migration runner. Only adds missing columns in a safe, additive way.
    """
    inspector = inspect(engine)
    tables = set(inspector.get_table_names())

    if "users" in tables:
        user_columns = {col["name"] for col in inspector.get_columns("users")}
        if "wallet_address" not in user_columns:
            with engine.begin() as conn:
                conn.execute(text("ALTER TABLE users ADD COLUMN wallet_address VARCHAR(128)"))
            logger.info("Added users.wallet_address column")


def seed_super_admin():
    """환경변수 기반 슈퍼관리자 1명 자동 생성"""
    if not settings.SUPER_ADMIN_EMAIL or not settings.SUPER_ADMIN_PASSWORD:
        return

    with next(get_db()) as db:
        exists = db.query(User).filter(User.email == settings.SUPER_ADMIN_EMAIL).first()
        if exists:
            if exists.role != UserRole.ADMIN.value:
                exists.role = UserRole.ADMIN.value
                db.commit()
            return

        admin = User(
            email=settings.SUPER_ADMIN_EMAIL,
            password_hash=hash_password(settings.SUPER_ADMIN_PASSWORD),
            username="SuperAdmin",
            role=UserRole.ADMIN.value,
            is_email_verified=True,
        )
        db.add(admin)
        db.commit()
        logger.info(f"Super admin created: {settings.SUPER_ADMIN_EMAIL}")


def seed_initial_data():
    """초기 센터, 상품, 환율 데이터 생성"""
    with next(get_db()) as db:
        # 1. 센터 생성
        if db.query(Center).count() == 0:
            centers = [
                Center(name="서울센터", region="서울"),
                Center(name="부산센터", region="부산"),
                Center(name="대구센터", region="대구"),
            ]
            db.add_all(centers)
            db.commit()
            logger.info("- Created 3 centers")

        # 2. 섹터 생성
        if db.query(Sector).count() == 0:
            sectors = [
                Sector(name="A", fee_percent=5),
                Sector(name="B", fee_percent=5),
                Sector(name="C", fee_percent=5),
                Sector(name="D", fee_percent=5),
                Sector(name="E", fee_percent=5),
            ]
            db.add_all(sectors)
            db.commit()
            logger.info("- Created 5 sectors (A-E)")

        # 3. 상품 생성
        if db.query(Product).count() == 0:
            products = [
                Product(
                    name="JOY 1000개 패키지",
                    joy_amount=1000,
                    price_usdt=200.00,
                    price_krw=260000,
                    sort_order=1
                ),
                Product(
                    name="JOY 2000개 패키지",
                    joy_amount=2000,
                    price_usdt=380.00,
                    price_krw=494000,
                    discount_rate=5,
                    sort_order=2
                ),
                Product(
                    name="JOY 5000개 패키지",
                    joy_amount=5000,
                    price_usdt=900.00,
                    price_krw=1170000,
                    discount_rate=10,
                    sort_order=3
                ),
            ]
            db.add_all(products)
            db.commit()
            logger.info("- Created 3 products")

        # 4. 환율 생성
        if db.query(ExchangeRate).count() == 0:
            rate = ExchangeRate(
                joy_to_krw=260.0,
                usdt_to_krw=1300.0,
                is_active=True
            )
            db.add(rate)
            db.commit()
            logger.info("- Created 1 exchange rate")


def generate_recovery_codes():
    """기존 사용자에게 복구 코드가 없으면 생성"""
    with next(get_db()) as db:
        users_without_code = db.query(User).filter(User.recovery_code == None).all()
        if users_without_code:
            for user in users_without_code:
                user.recovery_code = generate_recovery_code()
            db.commit()
            logger.info(f"- Generated recovery codes for {len(users_without_code)} users")


@app.get("/healthz")
def healthz():
    return {"status": "ok"}


@app.get("/exchange-rate", tags=["exchange"])
def get_exchange_rate(db: Session = Depends(get_db)):
    """현재 JOY/USDT 환율 조회 (공개)"""
    rate = db.query(ExchangeRate).filter(ExchangeRate.is_active == True).first()
    if not rate:
        return {"joy_per_usdt": 5.0, "joy_to_krw": 260.0, "usdt_to_krw": 1300.0}
    return {
        "joy_per_usdt": float(rate.joy_per_usdt),
        "joy_to_krw": float(rate.joy_to_krw),
        "usdt_to_krw": float(rate.usdt_to_krw),
    }


@app.get("/sectors", tags=["sectors"])
def get_sectors_public(db: Session = Depends(get_db)):
    """회원가입 시 섹터 선택용 공개 API"""
    sectors = db.query(Sector).order_by(Sector.name).all()
    return [{"id": s.id, "name": s.name} for s in sectors]


# Routers
app.include_router(auth_router)
app.include_router(deposits_router)
app.include_router(admin_deposits_router)
app.include_router(admin_users_router)
app.include_router(admin_settings_router)
app.include_router(admin_sectors_router)
app.include_router(sector_dashboard_router)
app.include_router(centers_router)
app.include_router(products_router)
app.include_router(notifications_router)
