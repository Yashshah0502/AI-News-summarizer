# scripts/send_test_email.py
import os
from dotenv import load_dotenv
from email.message import EmailMessage
from app.services.email_sender import send_email

def main():
    load_dotenv()

    msg = EmailMessage()
    msg["Subject"] = "SMTP test"
    msg["From"] = os.environ["FROM_EMAIL"]
    msg["To"] = os.environ["TO_EMAIL"]
    msg.set_content("hello from AI-News-summarizer")

    send_email(msg)
    print("sent")

if __name__ == "__main__":
    main()
