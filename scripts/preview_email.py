# scripts/preview_email.py
import os
import sys
from dotenv import load_dotenv

from app.services.email_renderer import render_digest
from app.services.email_message_builder import build_email_message


def main():
    load_dotenv()
    digest_id = int(sys.argv[1])

    subject, text_body, html_body = render_digest(digest_id)

    msg = build_email_message(
        subject=subject,
        text_body=text_body,
        html_body=html_body,
        from_email=os.getenv("FROM_EMAIL", "you@example.com"),
        to_email=os.getenv("TO_EMAIL", "you@example.com"),
    )

    # Print quick preview
    print("SUBJECT:", subject)
    print("\n--- TEXT PREVIEW ---\n")
    print(text_body[:1500])

    # Save .eml so you can open in Mail
    out_path = f"digest_{digest_id}.eml"
    with open(out_path, "wb") as f:
        f.write(msg.as_bytes())
    print(f"\nSaved: {out_path}")


if __name__ == "__main__":
    main()
