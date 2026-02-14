# backend/app/models/__init__.py

from app.models.center import Center
from app.models.sector import Sector
from app.models.user import User
from app.models.referral import Referral
from app.models.product import Product
from app.models.purchase import Purchase
from app.models.deposit_request import DepositRequest
from app.models.point import Point
from app.models.exchange_rate import ExchangeRate
from app.models.notification import Notification
from app.models.legal_consent import LegalConsent
from app.models.point_withdrawal import PointWithdrawal

__all__ = [
    "User",
    "Center",
    "Sector",
    "Referral",
    "Product",
    "Purchase",
    "DepositRequest",
    "Point",
    "ExchangeRate",
    "Notification",
    "LegalConsent",
    "PointWithdrawal",
]
