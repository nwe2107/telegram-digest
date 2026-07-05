"""One-time interactive login. Creates digest.session for future non-interactive runs."""
import os
import sys

from telethon.sync import TelegramClient

api_id = os.environ.get("TG_API_ID")
api_hash = os.environ.get("TG_API_HASH")
if not api_id or not api_hash:
    sys.exit("Set TG_API_ID and TG_API_HASH environment variables first.")

with TelegramClient("digest", int(api_id), api_hash) as client:
    me = client.get_me()
    print(f"Logged in as {me.first_name} (@{me.username}). Session saved to digest.session")
