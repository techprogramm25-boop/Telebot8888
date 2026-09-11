import os
import re
import logging
from fastapi import FastAPI, Request
from aiogram import Bot, Dispatcher, types, F
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, Update

API_TOKEN = os.getenv("BOT_TOKEN", "8735824882:AAGdS6WeHfTz2RenWRYUnNxleNESNXc1F4Y")

# Majburiy obuna kanali va guruhi
REQUIRED_CHANNEL = "@YukchiForwarder"  # Kanal yoki guruh username'i
TARGET_GROUP_ID = -1003968416767       # Postlar boradigan guruh ID'si

logging.basicConfig(level=logging.INFO)

bot = Bot(
    token=API_TOKEN, 
    default=DefaultBotProperties(parse_mode=ParseMode.HTML)
)

storage = MemoryStorage()
dp = Dispatcher(storage=storage)
app = FastAPI()

class PostState(StatesGroup):
    waiting_for_text = State()
    waiting_for_phone = State()

PHONE_REGEX = r'(\+?998\s?\d{2}\s?\d{3}\s?\d{2}\s?\d{2}|\b\d{2}\s?\d{3}\s?\d{2}\s?\d{2}\b|\b\d{9}\b)'

# Obunani tekshirish funksiyasi
async def check_subscription(user_id: int) -> bool:
    try:
        member = await bot.get_chat_member(chat_id=REQUIRED_CHANNEL, user_id=user_id)
        return member.status in ["creator", "administrator", "member"]
    except Exception:
        return False

# Obuna bo'lish tugmalari
def get_sub_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="📢 Guruhga/Kanalga qo'shilish", url="https://t.me/YukchiForwarder")
        ],
        [
            InlineKeyboardButton(text="🔄 Tekshirish", callback_data="check_sub")
        ]
    ])

@dp.message(F.text == "/start")
async def start_cmd(message: types.Message, state: FSMContext):
    is_subscribed = await check_subscription(message.from_user.id)
    
    if not is_subscribed:
        await message.answer(
            "⚠️ <b>Botdan foydalanish uchun avval guruhimizga qo'shiling!</b>",
            reply_markup=get_sub_keyboard()
        )
        return

    welcome_text = (
        "Assalomu Alaykum 😎\n\n"
        "____________________________________\n"
        "📢 Yukingiz bo‘lsa — guruhga joylang!\n"
        "🚛 Mashina bo‘lsa — yukingizni toping!\n"
        "_______________________________\n"
        "Reklama 🧐 Ban\n"
        "__                         —\n"
        "@Yusufxonpro1 Admin😁\n"
        "@YukchiForwarder\n\n"
        "<b>E'lon joylash uchun yuk matnini yoki rasmini yuboring:</b>"
    )
    await message.answer(welcome_text)
    await state.set_state(PostState.waiting_for_text)

# Tekshirish tugmasi bosilganda
@dp.callback_query(F.data == "check_sub")
async def check_sub_callback(call: types.CallbackQuery, state: FSMContext):
    is_subscribed = await check_subscription(call.from_user.id)
    if is_subscribed:
        await call.message.delete()
        await call.message.answer(
            "✅ Obuna tasdiqlandi! Endi yuk matnini yoki rasmini yuborishingiz mumkin:"
        )
        await state.set_state(PostState.waiting_for_text)
    else:
        await call.answer("❌ Siz hali guruhga qo'shilmadingiz! Avval qo'shiling va qayta bosing.", show_alert=True)

@dp.message(PostState.waiting_for_text)
async def process_text(message: types.Message, state: FSMContext):
    is_subscribed = await check_subscription(message.from_user.id)
    if not is_subscribed:
        await message.answer("⚠️ Botdan foydalanish uchun guruhga a'zo bo'lishingiz kerak!", reply_markup=get_sub_keyboard())
        return

    raw_text = message.text or message.caption or ""
    cleaned_text = re.sub(PHONE_REGEX, "", raw_text).strip()
    
    await state.update_data(cleaned_text=cleaned_text)
    await message.answer("Endi murojaat uchun <b>Telefon raqamingizni</b> yuboring (Masalan: +998901234567):")
    await state.set_state(PostState.waiting_for_phone)

@dp.message(PostState.waiting_for_phone)
async def process_phone(message: types.Message, state: FSMContext):
    phone_number = message.text.strip()
    data = await state.get_data()
    cleaned_text = data.get("cleaned_text", "")

    final_caption = (
        f"{cleaned_text}\n\n"
        "_____________________\n"
        "@Yusufxonpro1 Admin\n"
        "@YukchiForwarder"
    )

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="📞 Nomer ko'rish", callback_data=f"show_phone:{phone_number}")
        ],
        [
            InlineKeyboardButton(text="➕ Botni guruhga qo'shish", url="https://t.me/TeleProzona_Bot?startgroup=true")
        ]
    ])

    try:
        await bot.send_message(
            chat_id=TARGET_GROUP_ID,
            text=final_caption,
            reply_markup=keyboard
        )
        await message.answer("✅ E'loningiz muvaffaqiyatli guruhga joylandi! Yangi e'lon berish uchun matn yuboring.")
    except Exception as e:
        await message.answer(f"❌ Xatolik yuz berdi. Bot guruhda admin ekanligiga ishonch hosil qiling.\nBatafsil: {e}")

    await state.clear()

@dp.callback_query(F.data.startswith("show_phone:"))
async def show_phone_handler(call: types.CallbackQuery):
    phone = call.data.split("show_phone:")[1]
    await call.answer(f"📞 Murojaat uchun nomer:\n{phone}", show_alert=True)

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
    return {"status": "Bot faol ishlamoqda!"}
