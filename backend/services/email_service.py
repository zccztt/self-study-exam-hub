# -*- coding: utf-8 -*-
"""Transactional email helpers."""

from email.message import EmailMessage
import smtplib
from urllib.parse import quote

from backend.config import settings


def send_password_reset_email(recipient: str, token: str) -> None:
    if not settings.SMTP_HOST:
        raise RuntimeError("SMTP_HOST is not configured.")
    reset_url = f"{settings.FRONTEND_URL.rstrip('/')}/auth?reset_token={quote(token)}"
    message = EmailMessage()
    message["Subject"] = "自考备考中枢密码重置"
    message["From"] = settings.SMTP_FROM_EMAIL or settings.SMTP_USERNAME or "noreply@localhost"
    message["To"] = recipient
    message.set_content(
        "你正在重置自考备考中枢账号密码。\n\n"
        f"请在 {settings.PASSWORD_RESET_EXPIRE_MINUTES} 分钟内打开以下链接：\n{reset_url}\n\n"
        "如果不是你本人操作，请忽略此邮件。"
    )
    with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=10) as client:
        if settings.SMTP_USE_TLS:
            client.starttls()
        if settings.SMTP_USERNAME:
            client.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD or "")
        client.send_message(message)
