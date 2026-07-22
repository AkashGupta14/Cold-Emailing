#!/usr/bin/env python3
"""Parse a Cold_Emails_<date>.md queue file into emails/<date>/.

Usage:
    python tools/parse_queue.py <path-to-queue.md> <YYYY-MM-DD>

The queue file format (repeat per set):

    SET 1
    Subject: <subject line>
    Body:
    <one or more lines of body text>
    BCC:
    a@example.com
    b@example.com

Optional per-set lines (place before "Body:"): From name:, Reply-to:, To:
Each SET becomes one separate email. The resume is auto-attached by
send_emails.py, so it is NOT listed here.
"""
from __future__ import annotations

import pathlib
import re
import sys

import yaml

OPTIONAL = {
    "from name:": "from_name",
    "reply-to:": "reply_to",
    "to:": "to",
}


def main() -> int:
    if len(sys.argv) != 3:
        sys.exit("Usage: python tools/parse_queue.py <queue.md> <YYYY-MM-DD>")
    src = pathlib.Path(sys.argv[1])
    date = sys.argv[2]
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", date):
        sys.exit("Date must be YYYY-MM-DD")

    repo_root = pathlib.Path(__file__).resolve().parent.parent
    out = repo_root / "emails" / date
    out.mkdir(parents=True, exist_ok=True)

    sets, cur, section = [], None, None
    for line in src.read_text(encoding="utf-8").splitlines():
        if re.match(r"^SET\b", line.strip()):
            if cur:
                sets.append(cur)
            cur = {"subject": "", "body": [], "bcc": [], "extra": {}}
            section = None
            continue
        if cur is None:
            continue
        low = line.strip().lower()
        if low.startswith("subject:"):
            cur["subject"] = line.split(":", 1)[1].strip()
            section = None
        elif low == "body:":
            section = "body"
        elif low == "bcc:":
            section = "bcc"
        elif any(low.startswith(k) for k in OPTIONAL):
            key = next(OPTIONAL[k] for k in OPTIONAL if low.startswith(k))
            cur["extra"][key] = line.split(":", 1)[1].strip()
        elif section == "body":
            cur["body"].append(line)
        elif section == "bcc" and line.strip():
            for addr in re.split(r"[,\s]+", line.strip()):
                if addr:
                    cur["bcc"].append(addr)
    if cur:
        sets.append(cur)

    def trim(block: list[str]) -> str:
        while block and not block[0].strip():
            block.pop(0)
        while block and not block[-1].strip():
            block.pop()
        return "\n".join(block) + "\n"

    emails = []
    for i, s in enumerate(sets, 1):
        fname = f"body{i}.txt"
        (out / fname).write_text(trim(s["body"]), encoding="utf-8")
        entry = {"subject": s["subject"], "body": fname}
        entry.update(s["extra"])
        entry["bcc"] = s["bcc"]
        emails.append(entry)

    with (out / "campaign.yml").open("w", encoding="utf-8") as f:
        f.write(f"# Generated from {src.name}\n")
        yaml.safe_dump({"emails": emails}, f, sort_keys=False,
                       allow_unicode=True, width=4096)

    print(f"Parsed {len(sets)} set(s) into {out}")
    for i, s in enumerate(sets, 1):
        print(f"  SET {i}: bcc={len(s['bcc'])}  subject={s['subject'][:60]!r}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
