from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.core.db import get_db
from app.core.security import hash_password, verify_password, create_access_token
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
    )
    db.add(user)
    db.commit()
    return Tokens(access=create_access_token(sub=user.email))


@router.post("/login", response_model=Tokens)
def login(data: LoginIn, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == data.email).first()
    if not user or not verify_password(data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="이메일 또는 비밀번호가 올바르지 않습니다.")
    return Tokens(access=create_access_token(sub=user.email))
