# backend/app/services/wallet_monitor.py
import time
import logging
import requests
from app.core.config import settings
from app.services.telegram import (
    notify_deposit_detected,
    notify_deposit_matched,
    notify_deposit_underpaid,
    notify_deposit_unmatched,
)

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
# 입금 매칭 로직
# ──────────────────────────────────────────────
def _match_deposit_to_request(amount: float, sender: str, tx_hash: str, chain: str):
    """
    블록체인에서 감지된 입금을 DB의 pending 요청과 매칭.
    소수점 식별자(0.37 등)를 기반으로 매칭.
    """
    from app.core.db import SessionLocal
    from app.models import DepositRequest, ExchangeRate, Notification

    db = SessionLocal()
    try:
        # 중복 처리 방지: 이미 매칭된 TX인지 확인
        existing = db.query(DepositRequest).filter(
            DepositRequest.detected_tx_hash == tx_hash
        ).first()
        if existing:
            logger.info(f"TX {tx_hash[:16]}... already matched to deposit #{existing.id}")
            return

        # 소수점 추출 (예: 200.37 → 0.37)
        amount_rounded = round(amount, 2)
        decimal_part = round(amount_rounded % 1, 2)

        # 같은 체인의 pending 요청 중 소수점이 일치하는 것 찾기
        pending_requests = db.query(DepositRequest).filter(
            DepositRequest.chain == chain,
            DepositRequest.status == "pending",
            DepositRequest.detected_tx_hash == None,
        ).all()

        matched = None
        for req in pending_requests:
            req_decimal = round(float(req.expected_amount) % 1, 2)
            if req_decimal == decimal_part and decimal_part > 0:
                matched = req
                break

        if not matched:
            # 매칭 실패 → 미매칭 알림
            logger.warning(f"No matching deposit for {amount} USDT on {chain} (decimal: {decimal_part})")
            notify_deposit_unmatched(amount=amount, sender=sender, tx_hash=tx_hash, chain=chain)
            return

        # 매칭 성공 → DB 업데이트
        matched.actual_amount = amount_rounded
        matched.detected_tx_hash = tx_hash

        # 유저 정보 로드
        from app.models import User
        from datetime import datetime
        user = db.query(User).filter(User.id == matched.user_id).first()
        user_email = user.email if user else "unknown"

        # 환율 조회
        rate = db.query(ExchangeRate).filter(ExchangeRate.is_active == True).first()
        joy_per_usdt = float(rate.joy_per_usdt) if rate else 5.0

        # 금액 차이 판단 (소수점 식별자 제거한 정수 기준)
        expected_base = int(float(matched.expected_amount))
        actual_base = int(amount_rounded)
        diff = expected_base - actual_base

        if diff <= 0:
            # 정상 입금 → 자동 승인 + JOY 지급
            matched.status = "approved"
            matched.approved_at = datetime.utcnow()
            matched.joy_credited = True

            if user:
                user.total_joy = int(user.total_joy or 0) + int(matched.joy_amount or 0)

            logger.info(f"Deposit auto-approved: #{matched.id} = {amount_rounded} USDT (expected {matched.expected_amount})")
            notify_deposit_matched(
                user_email=user_email,
                expected=float(matched.expected_amount),
                actual=amount_rounded,
                joy_amount=matched.joy_amount,
                chain=chain,
                tx_hash=tx_hash,
                deposit_id=matched.id,
            )
        else:
            # 부족 입금 → JOY 재계산 후 지급
            recalculated_joy = int(actual_base * joy_per_usdt)
            matched.joy_amount = recalculated_joy
            matched.status = "approved"
            matched.approved_at = datetime.utcnow()
            matched.joy_credited = True

            if user:
                user.total_joy = int(user.total_joy or 0) + recalculated_joy

            logger.warning(
                f"Underpaid deposit #{matched.id}: expected {expected_base}, got {actual_base}. "
                f"JOY: {original_joy} → {recalculated_joy}"
            )

            notify_deposit_underpaid(
                user_email=user_email,
                expected=float(matched.expected_amount),
                actual=amount_rounded,
                original_joy=original_joy,
                recalculated_joy=recalculated_joy,
                chain=chain,
                tx_hash=tx_hash,
                deposit_id=matched.id,
            )

            # 유저 인앱 알림 생성
            if user:
                notif = Notification(
                    user_id=user.id,
                    title="입금 금액 부족",
                    message=(
                        f"예상 금액: {matched.expected_amount} USDT, "
                        f"실제 입금: {amount_rounded} USDT. "
                        f"JOY {recalculated_joy:,}개로 조정되었습니다."
                    ),
                    type="deposit_underpaid",
                )
                db.add(notif)

        db.commit()

    except Exception as e:
        db.rollback()
        logger.error(f"Deposit matching error: {e}")
    finally:
        db.close()


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
    """EVM 트랜잭션 처리 (Polygon/Ethereum 공용) + 자동 매칭"""
    for tx in transactions:
        tx_hash = tx.get("hash", "")
        key = f"{chain_name}:{tx_hash}"

        if key in _notified_txs:
            continue

        raw_value = int(tx.get("value", "0"))
        amount = raw_value / (10 ** 6)  # USDT 6 decimals
        amount = round(amount, 2)

        if amount <= 0:
            _notified_txs.add(key)
            continue

        sender = tx.get("from", "unknown")
        logger.info(f"[{chain_name}] USDT deposit: {amount} from {sender} (tx: {tx_hash[:16]}...)")

        # 자동 매칭 시도
        _match_deposit_to_request(
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
    """TRON 트랜잭션 처리 + 자동 매칭"""
    for tx in transactions:
        tx_hash = tx.get("transaction_id", "")
        key = f"TRON:{tx_hash}"

        if key in _notified_txs:
            continue

        token_info = tx.get("token_info", {})
        decimals = int(token_info.get("decimals", 6))
        raw_value = int(tx.get("value", "0"))
        amount = raw_value / (10 ** decimals)
        amount = round(amount, 2)

        if amount <= 0:
            _notified_txs.add(key)
            continue

        sender = tx.get("from", "unknown")
        logger.info(f"[TRON] USDT deposit: {amount} from {sender} (tx: {tx_hash[:16]}...)")

        # 자동 매칭 시도
        _match_deposit_to_request(
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
