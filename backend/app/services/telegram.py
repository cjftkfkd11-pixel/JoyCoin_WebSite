# backend/app/services/telegram.py
import requests
from datetime import datetime
from app.core.config import settings


def send_telegram_notification(message: str) -> bool:
    """
    텔레그램 봇으로 알림 전송

    Args:
        message: 전송할 메시지

    Returns:
        bool: 전송 성공 여부
    """
    if not settings.TELEGRAM_BOT_TOKEN or not settings.TELEGRAM_CHAT_ID:
        print("⚠️ 텔레그램 설정이 없습니다. 알림을 전송하지 않습니다.")
        return False

    url = f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/sendMessage"

    payload = {
        "chat_id": settings.TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "HTML"
    }

    try:
        response = requests.post(url, json=payload, timeout=10)
        response.raise_for_status()
        print(f"✅ 텔레그램 알림 전송 성공")
        return True
    except Exception as e:
        print(f"❌ 텔레그램 알림 전송 실패: {e}")
        return False


def notify_new_deposit_request(user_email: str, amount: float, chain: str, deposit_id: int):
    """
    새로운 입금 요청 알림
    """
    message = f"""
🔔 <b>새로운 입금 요청</b>

👤 유저: {user_email}
💰 금액: {amount} USDT
🌐 네트워크: {chain}
🆔 요청 ID: #{deposit_id}

⏰ 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""
    return send_telegram_notification(message)


def notify_deposit_approved(user_email: str, amount: float, deposit_id: int):
    """
    입금 승인 완료 알림
    """
    message = f"""
✅ <b>입금 승인 완료</b>

👤 유저: {user_email}
💰 금액: {amount} USDT
🆔 요청 ID: #{deposit_id}

사용자 잔액에 충전되었습니다.
"""
    return send_telegram_notification(message)
