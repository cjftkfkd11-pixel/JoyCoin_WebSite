from fastapi import APIRouter, Depends, HTTPException, status, Response, Request
from sqlalchemy.orm import Session
from app.core.db import get_db
from app.core.security import hash_password, verify_password, create_access_token
from app.schemas.auth import SignupIn, LoginIn, Tokens
from app.models import User, Center, Referral, Sector, LegalConsent
from app.core.config import settings
from jose import jwt, JWTError

router = APIRouter(prefix="/auth", tags=["auth"])


def _client_ip(request: Request) -> str | None:
    forwarded_for = request.headers.get("x-forwarded-for")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    if request.client:
        return request.client.host
    return None

async def get_current_user(request: Request, db: Session = Depends(get_db)):
    token = request.cookies.get("accessToken")
    if not token:
        raise HTTPException(status_code=401, detail="인증 쿠키가 없습니다.")

    try:
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=["HS256"])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise HTTPException(status_code=401, detail="유효하지 않은 토큰입니다")
    except JWTError:
        raise HTTPException(status_code=401, detail="인증 세션이 만료되었습니다")

    user = db.query(User).filter(User.id == int(user_id)).first()
    if user is None:
        raise HTTPException(status_code=401, detail="사용자를 찾을 수 없습니다.")
    return user

# ---------------------------------------------------------
# 1. 회원가입
# ---------------------------------------------------------
@router.post("/signup")
def signup(data: SignupIn, request: Request, db: Session = Depends(get_db)):
    if db.query(User).filter(User.email == data.email).first():
        raise HTTPException(status_code=400, detail="이미 사용 중인 이메일입니다")
    if db.query(User).filter(User.username == data.username).first():
        raise HTTPException(status_code=400, detail="이미 사용 중인 닉네임입니다")
    if not (data.terms_accepted and data.risk_accepted and data.privacy_accepted):
        raise HTTPException(status_code=400, detail="Required legal agreements were not accepted.")

    referrer = None
    if data.referral_code:
        referrer = db.query(User).filter(User.referral_code == data.referral_code).first()
        if not referrer:
            raise HTTPException(status_code=400, detail="유효하지 않은 추천인 코드입니다")
        if referrer.email == data.email:
            raise HTTPException(status_code=400, detail="자신을 추천인으로 지정할 수 없습니다")
        # 1단계 추천만 허용: 추천인이 이미 누군가에 의해 추천받은 사람이면 거절
        if referrer.referred_by is not None:
            raise HTTPException(status_code=400, detail="해당 추천인은 추천 권한이 없습니다 (1단계 추천만 허용)")

    if data.center_id:
        center = db.query(Center).filter(Center.id == data.center_id).first()
        if not center:
            raise HTTPException(status_code=400, detail="유효하지 않은 센터입니다")

    if data.sector_id:
        sector = db.query(Sector).filter(Sector.id == data.sector_id).first()
        if not sector:
            raise HTTPException(status_code=400, detail="유효하지 않은 섹터입니다")

    user = User(
        email=data.email,
        password_hash=hash_password(data.password),
        username=data.username,
        wallet_address=data.wallet_address.strip(),
        referred_by=referrer.id if referrer else None,
        center_id=data.center_id if data.center_id else None,
        sector_id=data.sector_id if data.sector_id else None,
        role="user",
        is_email_verified=True,
    )
    db.add(user)
    db.flush()

    if referrer:
        referral = Referral(
            referrer_id=referrer.id,
            referred_id=user.id,
            reward_points=0
        )
        db.add(referral)
        referrer.referral_reward_remaining = int(referrer.referral_reward_remaining or 0) + 1

    consent = LegalConsent(
        user_id=user.id,
        event_type="signup",
        legal_version=data.legal_version,
        locale=data.locale,
        page_path="/auth/signup",
        terms_accepted=data.terms_accepted,
        risk_accepted=data.risk_accepted,
        privacy_accepted=data.privacy_accepted,
        ip_address=_client_ip(request),
        user_agent=request.headers.get("user-agent"),
    )
    db.add(consent)

    db.commit()
    return {"message": "회원가입 성공", "user_id": user.id, "referral_code": user.referral_code}

# ---------------------------------------------------------
# 2. 로그인
# ---------------------------------------------------------
@router.post("/login", response_model=Tokens)
def login(data: LoginIn, response: Response, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == data.email).first()
    if not user or not verify_password(data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="이메일 또는 비밀번호가 올바르지 않습니다.",
        )
    if user.is_banned:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="차단된 계정입니다. 관리자에게 문의하세요.",
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
        secure=settings.COOKIE_SECURE,
        samesite="lax",
        max_age=settings.JWT_EXPIRE_MIN * 60,
        path="/"
    )

    return Tokens(access=access)

# ---------------------------------------------------------
# 3. 내 정보 조회 (/auth/me)
# ---------------------------------------------------------
@router.get("/me")
async def get_me(current_user: User = Depends(get_current_user)):
    center_data = None
    if current_user.center:
        center_data = {
            "id": current_user.center.id,
            "name": current_user.center.name,
            "region": current_user.center.region,
        }

    return {
        "id": current_user.id,
        "email": current_user.email,
        "username": current_user.username,
        "wallet_address": current_user.wallet_address,
        "total_joy": int(current_user.total_joy or 0),
        "total_points": int(current_user.total_points or 0),
        "referral_reward_remaining": int(current_user.referral_reward_remaining or 0),
        "role": current_user.role,
        "referral_code": current_user.referral_code,
        "recovery_code": current_user.recovery_code,
        "center": center_data,
    }


# ---------------------------------------------------------
# 4. 로그아웃
# ---------------------------------------------------------
@router.post("/logout")
def logout(response: Response):
    response.delete_cookie("accessToken", path="/")
    return {"message": "로그아웃 성공"}


# ---------------------------------------------------------
# 5. 비밀번호 변경
# ---------------------------------------------------------
from pydantic import BaseModel, Field

class ChangePasswordIn(BaseModel):
    current_password: str = Field(..., min_length=1)
    new_password: str = Field(..., min_length=6)

@router.post("/change-password")
async def change_password(
    data: ChangePasswordIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if not verify_password(data.current_password, current_user.password_hash):
        raise HTTPException(status_code=400, detail="현재 비밀번호가 올바르지 않습니다.")

    if data.current_password == data.new_password:
        raise HTTPException(status_code=400, detail="새 비밀번호는 현재 비밀번호와 달라야 합니다")

    current_user.password_hash = hash_password(data.new_password)
    db.commit()

    return {"message": "비밀번호가 성공적으로 변경되었습니다."}


# ---------------------------------------------------------
# 5-1. 지갑 주소 변경
# ---------------------------------------------------------
class UpdateWalletIn(BaseModel):
    wallet_address: str = Field(..., min_length=6, max_length=128)

@router.put("/wallet-address")
async def update_wallet_address(
    data: UpdateWalletIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    current_user.wallet_address = data.wallet_address.strip()
    db.commit()
    return {"message": "지갑 주소가 변경되었습니다.", "wallet_address": current_user.wallet_address}


# ---------------------------------------------------------
# 6. 이메일/유저네임 중복 확인
# ---------------------------------------------------------
@router.get("/check-email")
def check_email(email: str, db: Session = Depends(get_db)):
    exists = db.query(User).filter(User.email == email).first() is not None
    return {"exists": exists}


@router.get("/check-username")
def check_username(username: str, db: Session = Depends(get_db)):
    exists = db.query(User).filter(User.username == username).first() is not None
    return {"exists": exists}


# ---------------------------------------------------------
# 7. 계정 복구 (복구 코드로 이메일 찾기)
# ---------------------------------------------------------
class FindEmailIn(BaseModel):
    recovery_code: str


@router.post("/find-email")
def find_email(data: FindEmailIn, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.recovery_code == data.recovery_code).first()
    if not user:
        raise HTTPException(status_code=404, detail="해당 복구 코드를 가진 계정이 없습니다.")

    email = user.email
    at_idx = email.index("@")
    masked_email = email[:2] + "*" * (at_idx - 2) + email[at_idx:]

    return {"email": masked_email, "full_email": user.email}


# ---------------------------------------------------------
# 8. 계정 복구 (복구 코드로 비밀번호 재설정)
# ---------------------------------------------------------
class ResetPasswordIn(BaseModel):
    recovery_code: str
    new_password: str = Field(..., min_length=6)


@router.post("/reset-password")
def reset_password(data: ResetPasswordIn, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.recovery_code == data.recovery_code).first()
    if not user:
        raise HTTPException(status_code=404, detail="해당 복구 코드를 가진 계정이 없습니다.")

    user.password_hash = hash_password(data.new_password)
    db.commit()

    return {"message": "비밀번호가 성공적으로 재설정되었습니다.", "email": user.email}
