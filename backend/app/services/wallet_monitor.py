# backend/app/services/wallet_monitor.py
import time
import logging
import requests
from app.core.config import settings
from app.services.telegram import notify_deposit_detected

logger = logging.getLogger(__name__)

# USDT 컨트랙트 주소
POLYGON_USDT_CONTRACT = "0xc2132D05D31c914a87C6611C10748AEb04B58e8F"
ETH_USDT_CONTRACT = "0xdAC17F958D2ee523a2206206994597C13D831ec7"
TRON_USDT_CONTRACT = "TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t"

# Etherscan V2 API (Polygon + Ethereum 공용)
ETHERSCAN_V2_BASE = "https://api.etherscan.io/v2/api"

# 이미 알림 보낸 tx_hash (체인별 분리)
_notified_txs: set[str] = set()

# 유효하지 않은 주소로 반복 에러 방지
_disabled_chains: set[str] = set()


# ──────────────────────────────────────────────
# EVM 체인 (Polygon / Ethereum) - Etherscan V2
# ──────────────────────────────────────────────
def fetch_evm_usdt_transfers(admin_address: str, chain_id: int, contract: str) -> list[dict]:
    """Etherscan V2 API로 EVM 체인 USDT 입금 조회"""
    if not settings.POLYGONSCAN_API_KEY:
        return []

    params = {
        "chainid": chain_id,
        "module": "account",
        "action": "tokentx",
        "contractaddress": contract,
        "address": admin_address,
        "page": 1,
        "offset": 50,
        "sort": "desc",
        "apikey": settings.POLYGONSCAN_API_KEY,
    }

    try:
        resp = requests.get(ETHERSCAN_V2_BASE, params=params, timeout=15)
        resp.raise_for_status()
        data = resp.json()

        if data.get("status") != "1" or not data.get("result"):
            return []

        incoming = [
            tx for tx in data["result"]
            if tx.get("to", "").lower() == admin_address.lower()
        ]
        return incoming

    except Exception as e:
        logger.error(f"Etherscan V2 API error (chainid={chain_id}): {e}")
        return []


def _process_evm_txs(transactions: list[dict], chain_name: str):
    """EVM 트랜잭션 처리 (Polygon/Ethereum 공용)"""
    for tx in transactions:
        tx_hash = tx.get("hash", "")
        key = f"{chain_name}:{tx_hash}"

        if key in _notified_txs:
            continue

        raw_value = int(tx.get("value", "0"))
        amount = raw_value / (10 ** 6)  # USDT 6 decimals

        if amount <= 0:
            _notified_txs.add(key)
            continue

        sender = tx.get("from", "unknown")
        logger.info(f"[{chain_name}] USDT deposit: {amount} from {sender} (tx: {tx_hash[:16]}...)")

        notify_deposit_detected(
            amount=amount,
            sender=sender,
            tx_hash=tx_hash,
            chain=chain_name,
        )
        _notified_txs.add(key)


# ──────────────────────────────────────────────
# TRON (TRC-20) - TronGrid API
# ──────────────────────────────────────────────
def fetch_tron_usdt_transfers(admin_address: str) -> list[dict]:
    """TronGrid API로 TRON USDT 입금 조회"""
    url = f"https://api.trongrid.io/v1/accounts/{admin_address}/transactions/trc20"
    params = {
        "only_to": "true",
        "contract_address": TRON_USDT_CONTRACT,
        "limit": 50,
        "order_by": "block_timestamp,desc",
    }
    headers = {}
    if settings.TRONGRID_API_KEY:
        headers["TRON-PRO-API-KEY"] = settings.TRONGRID_API_KEY

    try:
        resp = requests.get(url, params=params, headers=headers, timeout=15)
        if resp.status_code == 400:
            body = resp.json() if resp.headers.get("content-type", "").startswith("application/json") else {}
            err_msg = body.get("error", resp.text[:200])
            logger.error(f"TronGrid 400 Bad Request: {err_msg} — disabling TRON polling")
            _disabled_chains.add("TRON")
            return []
        resp.raise_for_status()
        data = resp.json()
        return data.get("data", [])
    except requests.exceptions.RequestException as e:
        logger.error(f"TronGrid API error: {e}")
        return []


def _process_tron_txs(transactions: list[dict]):
    """TRON 트랜잭션 처리"""
    for tx in transactions:
        tx_hash = tx.get("transaction_id", "")
        key = f"TRON:{tx_hash}"

        if key in _notified_txs:
            continue

        token_info = tx.get("token_info", {})
        decimals = int(token_info.get("decimals", 6))
        raw_value = int(tx.get("value", "0"))
        amount = raw_value / (10 ** decimals)

        if amount <= 0:
            _notified_txs.add(key)
            continue

        sender = tx.get("from", "unknown")
        logger.info(f"[TRON] USDT deposit: {amount} from {sender} (tx: {tx_hash[:16]}...)")

        notify_deposit_detected(
            amount=amount,
            sender=sender,
            tx_hash=tx_hash,
            chain="TRON",
        )
        _notified_txs.add(key)


# ──────────────────────────────────────────────
# 통합 폴링
# ──────────────────────────────────────────────
def _init_known_txs():
    """서버 시작 시 기존 트랜잭션을 등록하여 중복 알림 방지"""
    evm_addr = settings.USDT_ADMIN_ADDRESS
    tron_addr = settings.USDT_ADMIN_ADDRESS_TRON

    # Polygon
    if evm_addr and settings.POLYGONSCAN_API_KEY:
        try:
            txs = fetch_evm_usdt_transfers(evm_addr, 137, POLYGON_USDT_CONTRACT)
            for tx in txs:
                _notified_txs.add(f"Polygon:{tx.get('hash', '')}")
            logger.info(f"Polygon: {len(txs)} existing txs marked as known")
        except Exception as e:
            logger.error(f"Polygon init error: {e}")

    # Ethereum
    if evm_addr and settings.POLYGONSCAN_API_KEY:
        try:
            txs = fetch_evm_usdt_transfers(evm_addr, 1, ETH_USDT_CONTRACT)
            for tx in txs:
                _notified_txs.add(f"Ethereum:{tx.get('hash', '')}")
            logger.info(f"Ethereum: {len(txs)} existing txs marked as known")
        except Exception as e:
            logger.error(f"Ethereum init error: {e}")

    # TRON
    if tron_addr and "TRON" not in _disabled_chains:
        try:
            txs = fetch_tron_usdt_transfers(tron_addr)
            for tx in txs:
                _notified_txs.add(f"TRON:{tx.get('transaction_id', '')}")
            logger.info(f"TRON: {len(txs)} existing txs marked as known")
        except Exception as e:
            logger.error(f"TRON init error: {e}")


def poll_wallet_once():
    """1회 폴링: 모든 체인의 USDT 입금 감지"""
    evm_addr = settings.USDT_ADMIN_ADDRESS
    tron_addr = settings.USDT_ADMIN_ADDRESS_TRON

    # Polygon
    if evm_addr and settings.POLYGONSCAN_API_KEY:
        txs = fetch_evm_usdt_transfers(evm_addr, 137, POLYGON_USDT_CONTRACT)
        _process_evm_txs(txs, "Polygon")

    # Ethereum
    if evm_addr and settings.POLYGONSCAN_API_KEY:
        txs = fetch_evm_usdt_transfers(evm_addr, 1, ETH_USDT_CONTRACT)
        _process_evm_txs(txs, "Ethereum")

    # TRON
    if tron_addr and "TRON" not in _disabled_chains:
        txs = fetch_tron_usdt_transfers(tron_addr)
        _process_tron_txs(txs)

    # 메모리 관리
    if len(_notified_txs) > 3000:
        _notified_txs.clear()


def wallet_monitor_loop():
    """백그라운드 스레드: 주기적으로 전체 체인 폴링"""
    interval = settings.WALLET_POLL_INTERVAL_SECONDS or 60
    logger.info(f"Wallet monitor started (polling every {interval}s)")

    _init_known_txs()

    while True:
        try:
            poll_wallet_once()
        except Exception as e:
            logger.error(f"Wallet monitor error: {e}")
        time.sleep(interval)
