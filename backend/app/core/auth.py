from fastapi import Request, HTTPException, status, Depends
from jose import jwt, JWTError
from sqlalchemy.orm import Session
from app.core.db import get_db
from app.core.config import settings
from app.models import User

# 1. 일반 유저 확인 경비원 (쿠키 기반)
def get_current_user(request: Request, db: Session = Depends(get_db)):
    token = request.cookies.get("accessToken")
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="인증 세션이 없습니다. 다시 로그인해주세요."
        )

    try:
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

# 2. [추가] 관리자 확인 경비원 (쿠키 기반)
def get_current_admin(current_user: User = Depends(get_current_user)):
    # 유저의 role이 'admin'인지 확인합니다.
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="관리자 권한이 없습니다."
        )
    return current_user