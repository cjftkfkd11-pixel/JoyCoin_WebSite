# backend/app/schemas/deposits.py
from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional


class DepositRequestIn(BaseModel):
    chain: str = Field(..., pattern="^(TRON|ETH)$")
    amount_usdt: float


class DepositRequestOut(BaseModel):
    id: int
    user_id: int
    chain: str
    assigned_address: str
    expected_amount: float
    reference_code: str
    status: str
    detected_amount: Optional[float] = None
    tx_hash: Optional[str] = None
    from_address: Optional[str] = None
    confirmed_at: Optional[datetime] = None
    created_at: datetime

    model_config = dict(from_attributes=True)  # ✅ v2
