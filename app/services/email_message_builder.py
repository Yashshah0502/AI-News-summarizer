# app/services/email_message_builder.py
from __future__ import annotations

from email.message import EmailMessage


def build_email_message(subject: str, text_body: str, html_body: str, from_email: str, to_email: str) -> EmailMessage:
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = from_email
    msg["To"] = to_email

    msg.set_content(text_body)
    msg.add_alternative(html_body, subtype="html")  # creates multipart/alternative :contentReference[oaicite:2]{index=2}
    return msg
