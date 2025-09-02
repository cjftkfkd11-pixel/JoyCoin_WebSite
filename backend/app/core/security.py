import os
import time
from passlib.hash import argon2
from jose import jwt

JWT_SECRET = os.getenv("JWT_SECRET", "change_me")
JWT_EXPIRE_MIN = int(os.getenv("JWT_EXPIRE_MIN", "20"))
ALGO = "HS256"


def hash_password(plain: str) -> str:
    return argon2.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    try:
        return argon2.verify(plain, hashed)
    except Exception:
        return False


def create_access_token(sub: str) -> str:
    now = int(time.time())
    exp = now + (JWT_EXPIRE_MIN * 60)
    payload = {"sub": sub, "iat": now, "exp": exp, "type": "access"}
    return jwt.encode(payload, JWT_SECRET, algorithm=ALGO)
