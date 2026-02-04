from fastapi import APIRouter, Depends, HTTPException, status, Response, Request
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.core.db import get_db
from app.core.security import hash_password, verify_password, create_access_token
from app.schemas.auth import SignupIn, LoginIn, Tokens
from app.models import User, Center, Referral, Point
from app.core.config import settings
from jose import jwt, JWTError # 토큰 해독을 위해 필요

router = APIRouter(prefix="/auth", tags=["auth"])

# [추가] 쿠키에서 유저를 찾아내는 함수 (Dependency)
async def get_current_user(request: Request, db: Session = Depends(get_db)):
    # 프론트에서 보낸 'accessToken' 쿠키를 가져옵니다.
    token = request.cookies.get("accessToken")
    if not token:
        raise HTTPException(status_code=401, detail="인증 쿠키가 없습니다.")
    
    try:
        # 토큰 해독
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=["HS256"])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise HTTPException(status_code=401, detail="유효하지 않은 토큰입니다.")
    except JWTError:
        raise HTTPException(status_code=401, detail="인증 세션이 만료되었습니다.")
    
    user = db.query(User).filter(User.id == int(user_id)).first()
    if user is None:
        raise HTTPException(status_code=401, detail="사용자를 찾을 수 없습니다.")
    return user

# ---------------------------------------------------------
# 1. 회원가입 (기존 유지)
# ---------------------------------------------------------
@router.post("/signup")
def signup(data: SignupIn, db: Session = Depends(get_db)):
    if db.query(User).filter(User.email == data.email).first():
        raise HTTPException(status_code=400, detail="이미 사용 중인 이메일입니다")

    referrer = None
    if data.referral_code:
        referrer = db.query(User).filter(User.referral_code == data.referral_code).first()
        if not referrer:
            raise HTTPException(status_code=400, detail="유효하지 않은 추천인 코드입니다")
        if referrer.email == data.email:
            raise HTTPException(status_code=400, detail="자신을 추천인으로 지정할 수 없습니다")

    if data.center_id:
        center = db.query(Center).filter(Center.id == data.center_id).first()
        if not center:
            raise HTTPException(status_code=400, detail="유효하지 않은 센터입니다")

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
    db.flush()

    if referrer:
        referral = Referral(
            referrer_id=referrer.id,
            referred_id=user.id,
            reward_points=100
        )
        db.add(referral)
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
    return {"message": "회원가입 성공", "user_id": user.id, "referral_code": user.referral_code}

# ---------------------------------------------------------
# 2. 로그인 (기존 유지 + 쿠키 설정)
# ---------------------------------------------------------
@router.post("/login", response_model=Tokens)
def login(data: LoginIn, response: Response, db: Session = Depends(get_db)):
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

    response.set_cookie(
        key="accessToken",
        value=access,
        httponly=True,
        secure=False, # 로컬 테스트 환경이므로 False로 고정 (중요!)
        samesite="lax",
        max_age=settings.JWT_EXPIRE_MIN * 60,
        path="/"
    )

    return Tokens(access=access)

# ---------------------------------------------------------
# 3. [신규 추가] 내 정보 조회 (/auth/me)
# ---------------------------------------------------------
@router.get("/me")
async def get_me(current_user: User = Depends(get_current_user)):
    """
    현재 로그인된 유저의 정보를 반환합니다. 
    마이페이지 404 에러와 인증 세션 만료를 해결합니다.
    """
    return {
        "id": current_user.id,
        "email": current_user.email,
        "username": current_user.username,
        "balance": getattr(current_user, "balance", 0), # balance 필드가 모델에 있다면 가져옴
        "role": current_user.role
    }