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

# Solana USDT (SPL) 민트 주소
SOLANA_USDT_MINT = "Es9vMFrzaCERmJfrF4H2FYD4KCoNkY11McCe8BenwNYB"
SOLANA_RPC = "https://api.mainnet-beta.solana.com"

# 이미 처리한 tx_hash (중복 방지)
_notified_txs: set[str] = set()

# 관리자 USDT 토큰 계정 주소 (캐시)
_solana_token_account: str | None = None


# ──────────────────────────────────────────────
# 입금 매칭 로직 (공통)
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
        # 중복 처리 방지
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
            logger.warning(f"No matching deposit for {amount} USDT on {chain} (decimal: {decimal_part})")
            notify_deposit_unmatched(amount=amount, sender=sender, tx_hash=tx_hash, chain=chain)
            return

        # 매칭 성공 → DB 업데이트
        matched.actual_amount = amount_rounded
        matched.detected_tx_hash = tx_hash

        from app.models import User
        from datetime import datetime
        user = db.query(User).filter(User.id == matched.user_id).first()
        user_email = user.email if user else "unknown"

        rate = db.query(ExchangeRate).filter(ExchangeRate.is_active == True).first()
        joy_per_usdt = float(rate.joy_per_usdt) if rate else 5.0

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

            logger.info(f"Deposit auto-approved: #{matched.id} = {amount_rounded} USDT")
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
                f"JOY: {recalculated_joy}"
            )
            notify_deposit_underpaid(
                user_email=user_email,
                expected=float(matched.expected_amount),
                actual=amount_rounded,
                original_joy=matched.joy_amount,
                recalculated_joy=recalculated_joy,
                chain=chain,
                tx_hash=tx_hash,
                deposit_id=matched.id,
            )

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
# Solana SPL USDT 모니터링
# ──────────────────────────────────────────────
def _solana_rpc(method: str, params: list) -> dict:
    payload = {"jsonrpc": "2.0", "id": 1, "method": method, "params": params}
    resp = requests.post(SOLANA_RPC, json=payload, timeout=20)
    resp.raise_for_status()
    return resp.json()


def get_solana_usdt_token_account(wallet_address: str) -> str | None:
    """관리자 지갑의 USDT 토큰 계정 주소 조회"""
    try:
        result = _solana_rpc("getTokenAccountsByOwner", [
            wallet_address,
            {"mint": SOLANA_USDT_MINT},
            {"encoding": "jsonParsed"},
        ])
        accounts = result.get("result", {}).get("value", [])
        if accounts:
            return accounts[0]["pubkey"]
        logger.warning(f"No USDT token account found for {wallet_address}")
        return None
    except Exception as e:
        logger.error(f"Solana getTokenAccountsByOwner error: {e}")
        return None


def fetch_solana_usdt_transfers(token_account: str, limit: int = 30) -> list[dict]:
    """Solana USDT 입금 내역 조회"""
    try:
        # 최근 서명 목록
        sig_result = _solana_rpc("getSignaturesForAddress", [
            token_account,
            {"limit": limit},
        ])
        signatures = sig_result.get("result", [])

        transfers = []
        for sig_info in signatures:
            sig = sig_info.get("signature")
            if not sig or sig_info.get("err"):
                continue

            key = f"Solana:{sig}"
            if key in _notified_txs:
                continue

            try:
                tx_result = _solana_rpc("getParsedTransaction", [
                    sig,
                    {"encoding": "jsonParsed", "maxSupportedTransactionVersion": 0},
                ])
                tx = tx_result.get("result")
                if not tx:
                    continue

                # SPL 토큰 transfer 명령어 파싱
                instructions = (
                    tx.get("transaction", {})
                    .get("message", {})
                    .get("instructions", [])
                )
                # inner instructions도 확인
                inner = tx.get("meta", {}).get("innerInstructions", [])
                all_instructions = list(instructions)
                for inner_group in inner:
                    all_instructions.extend(inner_group.get("instructions", []))

                for ix in all_instructions:
                    if ix.get("program") != "spl-token":
                        continue
                    parsed = ix.get("parsed", {})
                    if parsed.get("type") not in ("transfer", "transferChecked"):
                        continue
                    info = parsed.get("info", {})
                    dest = info.get("destination") or info.get("destination", "")
                    if dest != token_account:
                        continue

                    # 금액 파싱
                    token_amount = info.get("tokenAmount", {})
                    ui_amount = token_amount.get("uiAmount") if token_amount else None
                    if ui_amount is None:
                        raw = int(info.get("amount", 0))
                        ui_amount = raw / 1_000_000  # USDT 6 decimals

                    sender = info.get("authority") or info.get("source", "unknown")
                    transfers.append({
                        "tx_hash": sig,
                        "amount": round(float(ui_amount), 2),
                        "sender": sender,
                    })
                    break  # 같은 tx에서 첫 번째 매칭만

            except Exception as e:
                logger.error(f"Solana tx parse error ({sig[:16]}...): {e}")
                continue

        return transfers

    except Exception as e:
        logger.error(f"Solana fetch error: {e}")
        return []


def _process_solana_txs(transfers: list[dict]):
    for t in transfers:
        key = f"Solana:{t['tx_hash']}"
        if key in _notified_txs:
            continue

        amount = t["amount"]
        if amount <= 0:
            _notified_txs.add(key)
            continue

        logger.info(f"[Solana] USDT deposit: {amount} from {t['sender']} (tx: {t['tx_hash'][:16]}...)")
        _match_deposit_to_request(
            amount=amount,
            sender=t["sender"],
            tx_hash=t["tx_hash"],
            chain="Solana",
        )
        _notified_txs.add(key)


# ──────────────────────────────────────────────
# 통합 폴링
# ──────────────────────────────────────────────
def _init_known_txs():
    """서버 시작 시 기존 트랜잭션 등록 (중복 알림 방지)"""
    global _solana_token_account

    solana_addr = settings.USDT_ADMIN_ADDRESS_SOLANA
    if solana_addr:
        try:
            _solana_token_account = get_solana_usdt_token_account(solana_addr)
            if _solana_token_account:
                transfers = fetch_solana_usdt_transfers(_solana_token_account, limit=50)
                for t in transfers:
                    _notified_txs.add(f"Solana:{t['tx_hash']}")
                logger.info(f"Solana: {len(transfers)} existing txs marked as known")
        except Exception as e:
            logger.error(f"Solana init error: {e}")


def poll_wallet_once():
    """1회 폴링: Solana USDT 입금 감지"""
    global _solana_token_account

    solana_addr = settings.USDT_ADMIN_ADDRESS_SOLANA
    if not solana_addr:
        return

    # 토큰 계정 캐시
    if not _solana_token_account:
        _solana_token_account = get_solana_usdt_token_account(solana_addr)

    if _solana_token_account:
        transfers = fetch_solana_usdt_transfers(_solana_token_account)
        _process_solana_txs(transfers)

    # 메모리 관리
    if len(_notified_txs) > 3000:
        _notified_txs.clear()


def wallet_monitor_loop():
    """백그라운드 스레드: 주기적으로 Solana 폴링"""
    interval = settings.WALLET_POLL_INTERVAL_SECONDS or 60
    logger.info(f"Wallet monitor started (Solana, polling every {interval}s)")

    _init_known_txs()

    while True:
        try:
            poll_wallet_once()
        except Exception as e:
            logger.error(f"Wallet monitor error: {e}")
        time.sleep(interval)
