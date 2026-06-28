# Cold email automation

Sends your daily cold emails via Gmail, scheduled by GitHub Actions.

**Schedule:** every **weekday at 11:11 AM IST** (`41 5 * * 1-5` UTC).

**Safety:** the workflow only sends from `emails/<today>/campaign.yml`. If you
haven't created today's dated folder, **nothing is sent** — so yesterday's or
stale content can never go out by accident.

---

## One-time setup

### 1. Create a Gmail App Password
1. Your Google account must have **2-Step Verification** enabled.
2. Go to <https://myaccount.google.com/apppasswords>.
3. Create an app password (name it e.g. "cold-email-gha"). Copy the 16-character code.
   - This is **not** your normal Gmail password. Never commit it.

### 2. Push this project to GitHub
```bash
cd cold-email-automation
git init
git add .
git commit -m "Initial cold email automation"
git branch -M main
git remote add origin git@github.com:<you>/<repo>.git
git push -u origin main
```
Use a **private** repo (your bodies/recipients live here).

### 3. Add GitHub secrets
In your repo: **Settings → Secrets and variables → Actions → New repository secret**
- `GMAIL_USER` — your full Gmail address (e.g. `you@gmail.com`)
- `GMAIL_APP_PASSWORD` — the 16-char app password from step 1

That's it. The job now runs automatically each weekday morning.

---

## Daily routine (every morning)

1. Copy the template folder to today's date:
   ```bash
   cp -r emails/_example emails/$(date +%F)
   ```
2. Edit `emails/<today>/campaign.yml` — set subjects, `bcc` lists, body files,
   attachments. Add one entry per email (your ~5–10 sends).
3. Put body files (`.html` or `.txt`) and any attachments **inside that same
   dated folder**.
4. Commit and push **before 11:11 AM IST**:
   ```bash
   git add emails/$(date +%F) && git commit -m "Emails for $(date +%F)" && git push
   ```

If you skip a day, no folder = no send. Done.

### campaign.yml fields
| field | required | notes |
|-------|----------|-------|
| `subject` | yes | email subject line |
| `bcc` | yes* | list of hidden recipients (~4) |
| `to` | no | defaults to yourself; real recipients go in `bcc` |
| `cc` | no | visible CC list |
| `body` | yes | filename in the dated folder; `.html` → HTML, else plain text |
| `attachments` | no | list of filenames in the dated folder |
| `from_name` | no | display name on the From header |
| `reply_to` | no | Reply-To address |

\* you need `bcc` and/or `to`.

---

## Testing without sending real mail
- **Manual run:** Actions tab → *Send daily cold emails* → **Run workflow** →
  tick **Dry run**. It builds and validates everything but sends nothing.
- **Locally:**
  ```bash
  pip install -r requirements.txt
  export GMAIL_USER=you@gmail.com GMAIL_APP_PASSWORD=xxxx DRY_RUN=1
  cp -r emails/_example emails/$(date +%F)   # so today's folder exists
  python send_emails.py
  ```

---

## Notes & limits
- **Gmail sending limits:** a free `@gmail.com` account allows ~500 recipients
  per day; Google Workspace ~2,000. Your volume (~5–10 emails × ~4 bcc ≈ 20–40
  recipients/day) is well within limits.
- **Deliverability:** large Bcc batches and "cold" content can land in spam.
  Keep volumes modest, personalize, and include an opt-out line. Only email
  people you're permitted to contact.
- **Schedule drift:** GitHub-scheduled jobs can start a few minutes late under
  load. To change the time, edit the `cron` line in
  `.github/workflows/send-emails.yml` (remember it's UTC; IST = UTC + 5:30).
