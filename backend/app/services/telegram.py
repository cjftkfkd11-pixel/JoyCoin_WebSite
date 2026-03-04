# backend/app/services/telegram.py
from datetime import datetime, timedelta, timezone

import requests

from app.core.config import settings

KST = timezone(timedelta(hours=9))


def now_kst() -> str:
    return datetime.now(KST).strftime("%Y-%m-%d %H:%M:%S")


def send_telegram_notification(message: str) -> bool:
    """Send a Telegram bot notification."""
    if not settings.TELEGRAM_BOT_TOKEN or not settings.TELEGRAM_CHAT_ID:
        print("Telegram bot settings are missing. Skipping notification.")
        return False

    url = f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": settings.TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "HTML",
    }

    try:
        response = requests.post(url, json=payload, timeout=10)
        response.raise_for_status()
        print("Telegram notification sent")
        return True
    except Exception as e:
        print(f"Telegram notification failed: {e}")
        return False


def notify_new_deposit_request(
    user_email: str,
    amount: float,
    joy_amount: int,
    chain: str,
    deposit_id: int,
    wallet_address: str | None = None,
):
    """새 입금 요청 알림"""
    message = f"""
<b>📥 새 입금 요청 - 승인불필요</b>

사용자: {user_email}
금액: {amount} USDT
JOY 수량: {joy_amount:,} JOY
체인: {chain}
JOY 수령 지갑: <code>{wallet_address or '미등록'}</code>
요청 ID: #{deposit_id}

시간: {now_kst()}
"""
    return send_telegram_notification(message)


def notify_deposit_approved(user_email: str, amount: float, joy_amount: int, deposit_id: int):
    """입금 승인 완료 알림"""
    message = f"""
<b>✅ 입금 승인 완료</b>

사용자: {user_email}
금액: {amount} USDT
JOY 수량: {joy_amount:,} JOY
요청 ID: #{deposit_id}

사용자에게 JOY를 전송해 주세요.
"""
    return send_telegram_notification(message)


def notify_deposit_detected(amount: float, sender: str, tx_hash: str, chain: str = "Polygon"):
    """온체인 USDT 입금 감지 알림 (미매칭 시)"""
    explorer_urls = {
        "Polygon": f"https://polygonscan.com/tx/{tx_hash}",
        "Ethereum": f"https://etherscan.io/tx/{tx_hash}",
        "TRON": f"https://tronscan.org/#/transaction/{tx_hash}",
    }
    explorer_url = explorer_urls.get(chain, f"https://polygonscan.com/tx/{tx_hash}")
    message = f"""
<b>🔔 USDT 입금 감지</b>

체인: {chain}
금액: {amount} USDT
보낸 주소: <code>{sender}</code>
TX: <a href=\"{explorer_url}\">{tx_hash[:16]}...</a>

감지 시간: {now_kst()}

관리자 대시보드에서 확인해 주세요.
"""
    return send_telegram_notification(message)


def _explorer_url(chain: str, tx_hash: str) -> str:
    urls = {
        "Polygon": f"https://polygonscan.com/tx/{tx_hash}",
        "Ethereum": f"https://etherscan.io/tx/{tx_hash}",
        "TRON": f"https://tronscan.org/#/transaction/{tx_hash}",
    }
    return urls.get(chain, tx_hash)


def notify_deposit_matched(
    user_email: str, expected: float, actual: float, joy_amount: int,
    chain: str, tx_hash: str, deposit_id: int,
):
    """입금 자동 매칭 성공 알림"""
    url = _explorer_url(chain, tx_hash)
    message = f"""
<b>✅ 입금 자동 매칭</b>

사용자: {user_email}
예상 금액: {expected} USDT
실제 입금: {actual} USDT
JOY 수량: {joy_amount:,} JOY
체인: {chain}
TX: <a href=\"{url}\">{tx_hash[:16]}...</a>
요청 ID: #{deposit_id}

시간: {now_kst()}
"""
    return send_telegram_notification(message)


def notify_deposit_underpaid(
    user_email: str, expected: float, actual: float,
    original_joy: int, recalculated_joy: int,
    chain: str, tx_hash: str, deposit_id: int,
):
    """부족 입금 알림"""
    url = _explorer_url(chain, tx_hash)
    message = f"""
<b>⚠️ 부족 입금 감지</b>

사용자: {user_email}
예상 금액: {expected} USDT
실제 입금: {actual} USDT (부족!)
원래 JOY: {original_joy:,} → 재계산: {recalculated_joy:,} JOY
체인: {chain}
TX: <a href=\"{url}\">{tx_hash[:16]}...</a>
요청 ID: #{deposit_id}

관리자 확인이 필요합니다.
시간: {now_kst()}
"""
    return send_telegram_notification(message)


def notify_withdrawal_request(
    user_email: str,
    amount: int,
    wallet_address: str,
    chain: str,
    withdrawal_id: int,
):
    """JOY 출금 요청 알림"""
    message = f"""
<b>💸 JOY 출금 요청</b>

사용자: {user_email}
출금 수량: {amount:,} JOY
수령 지갑: <code>{wallet_address}</code>
체인: {chain}
요청 ID: #{withdrawal_id}

시간: {now_kst()}

관리자 대시보드에서 처리해 주세요.
"""
    return send_telegram_notification(message)


def notify_withdrawal_approved(
    user_email: str,
    amount: int,
    wallet_address: str,
    chain: str,
    withdrawal_id: int,
):
    """JOY 출금 승인 알림"""
    message = f"""
<b>✅ JOY 출금 승인 완료</b>

사용자: {user_email}
출금 수량: {amount:,} JOY
수령 지갑: <code>{wallet_address}</code>
체인: {chain}
요청 ID: #{withdrawal_id}

시간: {now_kst()}
"""
    return send_telegram_notification(message)


def notify_deposit_unmatched(amount: float, sender: str, tx_hash: str, chain: str):
    """매칭 실패 알림 (pending 요청 없음)"""
    url = _explorer_url(chain, tx_hash)
    message = f"""
<b>❓ 미매칭 입금 감지</b>

체인: {chain}
금액: {amount} USDT
보낸 주소: <code>{sender}</code>
TX: <a href=\"{url}\">{tx_hash[:16]}...</a>

매칭되는 입금 요청을 찾지 못했습니다.
관리자 대시보드에서 수동 확인해 주세요.

시간: {now_kst()}
"""
    return send_telegram_notification(message)
