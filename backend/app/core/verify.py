import os, secrets
import redis

BACKEND_PUBLIC_URL = os.getenv("BACKEND_PUBLIC_URL", "http://localhost:8000")
REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")
r = redis.Redis.from_url(REDIS_URL, decode_responses=True)

VERIFY_PREFIX = "verify_email:"
TTL_SECONDS = 15 * 60  # 15분


def generate_email_verify_link(email: str) -> str:
    token = secrets.token_urlsafe(32)
    r.setex(f"{VERIFY_PREFIX}{token}", TTL_SECONDS, email)
    return f"{BACKEND_PUBLIC_URL}/auth/verify-email?token={token}"


def consume_email_token(token: str) -> str | None:
    key = f"{VERIFY_PREFIX}{token}"
    email = r.get(key)
    if not email:
        return None
    r.delete(key)
    return email
