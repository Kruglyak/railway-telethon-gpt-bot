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
import json
import asyncio
from datetime import datetime
from telethon import TelegramClient, events
from telethon.sessions import StringSession
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy import Column, Integer, String, DateTime, Text, BigInteger

DATABASE_URL = os.environ.get("DATABASE_URL")  # Railway PostgreSQL URL
Base = declarative_base()
engine = create_async_engine(DATABASE_URL, echo=False, future=True)
AsyncSessionLocal = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

class MessageLog(Base):
    __tablename__ = "messages"
    id = Column(Integer, primary_key=True, index=True)
    direction = Column(String(4))
    chat_id = Column(BigInteger)
    chat_title = Column(String(256))
    chat_type = Column(String(32))
    sender_id = Column(BigInteger)
    sender_username = Column(String(128))
    sender_first_name = Column(String(128))
    sender_last_name = Column(String(128))
    message_id = Column(BigInteger)
    date = Column(DateTime)
    text = Column(Text)
    raw_json = Column(Text)

async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

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

    # Получаем человекочитаемый заголовок и логин отправителя
    sender = await event.get_sender()
    sender_username = sender.username if sender and sender.username else None
    sender_first_name = sender.first_name if sender and sender.first_name else None
    sender_last_name = sender.last_name if sender and sender.last_name else None

    if hasattr(chat, "title") and chat.title:
        chat_title = chat.title
        chat_type = type(chat).__name__
    elif event.is_private:
        chat_title = f"{sender_first_name or ''} {sender_last_name or ''}".strip() or str(sender.id)
        chat_type = "private"
    else:
        chat_title = "UnknownChat"
        chat_type = type(chat).__name__

    # Текст или тип медиа
    content = event.raw_text.strip()
    if not content:
        media = event.message.media
        content = f"<{media.__class__.__name__}>" if media else "<NoText>"

    content = content.replace("\n", "\\n")  # однострочно

    # Сохраняем в БД
    msg_log = MessageLog(
        direction=direction.strip(),
        chat_id=getattr(chat, 'id', None),
        chat_title=chat_title,
        chat_type=chat_type,
        sender_id=getattr(sender, 'id', None),
        sender_username=sender_username,
        sender_first_name=sender_first_name,
        sender_last_name=sender_last_name,
        message_id=event.message.id,
        date=event.message.date,
        text=content,
        raw_json=json.dumps(event.message.to_dict(), ensure_ascii=False)
    )
    try:
        async with AsyncSessionLocal() as session:
            session.add(msg_log)
            await session.commit()
    except Exception as e:
        logging.error(f"DB error: {e}")

    logging.info("[%s] %s | %s", direction, chat_title, content)


async def main():
    logging.info("✅ Bot started — пишет входящие и исходящие сообщения в консоль.")
    await client.run_until_disconnected()


if __name__ == "__main__":
    async def startup():
        await init_db()
        await main()
    with client:
        client.loop.run_until_complete(startup())
