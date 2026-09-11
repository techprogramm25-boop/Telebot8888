import os
from fastapi import FastAPI, Request
from aiogram import Bot, Dispatcher, types
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import Update

# Token Vercel Environment Variables yoki standart tokendan olinadi
TOKEN = os.getenv("BOT_TOKEN", "8735824882:AAGdS6WeHfTz2RenWRYUnNxleNESNXc1F4Y")

bot = Bot(token=TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

app = FastAPI()

# /start buyrug'iga javob beruvchi handler
@dp.message()
async def main_handler(message: types.Message):
    if message.text == "/start":
        await message.answer("Salom! Bot Vercel serverless muhitida muvaffaqiyatli ishlamoqda! 🚀")

# Webhook keladigan endpoint (Vercel va Telegram ulagichi)
@app.post("/")
@app.post("/api/index")
async def handle_webhook(request: Request):
    try:
        data = await request.json()
        update = Update(**data)
        await dp.feed_update(bot, update)
        return {"status": "ok"}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.get("/")
async def root():
    return {"status": "Bot is alive!"}
