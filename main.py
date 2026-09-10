import os
import logging
from fastapi import FastAPI, Request
from aiogram import Bot, Dispatcher, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage

API_TOKEN = os.getenv('BOT_TOKEN', '8735824882:AAGdS6WeHfTz2RenWRYUnNxleNESNXc1F4Y')
ADMINS = [6977836294, 8409259397]

logging.basicConfig(level=logging.INFO)
bot = Bot(token=API_TOKEN, parse_mode=types.ParseMode.HTML)
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)

# Vercel talab qiladigan handler (FastAPI app)
app = FastAPI()

@dp.message_handler(commands=['start'])
async def start_cmd(message: types.Message):
    if message.from_user.id not in ADMINS:
        await message.reply("⛔️ Sizga ushbu botdan foydalanish uchun ruxsat berilmagan.")
        return
    await message.answer("<b>@Yusufxonpro1 Siz uchun Tayyor!</b>\n\nYuk/E'lon matnini yoki rasmini yuboring:")

@app.post("/")
async def process_webhook(request: Request):
    update_data = await request.json()
    update = types.Update(**update_data)
    Dispatcher.set_current(dp)
    Bot.set_current(bot)
    await dp.process_update(update)
    return {"status": "ok"}

@app.get("/")
async def root():
    return {"status": "Bot is running on Vercel"}
