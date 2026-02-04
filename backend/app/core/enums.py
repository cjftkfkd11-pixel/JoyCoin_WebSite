# backend/app/core/enums.py
from enum import Enum


class UserRole(str, Enum):
    """사용자 역할"""
    USER = "user"
    ADMIN = "admin"


class DepositStatus(str, Enum):
    """입금 요청 상태"""
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class BlockchainNetwork(str, Enum):
    """지원하는 블록체인 네트워크"""
    TRC20 = "TRC20"
    ERC20 = "ERC20"
    BSC = "BSC"
    POLYGON = "Polygon"
