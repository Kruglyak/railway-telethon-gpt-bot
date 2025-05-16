import os
import logging
import asyncio
from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select
import openai
from models import MessageLog  # Модель сообщений из вашей базы

# --- Конфиг из переменных окружения ---
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
DATABASE_URL = os.environ.get("DATABASE_URL")

client = openai.OpenAI(api_key=OPENAI_API_KEY)
openai.api_key = OPENAI_API_KEY

# --- SQLAlchemy setup ---
# Привести строку подключения к виду postgresql+asyncpg://
if DATABASE_URL and DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql+asyncpg://", 1)
elif DATABASE_URL and DATABASE_URL.startswith("postgresql://"):
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://", 1)
engine = create_async_engine(DATABASE_URL, echo=False, future=True)
AsyncSessionLocal = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

async def answer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_question = update.message.text

    # 1. GPT формирует SQL SELECT-запрос
    sql_prompt = (
        "Ты — помощник, который пишет SQL-запросы к таблице messages.\n"
        "Структура таблицы:\n"
        "id, direction, chat_id, chat_title, chat_type, sender_id, sender_username, sender_first_name, sender_last_name, message_id, date, text, raw_json\n"
        f"Пользователь просит: {user_question}\n"
        "Напиши только SQL-запрос (только SELECT, без объяснений):"
    )
    sql_response = client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": sql_prompt}],
        max_tokens=200,
    )
    sql_query = sql_response.choices[0].message.content.strip().split(';')[0]

    # 2. Проверка безопасности
    if not sql_query.lower().startswith("select"):
        await update.message.reply_text("Ошибка: GPT сгенерировал не SELECT запрос.\n\n" + sql_query)
        return

    # 3. Выполнить SQL-запрос
    try:
        async with AsyncSessionLocal() as session:
            result = await session.execute(sql_query)
            rows = result.fetchall()
            # Универсально: если row — tuple, ищем text в каждом
            texts = []
            for row in rows:
                if hasattr(row, 'text'):
                    texts.append(row.text)
                elif isinstance(row, tuple) and len(row) > 0:
                    # ищем поле text по имени
                    if hasattr(row[0], 'text'):
                        texts.append(row[0].text)
                    elif 'text' in row._fields:
                        texts.append(getattr(row, 'text'))
                    elif isinstance(row[0], str):
                        texts.append(row[0])
    except Exception as e:
        await update.message.reply_text(f"Ошибка выполнения SQL-запроса: {e}\n\n{sql_query}")
        return

    if not texts:
        await update.message.reply_text("Сообщения не найдены.")
        return

    # 4. GPT делает саммари (ограничим до 30 сообщений)
    text_for_summary = "\n".join(texts[:30])
    summary_prompt = (
        f"Вот сообщения:\n{text_for_summary}\n\nСделай краткое саммари на русском."
    )
    summary_response = client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": summary_prompt}],
        max_tokens=300,
    )
    summary = summary_response.choices[0].message.content

    await update.message.reply_text(summary)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, answer))
    app.run_polling()
