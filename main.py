"""
User-bot для Railway: выводит ВСЕ сообщения (IN / OUT) в stdout.

Переменные окружения (задать в Railway → Variables):
  TELEGRAM_API_ID    — int  (получить на https://my.telegram.org)
  TELEGRAM_API_HASH  — str  (там же)
  TELEGRAM_SESSION   — str  (StringSession, см. ниже)

Как один раз создать TELEGRAM_SESSION локально:
------------------------------------------------
from telethon import TelegramClient, StringSession
api_id = ...
api_hash = ...
with TelegramClient(StringSession(), api_id, api_hash) as cli:
    print(cli.session.save())
------------------------------------------------
Скопируйте напечатанную строку в переменную окружения TELEGRAM_SESSION.
"""

import os
import logging
from telethon import TelegramClient, events
from telethon.sessions import StringSession

# ---------- конфигурация ----------
API_ID      = int(os.environ["TELEGRAM_API_ID"])
API_HASH    = os.environ["TELEGRAM_API_HASH"]
SESSION_STR = os.environ["TELEGRAM_SESSION"]

# ---------- логирование ----------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

# ---------- клиент ----------
client = TelegramClient(StringSession(SESSION_STR), API_ID, API_HASH)


@client.on(events.NewMessage)
async def handle_all(event):
    """
    Ловим всё: входящие (event.out == False) и исходящие (event.out == True).
    Печатаем направление, название чата и текст/тип контента.
    """
    direction = "OUT" if event.out else "IN "
    chat = await event.get_chat()

    # Получаем человекочитаемый заголовок
    if hasattr(chat, "title") and chat.title:
        chat_title = chat.title
    elif event.is_private:
        user = await event.get_sender()
        chat_title = f"{user.first_name or ''} {user.last_name or ''}".strip() or str(user.id)
    else:
        chat_title = "UnknownChat"

    # Текст или тип медиа
    content = event.raw_text.strip()
    if not content:
        media = event.message.media
        content = f"<{media.__class__.__name__}>" if media else "<NoText>"

    content = content.replace("\n", "\\n")  # однострочно

    logging.info("[%s] %s | %s", direction, chat_title, content)


async def main():
    logging.info("✅ Bot started — пишет входящие и исходящие сообщения в консоль.")
    await client.run_until_disconnected()


if __name__ == "__main__":
    with client:
        client.loop.run_until_complete(main())
