from pydantic import BaseModel, EmailStr, Field


class SignupIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=6)
    username: str = Field(min_length=2, max_length=100)
    wallet_address: str = Field(min_length=6, max_length=128)
    referral_code: str | None = None
    center_id: int | None = None
    sector_id: int | None = None
    terms_accepted: bool
    risk_accepted: bool
    privacy_accepted: bool
    legal_version: str = Field(default="2026-02-10", min_length=1, max_length=32)
    locale: str | None = None


class LoginIn(BaseModel):
    email: EmailStr
    password: str


class Tokens(BaseModel):
    access: str
