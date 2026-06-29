# Cold Emailing

Automated daily cold-email sender. You drop a day's emails into a dated folder;
GitHub Actions sends them every weekday morning via Gmail. Your resume is
attached to every email automatically.

> This README is the **single source of truth**. You (or an assistant in any new
> session) can read this top-to-bottom and run the whole thing — no prior context
> needed.

- **Repo:** `AkashGupta14/Cold-Emailing` (private)
- **Sender:** Gmail SMTP, account `akashgupta14902@gmail.com`
- **Send time:** weekdays at **11:11 AM IST** (`41 5 * * 1-5` UTC)
- **Reminder:** weekdays at **9:30 AM IST** you get an email titled
  "UPLOAD THE COLD EMAILING FILE FOR TODAY"

---

## 1. How it works (the core idea)

The send workflow only looks at **one folder: `emails/<today>/`** where `<today>`
is the date in **Asia/Kolkata** (e.g. `emails/2026-06-29/`).

- If that folder + its `campaign.yml` exist → it sends every email defined there.
- If it does **not** exist → it sends **nothing** and exits cleanly.

This is the safety mechanism: **no folder for today = no emails.** Stale or
yesterday's content can never go out by accident. To send on a given day, you
just create that day's folder before 11:11 AM IST.

Each entry in `campaign.yml` is **one separate email** ("set"): its own subject,
its own body, its own BCC list. Sets are never merged. The resume
(`assets/AkashGupta_Resume.pdf`) is attached to every one automatically.

---

## 2. Repository structure

```
Cold Emailing/
├── README.md                       # this file — full reference
├── send_emails.py                  # main sender (reads emails/<today>/)
├── send_reminder.py                # 9:30 AM reminder email
├── requirements.txt                # PyYAML
├── assets/
│   └── AkashGupta_Resume.pdf       # auto-attached to EVERY email
├── tools/
│   └── parse_queue.py              # turns a Cold_Emails_<date>.md into emails/<date>/
├── emails/
│   ├── _example/                   # template (never sent — name isn't a date)
│   │   ├── campaign.yml
│   │   ├── body1.html
│   │   ├── body2.html
│   │   └── body3.html
│   └── 2026-06-29/                 # a real day's folder (sends on that date)
│       ├── campaign.yml
│       ├── body1.txt
│       └── ...
└── .github/workflows/
    ├── send-emails.yml             # cron 11:11 AM IST weekdays + manual run
    └── reminder.yml                # cron 9:30 AM IST weekdays + manual run
```

---

## 3. `campaign.yml` reference

A `campaign.yml` is a list under `emails:`. One entry = one email.

```yaml
emails:
  - subject: "Subject for set 1"
    body: "body1.txt"          # a file in THIS dated folder (.html → HTML, else plain text)
    bcc:                       # 3-4 hidden recipients (hidden from each other)
      - "a@example.com"
      - "b@example.com"
    # optional fields:
    to: "someone@x.com"        # visible To; defaults to yourself if omitted
    cc: ["c@x.com"]            # visible Cc
    from_name: "Akash Gupta"   # display name on the From header
    reply_to: "you@gmail.com"  # Reply-To address
    attachments: ["extra.pdf"] # EXTRA files in this folder (resume is already auto-attached)

  - subject: "Subject for set 2"
    body: "body2.txt"
    bcc:
      - "d@example.com"
```

| field | required | notes |
|-------|----------|-------|
| `subject` | yes | subject line |
| `body` | yes | filename in the dated folder; `.html`/`.htm` → HTML, anything else → plain text |
| `bcc` | yes* | hidden recipients (kept hidden from each other) |
| `to` | no | visible primary recipient; defaults to yourself |
| `cc` | no | visible CC list |
| `from_name` | no | display name shown to recipients |
| `reply_to` | no | where replies go |
| `attachments` | no | extra files in the folder, **in addition to** the auto-attached resume |

\* each entry needs `bcc` and/or `to`.

**Auto-attached resume:** `assets/AkashGupta_Resume.pdf` is added to every email,
configured by the `DEFAULT_ATTACHMENTS` list at the top of `send_emails.py`. To
swap the resume, replace that file. To always attach more files, add them to
`DEFAULT_ATTACHMENTS`.

---

## 4. Adding a day's emails — from any session

### First time on a new machine
```bash
git clone https://github.com/AkashGupta14/Cold-Emailing.git "Cold Emailing"
cd "Cold Emailing"
# Requires the gh CLI logged in (gh auth login) OR git push access to the repo.
```

### Which date should the emails go to?
Target the **next time the workflow actually runs** = the earliest **weekday at
11:11 AM IST that is still in the future**:

- Before 11:11 IST on a weekday → **today**
- After 11:11 IST on a weekday → **next weekday**
- Anytime on a weekend → **next Monday**

Check current IST time with: `TZ=Asia/Kolkata date "+%Y-%m-%d %H:%M %A"`.

### Option A — from a queue file (recommended)

Write the day's content in a Markdown queue file (any location). Format, repeated
per set:

```
SET 1
Subject: <subject line>
Body:
<one or more lines of body text>
BCC:
a@example.com
b@example.com
c@example.com

SET 2
Subject: <different subject>
Body:
<different content>
BCC:
x@example.com
y@example.com
```

Optional per-set lines (put them before `Body:`): `From name:`, `Reply-to:`, `To:`.
BCC addresses may be one per line or comma-separated. Do **not** mention the
resume — it's auto-attached.

Then generate the folder and push:
```bash
python tools/parse_queue.py /path/to/Cold_Emails_2026-06-29.md 2026-06-29
git add emails/2026-06-29 && git commit -m "Queue emails for 2026-06-29" && git push
```

### Option B — by hand
```bash
cp -r emails/_example "emails/2026-06-29"
# edit emails/2026-06-29/campaign.yml + put body files in that folder
git add emails/2026-06-29 && git commit -m "Queue emails for 2026-06-29" && git push
```

### Adding more sets to a day already queued
Just append more entries to that day's `campaign.yml` (and add the body files),
then commit and push again. New sets stack onto the existing ones.

---

## 5. Testing without sending

- **Dry run (recommended before a big batch):** GitHub → **Actions** tab →
  *Send daily cold emails* → **Run workflow** → tick **Dry run**. It validates the
  YAML, confirms how many emails would send and to how many recipients, and sends
  nothing.
- **Local validation** (no real send):
  ```bash
  pip install -r requirements.txt
  GMAIL_USER=x GMAIL_APP_PASSWORD=y DRY_RUN=1 python send_emails.py
  ```
  (Needs `emails/<today>/` to exist, or it will just report "nothing to send".)

---

## 6. Running it manually / off-schedule

Both workflows have a manual trigger (Actions tab → pick workflow → **Run workflow**):
- *Send daily cold emails* — sends `emails/<today>/` right now (untick Dry run for a real send).
- *Daily upload reminder* — sends the reminder email right now.

---

## 7. One-time setup (already done; for reference / rebuild)

1. **Gmail App Password:** enable 2-Step Verification, then create one at
   <https://myaccount.google.com/apppasswords>. It's a 16-char code, not your
   normal password.
2. **GitHub secrets** (repo → Settings → Secrets and variables → Actions):
   - `GMAIL_USER` = `akashgupta14902@gmail.com`
   - `GMAIL_APP_PASSWORD` = the app password
   Set/rotate from the CLI: `gh secret set GMAIL_APP_PASSWORD` (prompts to paste).

---

## 8. Changing the schedule or timezone

Edit the `cron:` line in the workflow files (cron is **UTC**; IST = UTC + 5:30,
`1-5` = Mon–Fri):
- Send: `.github/workflows/send-emails.yml` → `41 5 * * 1-5` (11:11 IST)
- Reminder: `.github/workflows/reminder.yml` → `0 4 * * 1-5` (09:30 IST)

The "today" calculation uses the `TIMEZONE` env var in `send-emails.yml`
(`Asia/Kolkata`). GitHub-scheduled jobs can start a few minutes late under load.

---

## 9. Limits & deliverability

- **Gmail limits:** free `@gmail.com` allows ~500 recipients/day. Your typical
  volume is well within this.
- **Bounces hurt the most:** invalid/guessed addresses bounce, and repeated high
  bounce rates degrade your sender reputation (future mail lands in spam). Prefer
  verified addresses; avoid sending many guessed permutations.
- **Spam score:** authentication is solid (DKIM signed by Gmail, SPF passes). To
  improve further you could add a `List-Unsubscribe` header in `send_emails.py`.
- Only email people you're permitted to contact.
