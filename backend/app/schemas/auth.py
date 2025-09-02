from pydantic import BaseModel, EmailStr, Field


class SignupIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=12)
    region_code: str | None = None
    referrer_code: str | None = None


class LoginIn(BaseModel):
    email: EmailStr
    password: str


class Tokens(BaseModel):
    access: str
