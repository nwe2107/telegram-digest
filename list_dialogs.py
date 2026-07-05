"""List group/channel dialogs with their IDs. Run once to find the target group."""
import os

from telethon.sync import TelegramClient

with TelegramClient("digest", int(os.environ["TG_API_ID"]), os.environ["TG_API_HASH"]) as client:
    for d in client.iter_dialogs():
        if d.is_group or d.is_channel:
            print(f"{d.id}\t{d.title}")
