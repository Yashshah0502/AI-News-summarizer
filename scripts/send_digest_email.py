# scripts/send_digest_email.py
import os, sys
from dotenv import load_dotenv
from app.services.email_renderer import render_digest
from app.services.email_message_builder import build_email_message
from app.services.email_sender import send_email

def main():
    load_dotenv()
    digest_id = int(sys.argv[1])
    subject, text_body, html_body = render_digest(digest_id)

    from_email = os.environ["FROM_EMAIL"]
    to_email = os.environ["TO_EMAIL"]

    print(f"From: {from_email}")
    print(f"To: {to_email}")
    print(f"Subject: {subject}")

    msg = build_email_message(
        subject=subject,
        text_body=text_body,
        html_body=html_body,
        from_email=from_email,
        to_email=to_email,
    )
    send_email(msg)
    print(f"sent digest_id={digest_id}")

if __name__ == "__main__":
    main()
