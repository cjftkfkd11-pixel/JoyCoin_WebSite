from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from app.core.db import get_db
from app.core.security import hash_password, verify_password, create_access_token
from app.core.email import send_email
from app.core.verify import generate_email_verify_link, consume_email_token
from app.schemas.auth import SignupIn, LoginIn, Tokens
from app.models.user import User

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/signup", response_model=Tokens)
def signup(data: SignupIn, db: Session = Depends(get_db)):
    exists = db.query(User).filter(User.email == data.email).first()
    if exists:
        raise HTTPException(status_code=400, detail="이미 가입된 이메일입니다.")
    user = User(
        email=data.email,
        password_hash=hash_password(data.password),
        region_code=data.region_code,
        referrer_code=data.referrer_code,
        role="user",
        is_email_verified=False,  # 이메일 인증 전
    )
    db.add(user)
    db.commit()

    # 인증 링크 생성 + '로그'로 발송
    link = generate_email_verify_link(user.email)
    send_email(
        to=user.email,
        subject="[JoyCoin] 이메일 인증을 완료해 주세요",
        body=f"아래 링크를 클릭하여 이메일 인증을 완료하세요(15분 유효)\n\n{link}",
    )

    # 프론트 호환을 위해 토큰은 발급(단 로그인은 인증 전 403)
    return Tokens(access=create_access_token(sub=user.email))


@router.post("/login", response_model=Tokens)
def login(data: LoginIn, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == data.email).first()
    if not user or not verify_password(data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="이메일 또는 비밀번호가 올바르지 않습니다.",
        )
    if not user.is_email_verified:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="이메일 인증이 필요합니다."
        )
    return Tokens(access=create_access_token(sub=user.email))


@router.get("/verify-email")
def verify_email(token: str = Query(...), db: Session = Depends(get_db)):
    email = consume_email_token(token)
    if not email:
        raise HTTPException(
            status_code=400, detail="토큰이 유효하지 않거나 만료되었습니다."
        )
    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(status_code=404, detail="사용자를 찾을 수 없습니다.")
    if not user.is_email_verified:
        user.is_email_verified = True
        db.add(user)
        db.commit()
    return {"message": "이메일 인증이 완료되었습니다. 이제 로그인할 수 있습니다."}


@router.post("/request-email-verify")
def request_email_verify(email: str, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(status_code=404, detail="사용자를 찾을 수 없습니다.")
    if user.is_email_verified:
        return {"message": "이미 이메일 인증이 완료되었습니다."}
    link = generate_email_verify_link(user.email)
    send_email(
        to=user.email,
        subject="[JoyCoin] 이메일 인증 링크 재발송",
        body=f"아래 링크를 클릭하여 이메일 인증을 완료하세요(15분 유효)\n\n{link}",
    )
    return {"message": "인증 메일을 재발송했습니다."}
