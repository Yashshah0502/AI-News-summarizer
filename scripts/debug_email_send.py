#!/usr/bin/env python3
"""Debug email sending with detailed SMTP logs"""
import os
import sys
import smtplib
import ssl
from dotenv import load_dotenv
from app.services.email_renderer import render_digest
from app.services.email_message_builder import build_email_message

def main():
    load_dotenv()

    if len(sys.argv) < 2:
        print("Usage: python -m scripts.debug_email_send <digest_id>")
        sys.exit(1)

    digest_id = int(sys.argv[1])

    # Render email
    print("Rendering digest...")
    subject, text_body, html_body = render_digest(digest_id)

    from_email = os.environ["FROM_EMAIL"]
    to_email = os.environ["TO_EMAIL"]

    print(f"\n=== Email Details ===")
    print(f"From: {from_email}")
    print(f"To: {to_email}")
    print(f"Subject: {subject}")
    print(f"Text body size: {len(text_body)} bytes")
    print(f"HTML body size: {len(html_body)} bytes")

    # Build message
    msg = build_email_message(
        subject=subject,
        text_body=text_body,
        html_body=html_body,
        from_email=from_email,
        to_email=to_email,
    )

    # Get SMTP config
    host = os.environ["SMTP_HOST"]
    port = int(os.environ.get("SMTP_PORT", "465"))
    user = os.environ["SMTP_USER"]
    pwd = os.environ["SMTP_PASS"]

    print(f"\n=== SMTP Configuration ===")
    print(f"Host: {host}")
    print(f"Port: {port}")
    print(f"User: {user}")

    # Send with debugging enabled
    print(f"\n=== Sending Email ===")
    try:
        if port == 465:
            context = ssl.create_default_context()
            with smtplib.SMTP_SSL(host, port, context=context) as server:
                server.set_debuglevel(1)  # Enable debug output
                print("\nLogging in...")
                server.login(user, pwd)
                print("\nSending message...")
                result = server.send_message(msg)
                print(f"\n=== Send Result ===")
                print(f"Refused recipients: {result}")
                if not result:
                    print("✓ Email accepted by SMTP server for all recipients")
                else:
                    print(f"✗ Some recipients were refused: {result}")
        else:
            with smtplib.SMTP(host, port) as server:
                server.set_debuglevel(1)
                server.starttls(context=ssl.create_default_context())
                print("\nLogging in...")
                server.login(user, pwd)
                print("\nSending message...")
                result = server.send_message(msg)
                print(f"\n=== Send Result ===")
                print(f"Refused recipients: {result}")
                if not result:
                    print("✓ Email accepted by SMTP server for all recipients")
                else:
                    print(f"✗ Some recipients were refused: {result}")

        print("\n✓ Email sent successfully!")
        print("\nNote: 'Accepted by SMTP server' means Gmail received it, but:")
        print("  - It might still be in spam/promotions")
        print("  - There might be a delivery delay")
        print("  - The recipient server might reject it later")

    except smtplib.SMTPException as e:
        print(f"\n✗ SMTP Error: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n✗ Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
