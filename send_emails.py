#!/usr/bin/env python3
"""Send the day's cold emails via Gmail SMTP.

Design goals:
- "Freshness by folder": we only send emails found in emails/<today>/campaign.yml.
  If today's folder does not exist, we exit cleanly WITHOUT sending anything.
  This guarantees stale/yesterday content is never sent automatically.
- Each campaign.yml can contain several emails (you send ~5-10/day), and each
  email has its own Bcc list (~4 recipients), body file, and attachments.

Credentials come from environment variables (GitHub Actions secrets):
  GMAIL_USER           -> your full Gmail address (the sender / SMTP login)
  GMAIL_APP_PASSWORD   -> a Google "App Password" (NOT your normal password)

Optional environment variables:
  TIMEZONE             -> IANA tz used to decide what "today" is (default Asia/Kolkata)
  EMAILS_DIR           -> root folder holding dated subfolders (default "emails")
  DRY_RUN              -> "1"/"true" to build messages and log, but not actually send
"""

from __future__ import annotations

import mimetypes
import os
import smtplib
import sys
from datetime import datetime
from email.message import EmailMessage
from email.utils import formataddr
from pathlib import Path
from zoneinfo import ZoneInfo

try:
    import yaml
except ImportError:
    sys.exit("Missing dependency: PyYAML. Run `pip install -r requirements.txt`.")

SMTP_HOST = "smtp.gmail.com"
SMTP_PORT = 465  # SSL


def env_flag(name: str) -> bool:
    return os.environ.get(name, "").strip().lower() in {"1", "true", "yes", "on"}


def today_folder(emails_dir: Path, tz_name: str) -> tuple[str, Path]:
    """Return (date_string, path) for today's campaign folder."""
    try:
        tz = ZoneInfo(tz_name)
    except Exception:
        print(f"WARNING: unknown TIMEZONE '{tz_name}', falling back to UTC.")
        tz = ZoneInfo("UTC")
    date_str = datetime.now(tz).strftime("%Y-%m-%d")
    return date_str, emails_dir / date_str


def as_list(value) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [value]
    return [str(v) for v in value]


def load_body(folder: Path, body_file: str) -> tuple[str, bool]:
    """Return (content, is_html). .html -> HTML, everything else -> plain text."""
    path = folder / body_file
    if not path.is_file():
        raise FileNotFoundError(f"body file not found: {path}")
    content = path.read_text(encoding="utf-8")
    return content, path.suffix.lower() in {".html", ".htm"}


def attach_files(msg: EmailMessage, folder: Path, attachments: list[str]) -> None:
    for name in attachments:
        path = folder / name
        if not path.is_file():
            raise FileNotFoundError(f"attachment not found: {path}")
        ctype, encoding = mimetypes.guess_type(str(path))
        if ctype is None or encoding is not None:
            ctype = "application/octet-stream"
        maintype, subtype = ctype.split("/", 1)
        msg.add_attachment(
            path.read_bytes(),
            maintype=maintype,
            subtype=subtype,
            filename=path.name,
        )


def build_message(sender: str, item: dict, folder: Path) -> tuple[EmailMessage, list[str]]:
    """Build one EmailMessage. Returns (msg, all_envelope_recipients)."""
    subject = item.get("subject")
    if not subject:
        raise ValueError("email entry is missing 'subject'")

    bcc = as_list(item.get("bcc"))
    to = as_list(item.get("to")) or [sender]  # default: send To yourself
    cc = as_list(item.get("cc"))

    if not bcc and not item.get("to"):
        raise ValueError(f"'{subject}': no recipients (need 'bcc' and/or 'to')")

    body_file = item.get("body")
    if not body_file:
        raise ValueError(f"'{subject}': missing 'body' file")
    content, is_html = load_body(folder, body_file)

    msg = EmailMessage()
    from_name = item.get("from_name")
    msg["From"] = formataddr((from_name, sender)) if from_name else sender
    msg["To"] = ", ".join(to)
    if cc:
        msg["Cc"] = ", ".join(cc)
    # NOTE: Bcc is intentionally NOT added as a header. Recipients are passed
    # only in the SMTP envelope below, so Bcc addresses stay hidden.
    msg["Subject"] = subject
    reply_to = item.get("reply_to")
    if reply_to:
        msg["Reply-To"] = reply_to

    if is_html:
        msg.set_content("This email requires an HTML-capable client.")
        msg.add_alternative(content, subtype="html")
    else:
        msg.set_content(content)

    attach_files(msg, folder, as_list(item.get("attachments")))

    envelope = to + cc + bcc
    return msg, envelope


def main() -> int:
    sender = os.environ.get("GMAIL_USER", "").strip()
    password = os.environ.get("GMAIL_APP_PASSWORD", "").strip()
    emails_dir = Path(os.environ.get("EMAILS_DIR", "emails"))
    tz_name = os.environ.get("TIMEZONE", "Asia/Kolkata")
    dry_run = env_flag("DRY_RUN")

    date_str, folder = today_folder(emails_dir, tz_name)
    campaign = folder / "campaign.yml"

    if not campaign.is_file():
        print(f"No campaign for today ({date_str}) at {campaign}.")
        print("Nothing to send. Exiting cleanly so no stale emails go out.")
        return 0

    if not sender or not password:
        sys.exit("GMAIL_USER and GMAIL_APP_PASSWORD must be set (GitHub secrets).")

    data = yaml.safe_load(campaign.read_text(encoding="utf-8")) or {}
    items = data.get("emails", [])
    if not isinstance(items, list) or not items:
        print(f"campaign.yml for {date_str} has no 'emails:' list. Nothing to send.")
        return 0

    print(f"Found {len(items)} email(s) for {date_str}. dry_run={dry_run}")

    # Build everything first so a config error stops us BEFORE any send.
    built: list[tuple[EmailMessage, list[str], str]] = []
    for idx, item in enumerate(items, 1):
        try:
            msg, envelope = build_message(sender, item, folder)
        except Exception as exc:  # noqa: BLE001
            sys.exit(f"Error in email #{idx}: {exc}")
        built.append((msg, envelope, item.get("subject", "")))
        print(f"  #{idx} '{msg['Subject']}' -> {len(envelope)} recipient(s)")

    if dry_run:
        print("DRY_RUN set: not sending.")
        return 0

    failures = 0
    with smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT) as server:
        server.login(sender, password)
        for idx, (msg, envelope, subject) in enumerate(built, 1):
            try:
                server.send_message(msg, from_addr=sender, to_addrs=envelope)
                print(f"  sent #{idx}: '{subject}' to {len(envelope)} recipient(s)")
            except Exception as exc:  # noqa: BLE001
                failures += 1
                print(f"  FAILED #{idx}: '{subject}': {exc}")

    if failures:
        print(f"{failures} email(s) failed.")
        return 1
    print("All emails sent successfully.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
