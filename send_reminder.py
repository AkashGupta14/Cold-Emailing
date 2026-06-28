#!/usr/bin/env python3
"""Send a daily reminder email to yourself (no body, no attachment).

Runs on its own schedule (weekday mornings) to remind you to upload the day's
cold-emailing file. Reuses the same Gmail credentials as send_emails.py:
  GMAIL_USER, GMAIL_APP_PASSWORD
"""

from __future__ import annotations

import os
import smtplib
import sys
from email.message import EmailMessage

SMTP_HOST = "smtp.gmail.com"
SMTP_PORT = 465  # SSL

SUBJECT = "UPLOAD THE COLD EMAILING FILE FOR TODAY"


def main() -> int:
    sender = os.environ.get("GMAIL_USER", "").strip()
    password = os.environ.get("GMAIL_APP_PASSWORD", "").strip()
    if not sender or not password:
        sys.exit("GMAIL_USER and GMAIL_APP_PASSWORD must be set (GitHub secrets).")

    # Send to yourself.
    recipient = os.environ.get("REMINDER_TO", sender).strip() or sender

    msg = EmailMessage()
    msg["From"] = sender
    msg["To"] = recipient
    msg["Subject"] = SUBJECT
    msg.set_content("")  # no body

    with smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT) as server:
        server.login(sender, password)
        server.send_message(msg)

    print(f"Reminder sent to {recipient}: '{SUBJECT}'")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
