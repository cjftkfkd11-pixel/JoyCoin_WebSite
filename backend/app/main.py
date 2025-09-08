# backend/app/main.py
import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.core.db import Base, engine, get_db
from app.api.auth import router as auth_router
from app.api.deposits import router as deposits_router
from app.api.admin_deposits import router as admin_deposits_router

# ✅ 추가 import
from sqlalchemy.orm import Session
from app.core.config import settings
from app.core.security import hash_password
from app.models.user import User

from app.api.admin_users import router as admin_users_router

app = FastAPI(title="JoyCoin Website API")

origins = [o.strip() for o in os.getenv("CORS_ORIGINS", "http://localhost:3000").split(",")]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],     # ✅ 모든 메서드 허용
    allow_headers=["*"],     # ✅ 모든 헤더 허용
)

static_dir = "app/static"
os.makedirs(static_dir, exist_ok=True)
app.mount("/static", StaticFiles(directory=static_dir), name="static")


@app.on_event("startup")
def on_startup():
    Base.metadata.create_all(bind=engine)
    seed_super_admin()


def seed_super_admin():
    """환경변수 기반 슈퍼관리자 1명 자동 생성"""
    if not settings.SUPER_ADMIN_EMAIL or not settings.SUPER_ADMIN_PASSWORD:
        return
    db: Session
    with next(get_db()) as db:
        exists = db.query(User).filter(User.email == settings.SUPER_ADMIN_EMAIL).first()
        if exists:
            # 이미 있으면 role만 보정
            if exists.role != "admin":
                exists.role = "admin"
                db.commit()
            return
        # 없으면 새로 생성
        admin = User(
            email=settings.SUPER_ADMIN_EMAIL,
            password_hash=hash_password(settings.SUPER_ADMIN_PASSWORD),
            role="admin",
            is_email_verified=True,  # 관리자는 기본 인증 처리
        )
        db.add(admin)
        db.commit()


@app.get("/healthz")
def healthz():
    return {"status": "ok"}


app.include_router(auth_router)
app.include_router(deposits_router)
app.include_router(admin_deposits_router)
app.include_router(admin_users_router)
