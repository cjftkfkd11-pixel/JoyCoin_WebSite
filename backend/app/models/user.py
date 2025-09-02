from sqlalchemy import String, Integer, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column
from app.core.db import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    email: Mapped[str] = mapped_column(
        String(255), unique=True, index=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    region_code: Mapped[str | None] = mapped_column(String(32), nullable=True)
    referrer_code: Mapped[str | None] = mapped_column(
        String(64), nullable=True)
    role: Mapped[str] = mapped_column(String(16), default="user")
    created_at: Mapped[str] = mapped_column(
        DateTime(timezone=True), server_default=func.now())
