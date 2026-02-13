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
    """Notify admins that a new deposit request was created."""
    message = f"""
<b>New Deposit Request</b>

User: {user_email}
Amount: {amount} USDT
JOY: {joy_amount:,} JOY
Chain: {chain}
JOY wallet: <code>{wallet_address or '-'}</code>
Request ID: #{deposit_id}

Time: {now_kst()}
"""
    return send_telegram_notification(message)


def notify_deposit_approved(user_email: str, amount: float, joy_amount: int, deposit_id: int):
    """Notify admins that deposit approval is complete."""
    message = f"""
<b>Deposit Approved</b>

User: {user_email}
Amount: {amount} USDT
JOY: {joy_amount:,} JOY
Request ID: #{deposit_id}

Please send JOY to the user.
"""
    return send_telegram_notification(message)


def notify_deposit_detected(amount: float, sender: str, tx_hash: str, chain: str = "Polygon"):
    """Notify that an on-chain USDT transfer was detected."""
    explorer_urls = {
        "Polygon": f"https://polygonscan.com/tx/{tx_hash}",
        "Ethereum": f"https://etherscan.io/tx/{tx_hash}",
        "TRON": f"https://tronscan.org/#/transaction/{tx_hash}",
    }
    explorer_url = explorer_urls.get(chain, f"https://polygonscan.com/tx/{tx_hash}")
    message = f"""
<b>USDT Deposit Detected</b>

Chain: {chain}
Amount: {amount} USDT
From: <code>{sender}</code>
TX: <a href=\"{explorer_url}\">{tx_hash[:16]}...</a>

Detected at: {now_kst()}

Please verify in the admin dashboard.
"""
    return send_telegram_notification(message)
