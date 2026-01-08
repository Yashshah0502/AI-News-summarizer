# app/services/email_sender.py
import os
import smtplib
import ssl
from email.message import EmailMessage

def send_email(msg: EmailMessage) -> None:
    host = os.environ["SMTP_HOST"]
    port = int(os.environ.get("SMTP_PORT", "465"))
    user = os.environ["SMTP_USER"]
    pwd = os.environ["SMTP_PASS"]

    if port == 465:
        context = ssl.create_default_context()
        with smtplib.SMTP_SSL(host, port, context=context) as server:
            server.login(user, pwd)
            server.send_message(msg)  # sends to To/Cc/Bcc headers :contentReference[oaicite:1]{index=1}
    else:
        # STARTTLS (commonly 587)
        with smtplib.SMTP(host, port) as server:
            server.starttls(context=ssl.create_default_context())
            server.login(user, pwd)
            server.send_message(msg)
