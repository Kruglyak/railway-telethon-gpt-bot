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

openai.api_key = OPENAI_API_KEY

# --- SQLAlchemy setup ---
engine = create_async_engine(DATABASE_URL, echo=False, future=True)
AsyncSessionLocal = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

async def answer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_question = update.message.text
    # 1. Поиск релевантных сообщений в БД
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(MessageLog).where(MessageLog.text.ilike(f"%{user_question}%")).limit(5)
        )
        found = result.scalars().all()
        context_text = "\n".join([msg.text for msg in found if msg.text])

    # 2. Формируем prompt и отправляем в OpenAI
    prompt = f"История чата:\n{context_text}\n\nВопрос: {user_question}\nОтветь максимально полезно:"
    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=300,
    )
    answer = response.choices[0].message["content"]

    await update.message.reply_text(answer)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, answer))
    app.run_polling()
