# backend/app/services/wallet_monitor.py
import time
import logging
import requests
from collections import OrderedDict
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

# ──────────────────────────────────────────────
# [개선 1] LRU 방식 중복 방지 (기존: set → clear 시 전체 삭제 위험)
# OrderedDict를 사용해 오래된 것부터 제거하여 메모리 누수 없이 중복 방지
# ──────────────────────────────────────────────
_MAX_KNOWN_TXS = 2000  # 최대 저장 개수
_notified_txs: OrderedDict[str, bool] = OrderedDict()


def _add_known_tx(key: str):
    """처리 완료된 tx를 LRU 캐시에 추가 (오래된 것부터 자동 제거)"""
    _notified_txs[key] = True
    # 최대 개수를 넘으면 가장 오래된 것부터 제거 (clear 대신 점진적 삭제)
    while len(_notified_txs) > _MAX_KNOWN_TXS:
        _notified_txs.popitem(last=False)


def _is_known_tx(key: str) -> bool:
    """이미 처리한 tx인지 확인"""
    return key in _notified_txs


# 관리자 USDT 토큰 계정 주소 (캐시)
_solana_token_account: str | None = None

# [개선 2] 마지막으로 확인한 signature 저장 → 이후 새 tx만 조회
_last_known_signature: str | None = None

# [개선 3] 연속 에러 카운터 → 에러 시 폴링 간격 자동 증가
_consecutive_errors: int = 0

# ──────────────────────────────────────────────
# [개선 4] RPC 호출 간 딜레이 설정
# 무료 Solana RPC는 초당 ~10회 제한
# 호출 사이에 최소 딜레이를 두어 rate limit 회피
# ──────────────────────────────────────────────
_RPC_CALL_DELAY = 0.3        # RPC 호출 사이 최소 대기 시간 (초)
_BACKOFF_MAX_WAIT = 60       # exponential backoff 최대 대기 시간 (초)
_BACKOFF_MAX_RETRIES = 4     # 최대 재시도 횟수 (1→2→4→8초 후 포기)


# ──────────────────────────────────────────────
# 입금 매칭 로직 (공통) — 변경 없음
# ──────────────────────────────────────────────
def _match_deposit_to_request(amount: float, sender: str, tx_hash: str, chain: str):
    """
    블록체인에서 감지된 입금을 DB의 pending 요청과 매칭.
    소수점 식별자(0.37 등)를 기반으로 매칭.
    """
    from app.core.db import SessionLocal
    from app.models import DepositRequest, ExchangeRate, Notification, Point

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

        # 추천 보상: 구매자의 추천인(referred_by)에게 포인트 지급 (횟수 제한 없음)
        if user and user.referred_by:
            from sqlalchemy import func as sqlfunc
            referrer = db.query(User).filter(User.id == user.referred_by).first()
            if referrer:
                bonus_pct = rate.referral_bonus_percent if rate else 10
                usdt_amount = float(matched.actual_amount or matched.expected_amount or 0)
                bonus_points = int(usdt_amount * bonus_pct / 100)
                if bonus_points > 0:
                    current_balance = db.query(
                        sqlfunc.coalesce(sqlfunc.sum(Point.amount), 0)
                    ).filter(Point.user_id == referrer.id).scalar()
                    point_record = Point(
                        user_id=referrer.id,
                        amount=bonus_points,
                        balance_after=int(current_balance) + bonus_points,
                        type="referral_bonus",
                        description=f"추천 보상: {user.email} 구매 ({usdt_amount} USDT의 {bonus_pct}%)",
                    )
                    db.add(point_record)
                    referrer.total_points = int(referrer.total_points or 0) + bonus_points
                    logger.info(f"Referral bonus: referrer #{referrer.id} +{bonus_points}pts from buyer #{user.id} ({bonus_pct}%)")

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
    """
    [개선 5] Solana RPC 호출 + exponential backoff 재시도

    429 (Too Many Requests) 발생 시:
      1차 재시도: 1초 대기
      2차 재시도: 2초 대기
      3차 재시도: 4초 대기
      4차 재시도: 8초 대기
      → 그래도 실패하면 예외 발생 (다음 폴링 주기에 재시도)

    모든 RPC 호출 후 _RPC_CALL_DELAY만큼 대기하여 초당 호출 수 제한
    """
    last_error = None

    for attempt in range(_BACKOFF_MAX_RETRIES + 1):
        try:
            payload = {"jsonrpc": "2.0", "id": 1, "method": method, "params": params}
            resp = requests.post(SOLANA_RPC, json=payload, timeout=20)

            # 429 발생 → backoff 후 재시도
            if resp.status_code == 429:
                wait = min(2 ** attempt, _BACKOFF_MAX_WAIT)
                logger.warning(
                    f"RPC 429 rate limited ({method}), "
                    f"attempt {attempt + 1}/{_BACKOFF_MAX_RETRIES + 1}, "
                    f"waiting {wait}s..."
                )
                time.sleep(wait)
                continue

            resp.raise_for_status()

            # [개선 6] 호출 성공 후 다음 호출까지 딜레이
            # 연속 호출로 rate limit에 걸리는 것을 방지
            time.sleep(_RPC_CALL_DELAY)

            return resp.json()

        except requests.exceptions.HTTPError as e:
            if resp.status_code == 429:
                last_error = e
                continue  # 위에서 이미 처리됨
            raise  # 429 이외의 HTTP 에러는 즉시 발생
        except requests.exceptions.RequestException as e:
            # 네트워크 에러 (타임아웃 등)도 backoff 적용
            wait = min(2 ** attempt, _BACKOFF_MAX_WAIT)
            logger.warning(f"RPC network error ({method}): {e}, waiting {wait}s...")
            last_error = e
            time.sleep(wait)

    # 모든 재시도 실패
    logger.error(f"RPC {method} failed after {_BACKOFF_MAX_RETRIES + 1} attempts")
    raise last_error or Exception(f"RPC {method} failed")


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


def _fetch_new_signatures(token_account: str, limit: int = 15) -> list[dict]:
    """
    [개선 7] 새로운 signature만 가져오기

    기존 문제: 매번 최근 30개 signature를 전부 가져와서,
    각각에 대해 getTransaction을 호출 → 대부분 이미 처리한 tx를 중복 조회

    개선: _last_known_signature 이후의 새 tx만 조회
    - until 파라미터: 마지막으로 본 signature 이후만 가져옴
    - limit도 30 → 15로 줄임 (90초 간격이면 15개면 충분)
    """
    global _last_known_signature

    try:
        # until 파라미터로 마지막 확인 이후의 새 tx만 가져오기
        params: dict = {"limit": limit}
        if _last_known_signature:
            params["until"] = _last_known_signature

        sig_result = _solana_rpc("getSignaturesForAddress", [
            token_account,
            params,
        ])
        signatures = sig_result.get("result", [])

        # 새 signature가 있으면 가장 최신 것을 기록
        # (signatures는 최신순 정렬이므로 첫 번째가 가장 최신)
        if signatures:
            _last_known_signature = signatures[0].get("signature")

        return signatures

    except Exception as e:
        logger.error(f"Solana getSignaturesForAddress error: {e}")
        return []


def fetch_solana_usdt_transfers(token_account: str, limit: int = 15) -> list[dict]:
    """
    [개선 8] Solana USDT 입금 내역 조회 (최적화)

    변경점:
    - _fetch_new_signatures()로 새 tx만 가져옴 (중복 조회 제거)
    - getTransaction 호출 사이에 딜레이 (_solana_rpc 내부에서 처리)
    - 이미 알려진 tx는 건너뜀
    """
    signatures = _fetch_new_signatures(token_account, limit=limit)

    if not signatures:
        return []

    # 새 signature 중 아직 처리 안 한 것만 필터링
    new_sigs = []
    for sig_info in signatures:
        sig = sig_info.get("signature")
        if not sig or sig_info.get("err"):
            continue
        key = f"Solana:{sig}"
        if _is_known_tx(key):
            continue
        new_sigs.append(sig)

    if not new_sigs:
        logger.debug("No new signatures to process")
        return []

    logger.info(f"Found {len(new_sigs)} new signatures to check")

    # [개선 9] 새 tx만 getTransaction 호출 (딜레이는 _solana_rpc 내부에서 처리)
    transfers = []
    for sig in new_sigs:
        try:
            tx_result = _solana_rpc("getTransaction", [
                sig,
                {"encoding": "jsonParsed", "maxSupportedTransactionVersion": 0},
            ])
            tx = tx_result.get("result")
            if not tx:
                # tx가 없으면 이미 알려진 것으로 표시 (다음에 다시 조회 안 함)
                _add_known_tx(f"Solana:{sig}")
                continue

            # SPL 토큰 transfer 명령어 파싱
            instructions = (
                tx.get("transaction", {})
                .get("message", {})
                .get("instructions", [])
            )
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
            # 에러 발생한 tx도 기록하여 다음에 다시 시도하지 않음
            # (단, 429 에러는 _solana_rpc 내부에서 재시도하므로 여기 도달 시 진짜 실패)
            _add_known_tx(f"Solana:{sig}")
            continue

    return transfers


def _process_solana_txs(transfers: list[dict]):
    """감지된 입금을 DB와 매칭하고 처리 완료 표시"""
    for t in transfers:
        key = f"Solana:{t['tx_hash']}"
        if _is_known_tx(key):
            continue

        amount = t["amount"]
        if amount <= 0:
            _add_known_tx(key)
            continue

        logger.info(f"[Solana] USDT deposit: {amount} from {t['sender']} (tx: {t['tx_hash'][:16]}...)")
        _match_deposit_to_request(
            amount=amount,
            sender=t["sender"],
            tx_hash=t["tx_hash"],
            chain="Solana",
        )
        _add_known_tx(key)


# ──────────────────────────────────────────────
# 통합 폴링
# ──────────────────────────────────────────────
def _init_known_txs():
    """
    [개선 10] 서버 시작 시 기존 트랜잭션 등록 (중복 알림 방지)

    기존 문제: 시작할 때 50개 signature를 가져와서 각각 getTransaction 호출
    → 서버 시작마다 최대 52회 RPC 호출 → 429 위험

    개선: signature 목록만 가져와서 "이미 처리한 것"으로 등록
    → getTransaction 호출 0회 (2회만 사용: getTokenAccountsByOwner + getSignaturesForAddress)
    → 시작 직후에는 새 tx만 감지
    """
    global _solana_token_account, _last_known_signature

    solana_addr = settings.USDT_ADMIN_ADDRESS_SOLANA
    if not solana_addr:
        return

    try:
        _solana_token_account = get_solana_usdt_token_account(solana_addr)
        if not _solana_token_account:
            return

        # signature 목록만 가져오기 (getTransaction 호출 안 함!)
        sig_result = _solana_rpc("getSignaturesForAddress", [
            _solana_token_account,
            {"limit": 30},
        ])
        signatures = sig_result.get("result", [])

        # 모든 기존 signature를 "이미 처리한 것"으로 등록
        for sig_info in signatures:
            sig = sig_info.get("signature")
            if sig:
                _add_known_tx(f"Solana:{sig}")

        # 가장 최신 signature 기록 → 다음 폴링부터 이후만 조회
        if signatures:
            _last_known_signature = signatures[0].get("signature")

        logger.info(
            f"Solana init: {len(signatures)} existing signatures marked as known "
            f"(RPC calls: 2, getTransaction: 0)"
        )

    except Exception as e:
        logger.error(f"Solana init error: {e}")


def poll_wallet_once():
    """
    [개선 11] 1회 폴링: Solana USDT 입금 감지

    변경점:
    - 에러 발생 시 _consecutive_errors 증가 → 폴링 간격 자동 증가
    - 성공 시 에러 카운터 초기화
    """
    global _solana_token_account, _consecutive_errors

    solana_addr = settings.USDT_ADMIN_ADDRESS_SOLANA
    if not solana_addr:
        return

    # 토큰 계정 캐시
    if not _solana_token_account:
        _solana_token_account = get_solana_usdt_token_account(solana_addr)

    if _solana_token_account:
        transfers = fetch_solana_usdt_transfers(_solana_token_account)
        _process_solana_txs(transfers)
        # 성공 시 에러 카운터 초기화
        _consecutive_errors = 0


def wallet_monitor_loop():
    """
    [개선 12] 백그라운드 스레드: 주기적으로 Solana 폴링

    변경점:
    - 기본 폴링 간격: 90초 (기존 60초)
    - 에러 발생 시 간격 자동 증가 (90→180→360초, 최대 600초)
    - 연속 성공 시 기본 간격으로 복귀
    """
    global _consecutive_errors

    base_interval = settings.WALLET_POLL_INTERVAL_SECONDS or 90
    logger.info(f"Wallet monitor started (Solana, base polling every {base_interval}s)")

    _init_known_txs()

    while True:
        try:
            poll_wallet_once()
        except Exception as e:
            _consecutive_errors += 1
            logger.error(f"Wallet monitor error (consecutive: {_consecutive_errors}): {e}")

        # [개선 13] 에러 시 폴링 간격 자동 증가 (adaptive interval)
        # 연속 에러가 많을수록 대기 시간 증가 → RPC 서버 부담 감소
        if _consecutive_errors > 0:
            interval = min(base_interval * (2 ** _consecutive_errors), 600)
            logger.info(f"Increased polling interval to {interval}s (errors: {_consecutive_errors})")
        else:
            interval = base_interval

        time.sleep(interval)
