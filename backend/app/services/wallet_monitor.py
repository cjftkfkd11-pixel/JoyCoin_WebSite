# backend/app/services/wallet_monitor.py
import time
import logging
import requests
from app.core.config import settings
from app.services.telegram import notify_deposit_detected

logger = logging.getLogger(__name__)

# Polygon USDT 컨트랙트 주소
POLYGON_USDT_CONTRACT = "0xc2132D05D31c914a87C6611C10748AEb04B58e8F"

# Etherscan V2 API 베이스 URL
API_BASE = "https://api.etherscan.io/v2/api"

# 이미 알림 보낸 tx_hash 저장 (중복 방지)
_notified_txs: set[str] = set()


def fetch_recent_usdt_transfers(admin_address: str) -> list[dict]:
    """
    Etherscan V2 API로 관리자 지갑의 최근 USDT 입금 조회
    """
    params = {
        "chainid": 137,  # Polygon
        "module": "account",
        "action": "tokentx",
        "contractaddress": POLYGON_USDT_CONTRACT,
        "address": admin_address,
        "page": 1,
        "offset": 50,
        "sort": "desc",
        "apikey": settings.POLYGONSCAN_API_KEY,
    }

    try:
        resp = requests.get(API_BASE, params=params, timeout=15)
        resp.raise_for_status()
        data = resp.json()

        if data.get("status") != "1" or not data.get("result"):
            return []

        # 관리자 지갑으로 들어온 것만 필터 (to == admin_address)
        incoming = [
            tx for tx in data["result"]
            if tx.get("to", "").lower() == admin_address.lower()
        ]

        return incoming

    except Exception as e:
        logger.error(f"Polygonscan API error: {e}")
        return []


def _init_known_txs():
    """
    서버 시작 시 기존 트랜잭션을 모두 '이미 알림 보낸 것'으로 등록하여
    이전 입금에 대한 중복 알림 방지
    """
    if not settings.USDT_ADMIN_ADDRESS or not settings.POLYGONSCAN_API_KEY:
        return

    try:
        transactions = fetch_recent_usdt_transfers(settings.USDT_ADMIN_ADDRESS)
        for tx in transactions:
            _notified_txs.add(tx.get("hash", ""))
        logger.info(f"Wallet monitor initialized: {len(transactions)} existing txs marked as known")
    except Exception as e:
        logger.error(f"Failed to init wallet monitor: {e}")


def poll_wallet_once():
    """
    1회 폴링: 새 USDT 입금 감지 → 텔레그램 알림
    """
    if not settings.USDT_ADMIN_ADDRESS or not settings.POLYGONSCAN_API_KEY:
        return

    transactions = fetch_recent_usdt_transfers(settings.USDT_ADMIN_ADDRESS)

    for tx in transactions:
        tx_hash = tx.get("hash", "")

        # 이미 알림 보낸 트랜잭션 스킵
        if tx_hash in _notified_txs:
            continue

        # USDT는 6 decimals
        raw_value = int(tx.get("value", "0"))
        amount = raw_value / (10 ** 6)

        # 0 USDT 트랜잭션 무시
        if amount <= 0:
            _notified_txs.add(tx_hash)
            continue

        sender = tx.get("from", "unknown")

        logger.info(f"New USDT deposit detected: {amount} USDT from {sender} (tx: {tx_hash[:16]}...)")

        # 텔레그램 알림 전송
        notify_deposit_detected(
            amount=amount,
            sender=sender,
            tx_hash=tx_hash,
        )

        _notified_txs.add(tx_hash)

    # 메모리 관리: 알림 기록이 너무 커지지 않도록 제한
    if len(_notified_txs) > 1000:
        # 가장 오래된 것들 제거 (set이라 순서 없지만, clear보다 나음)
        _notified_txs.clear()


def wallet_monitor_loop():
    """
    백그라운드 스레드: 주기적으로 지갑 폴링
    """
    interval = settings.WALLET_POLL_INTERVAL_SECONDS or 60
    logger.info(f"Wallet monitor started (polling every {interval}s)")

    # 기존 트랜잭션 등록 (중복 알림 방지)
    _init_known_txs()

    while True:
        try:
            poll_wallet_once()
        except Exception as e:
            logger.error(f"Wallet monitor error: {e}")
        time.sleep(interval)
