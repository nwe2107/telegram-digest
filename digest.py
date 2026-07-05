"""Fetch new messages from the group, email an HTML digest, update state.

Env vars: TG_API_ID, TG_API_HASH, TG_GROUP_ID, GMAIL_ADDRESS, GMAIL_APP_PASSWORD
State: state.txt holds the last-seen message ID.
"""
import html
import os
import smtplib
import sys
from datetime import datetime, timedelta, timezone
from email.message import EmailMessage
from email.utils import make_msgid
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
    images = []  # (cid, jpeg bytes)
    photo_bytes = 0
    for msg in messages:
        new_last_id = max(new_last_id, msg.id)
        text = msg.text or ("" if msg.photo else "[media/no text]")
        sender = msg.sender
        name = (getattr(sender, "first_name", None) or getattr(sender, "title", None) or "Unknown")
        if getattr(sender, "last_name", None):
            name += f" {sender.last_name}"
        img_tag = ""
        if msg.photo:
            # ponytail: 15MB total cap keeps us under Gmail's 25MB limit; photos only, no video/docs
            if photo_bytes < 15_000_000 and (data := client.download_media(msg, file=bytes)):
                cid = make_msgid()[1:-1]
                images.append((cid, data))
                photo_bytes += len(data)
                img_tag = f"<br><img src='cid:{cid}' style='max-width:480px'>"
            else:
                img_tag = "<br>[photo omitted]"
        rows.append(
            f"<p><b>{html.escape(name)}</b> "
            f"<span style='color:#888'>{msg.date:%Y-%m-%d %H:%M} UTC</span><br>"
            f"{html.escape(text).replace(chr(10), '<br>')}{img_tag}</p>"
        )

if not rows:
    print("No new messages; nothing sent.")
    sys.exit(0)

body = f"<html><body><h2>Telegram digest — {len(rows)} messages</h2>{''.join(rows)}</body></html>"
mail = EmailMessage()
mail["Subject"] = f"Telegram digest {datetime.now():%Y-%m-%d} ({len(rows)} messages)"
mail["From"] = gmail
mail["To"] = gmail
mail.add_alternative(body, subtype="html")
for cid, data in images:
    mail.get_payload()[0].add_related(data, maintype="image", subtype="jpeg", cid=f"<{cid}>")

with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
    smtp.login(gmail, app_password)
    smtp.send_message(mail)

STATE.write_text(str(new_last_id))
print(f"Sent digest with {len(rows)} messages; last seen ID {new_last_id}.")
