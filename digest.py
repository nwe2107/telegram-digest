"""Fetch new messages from the group, email an HTML digest, update state.

Env vars: TG_API_ID, TG_API_HASH, TG_GROUP_ID, GMAIL_ADDRESS, GMAIL_APP_PASSWORD
State: state.txt holds the last-seen message ID.
"""
import html
import os
import smtplib
import sys
from datetime import datetime, timedelta, timezone
from email.mime.text import MIMEText
from pathlib import Path

from telethon.sync import TelegramClient

STATE = Path(__file__).with_name("state.txt")

group_id = int(os.environ["TG_GROUP_ID"])
gmail = os.environ["GMAIL_ADDRESS"]
app_password = os.environ["GMAIL_APP_PASSWORD"]

last_id = int(STATE.read_text()) if STATE.exists() else None

rows = []
new_last_id = last_id or 0
with TelegramClient("digest", int(os.environ["TG_API_ID"]), os.environ["TG_API_HASH"]) as client:
    if last_id:
        messages = client.iter_messages(group_id, min_id=last_id, reverse=True)
    else:
        # ponytail: first run seeds with the past 7 days instead of full history
        messages = client.iter_messages(
            group_id, reverse=True, offset_date=datetime.now(timezone.utc) - timedelta(days=7)
        )
    for msg in messages:
        new_last_id = max(new_last_id, msg.id)
        text = msg.text or "[media/no text]"
        sender = msg.sender
        name = (getattr(sender, "first_name", None) or getattr(sender, "title", None) or "Unknown")
        if getattr(sender, "last_name", None):
            name += f" {sender.last_name}"
        rows.append(
            f"<p><b>{html.escape(name)}</b> "
            f"<span style='color:#888'>{msg.date:%Y-%m-%d %H:%M} UTC</span><br>"
            f"{html.escape(text).replace(chr(10), '<br>')}</p>"
        )

if not rows:
    print("No new messages; nothing sent.")
    sys.exit(0)

body = f"<html><body><h2>Telegram digest — {len(rows)} messages</h2>{''.join(rows)}</body></html>"
mail = MIMEText(body, "html", "utf-8")
mail["Subject"] = f"Telegram digest {datetime.now():%Y-%m-%d} ({len(rows)} messages)"
mail["From"] = gmail
mail["To"] = gmail

with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
    smtp.login(gmail, app_password)
    smtp.send_message(mail)

STATE.write_text(str(new_last_id))
print(f"Sent digest with {len(rows)} messages; last seen ID {new_last_id}.")
