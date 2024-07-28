from pyrogram import Client

from settings.local_settings import PROXY, BOT_NAME, BOT_TOKEN

if not PROXY:
    client = Client(name=BOT_NAME, bot_token=BOT_TOKEN)
else:
    client = Client(name=BOT_NAME, bot_token=BOT_TOKEN, proxy=PROXY)
