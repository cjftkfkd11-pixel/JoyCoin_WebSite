# backend/app/api/auth.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.core.db import get_db
from app.core.security import hash_password, verify_password, create_access_token
from app.schemas.auth import SignupIn, LoginIn, Tokens
from app.models import User, Center, Referral, Point
from app.core.config import settings

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/signup")
def signup(data: SignupIn, db: Session = Depends(get_db)):
    # 1. 이메일 중복 체크
    if db.query(User).filter(User.email == data.email).first():
        raise HTTPException(status_code=400, detail="이미 사용 중인 이메일입니다")

    # 2. 추천인 코드 확인 (있다면)
    referrer = None
    if data.referral_code:
        referrer = db.query(User).filter(User.referral_code == data.referral_code).first()
        if not referrer:
            raise HTTPException(status_code=400, detail="유효하지 않은 추천인 코드입니다")

    # 3. 센터 확인 (있다면)
    if data.center_id:
        center = db.query(Center).filter(Center.id == data.center_id).first()
        if not center:
            raise HTTPException(status_code=400, detail="유효하지 않은 센터입니다")

    # 4. 사용자 생성 (이메일 인증 없음 → 가입 즉시 인증 완료 처리)
    user = User(
        email=data.email,
        password_hash=hash_password(data.password),
        username=data.username,
        referred_by=referrer.id if referrer else None,
        center_id=data.center_id if data.center_id else None,
        role="user",
        is_email_verified=True,
    )
    db.add(user)
    db.flush()  # ID 생성

    # 5. 추천인 관계 기록 (Referrals 테이블)
    if referrer:
        referral = Referral(
            referrer_id=referrer.id,
            referred_id=user.id,
            reward_points=100  # 추천 보상 100포인트
        )
        db.add(referral)

        # 6. 추천인에게 보상 포인트 지급
        referrer_current_balance = db.query(func.coalesce(func.sum(Point.amount), 0)).filter(
            Point.user_id == referrer.id
        ).scalar()

        referrer_point = Point(
            user_id=referrer.id,
            amount=100,
            balance_after=referrer_current_balance + 100,
            type="referral_bonus",
            description=f"{user.username}님 추천 보너스"
        )
        db.add(referrer_point)

    db.commit()

    return {
        "message": "회원가입 성공",
        "user_id": user.id,
        "referral_code": user.referral_code  # 내 추천인 코드 반환
    }


@router.post("/login", response_model=Tokens)
def login(data: LoginIn, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == data.email).first()
    if not user or not verify_password(data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="이메일 또는 비밀번호가 올바르지 않습니다.",
        )

    access = create_access_token(
        user_id=user.id,
        minutes=settings.JWT_EXPIRE_MIN,
        secret=settings.JWT_SECRET,
    )
    return Tokens(access=access)
