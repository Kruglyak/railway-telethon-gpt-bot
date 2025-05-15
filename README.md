# Railway Telethon All Messages Bot

User-bot для Railway: выводит все входящие и исходящие сообщения Telegram в stdout (Telethon). Готов к деплою в Railway.

## Быстрый старт

1. **Создайте переменные окружения в Railway:**
   - `TELEGRAM_API_ID` — int (получить на https://my.telegram.org)
   - `TELEGRAM_API_HASH` — str (там же)
   - `TELEGRAM_SESSION` — str (см. ниже)

2. **Как получить TELEGRAM_SESSION:**
    ```python
    from telethon import TelegramClient, StringSession
    api_id = ...
    api_hash = ...
    with TelegramClient(StringSession(), api_id, api_hash) as cli:
        print(cli.session.save())
    ```
    Скопируйте напечатанную строку в переменную окружения `TELEGRAM_SESSION`.

3. **Деплой в Railway:**
    - Нажмите "New Project" → "Deploy from GitHub repo".
    - Укажите эту репу.
    - Установите переменные окружения.
    - После запуска все входящие и исходящие сообщения будут появляться в логах Railway.

## Файлы
- `main.py` — основной бот
- `requirements.txt` — зависимости
- `Procfile` — для запуска в Railway

---

**Всё готово для деплоя!**
