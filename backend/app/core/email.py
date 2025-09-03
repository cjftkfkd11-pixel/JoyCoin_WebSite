import os, logging

SENDER = os.getenv("EMAIL_SENDER", "noreply@joycoin.local")
logger = logging.getLogger("email")


def send_email(to: str, subject: str, body: str):
    # 개발환경: 실제 발송 대신 로그로 대체
    logger.warning("[DEV-EMAIL] To=%s | Subject=%s\n%s", to, subject, body)
