from passlib.hash import argon2
from datetime import datetime, timedelta, timezone
from jose import jwt


def hash_password(plain: str) -> str:
    return argon2.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    try:
        return argon2.verify(plain, hashed)
    except Exception:
        return False


def create_access_token(*, user_id: int, minutes: int, secret: str) -> str:
    """JWT 액세스 토큰 생성 (H1: 통합된 유일한 토큰 생성 함수)"""
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user_id),
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(minutes=minutes)).timestamp()),
    }
    return jwt.encode(payload, secret, algorithm="HS256")
