# backend/app/api/deposits.py

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.core.db import get_db
from app.core.auth import get_current_user
from app.models import User, DepositRequest

from app.schemas.deposits import DepositRequestIn, DepositRequestOut
from app.services.deposits import create_deposit_request, get_user_deposits

router = APIRouter(prefix="/deposits", tags=["deposits"])
limiter = Limiter(key_func=get_remote_address)


@router.post("/request", response_model=DepositRequestOut)
@limiter.limit("3/minute")  # 1분에 3번까지만 입금 요청 가능
def request_deposit(
    request: Request,
    data: DepositRequestIn,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return create_deposit_request(db, user, data)


@router.get("/my")
def my_deposits(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    items = get_user_deposits(db, user)
    return {"items": items}
