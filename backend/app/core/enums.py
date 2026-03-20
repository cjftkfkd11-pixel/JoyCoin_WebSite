# backend/app/core/enums.py
from enum import Enum


class UserRole(str, Enum):
    """사용자 역할"""
    USER = "user"
    ADMIN = "admin"          # 슈퍼어드민 (최고 권한)
    US_ADMIN = "us_admin"    # 미국어드민 (조회 + USDT 출금신청)
    SECTOR_MANAGER = "sector_manager"


class DepositStatus(str, Enum):
    """입금 요청 상태"""
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class BlockchainNetwork(str, Enum):
    """지원하는 블록체인 네트워크"""
    SOLANA = "Solana"
