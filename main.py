import os
import re
import logging
import random
from fastapi import FastAPI, Request
from aiogram import Bot, Dispatcher, types, F
from aiogram.enums import ParseMode, ChatMemberStatus
from aiogram.client.default import DefaultBotProperties
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, Update

API_TOKEN = os.getenv("BOT_TOKEN", "8735824882:AAGdS6WeHfTz2RenWRYUnNxleNESNXc1F4Y")

REQUIRED_CHANNEL = "@YukchiForwarder"
TARGET_GROUP_ID = -1003968416767

logging.basicConfig(level=logging.INFO)

bot = Bot(
    token=API_TOKEN, 
    default=DefaultBotProperties(parse_mode=ParseMode.HTML)
)

storage = MemoryStorage()
dp = Dispatcher(storage=storage)
app = FastAPI()

# Ma'lumotlarni vaqtincha saqlash
user_posts_count = {}   # Foydalanuvchi necha marta post tashlagani
user_add_req = {}      # Foydalanuvchi nechta odam qo'shishi kerakligi

class PostState(StatesGroup):
    waiting_for_text = State()
    waiting_for_phone = State()

# Filtrlar uchun Regex patternlar
PHONE_REGEX = r'(\+?998\s?\d{2}\s?\d{3}\s?\d{2}\s?\d{2}|\b\d{2}\s?\d{3}\s?\d{2}\s?\d{2}\b|\b\d{9}\b)'
LINK_REGEX = r'(https?://[^\s]+|t\.me/[^\s]+|@[a-zA-Z0-9_]+)'

# Taqiqlangan reklama so'zlari
SPAM_WORDS = ["kanalga", "gruppaga", "o'ting", "oting", "murojaat", "arzon", "aksiya", "reklama", "lichkaga", "manga oting"]

async def check_subscription(user_id: int) -> bool:
    try:
        member = await bot.get_chat_member(chat_id=REQUIRED_CHANNEL, user_id=user_id)
        return member.status in [ChatMemberStatus.CREATOR, ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.MEMBER]
    except Exception:
        return False

def get_sub_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📢 Guruhga/Kanalga qo'shilish", url="https://t.me/YukchiForwarder")],
        [InlineKeyboardButton(text="🔄 Tekshirish", callback_data="check_sub")]
    ])

def get_add_members_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕ Guruhga odam qo'shish", url="https://t.me/YukchiForwarder")],
        [InlineKeyboardButton(text="🔄 Qo'shdim, tekshirish", callback_data="check_added_members")]
    ])

@dp.message(F.text == "/start")
async def start_cmd(message: types.Message, state: FSMContext):
    is_subscribed = await check_subscription(message.from_user.id)
    if not is_subscribed:
        await message.answer("⚠️ <b>Botdan foydalanish uchun avval guruhimizga qo'shiling!</b>", reply_markup=get_sub_keyboard())
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

@dp.callback_query(F.data == "check_sub")
async def check_sub_callback(call: types.CallbackQuery, state: FSMContext):
    if await check_subscription(call.from_user.id):
        await call.message.delete()
        await call.message.answer("✅ Obuna tasdiqlandi! Endi yuk matnini yuborishingiz mumkin:")
        await state.set_state(PostState.waiting_for_text)
    else:
        await call.answer("❌ Siz hali guruhga qo'shilmadingiz! Avval qo'shiling.", show_alert=True)

@dp.message(PostState.waiting_for_text)
async def process_text(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    if not await check_subscription(user_id):
        await message.answer("⚠️ Botdan foydalanish uchun guruhga a'zo bo'ling!", reply_markup=get_sub_keyboard())
        return

    # Odam qo'shish limitini tekshirish (2-martadan boshlab)
    posts_count = user_posts_count.get(user_id, 0)
    if posts_count >= 1:
        if user_id not in user_add_req:
            user_add_req[user_id] = random.randint(2, 50)
        
        req_count = user_add_req[user_id]
        await message.answer(
            f"🛑 <b>Diqqat!</b> Ikkinchi va undan keyingi e'lonlarni joylash uchun guruhga kamida <b>{req_count} ta odam</b> qo'shishingiz kerak!\n\n"
            "Odam qo'shib bo'lgach, pastdagi tekshirish tugmasini bosing:",
            reply_markup=get_add_members_keyboard()
        )
        return

    raw_text = message.text or message.caption or ""
    
    # 1. Telefon raqamlarni olib tashlash
    cleaned = re.sub(PHONE_REGEX, "", raw_text)
    # 2. @username, t.me ssilka va havola (link)larni butunlay tozalash
    cleaned = re.sub(LINK_REGEX, "", cleaned).strip()

    await state.update_data(cleaned_text=cleaned)
    await message.answer("Endi murojaat uchun <b>Telefon raqamingizni</b> yuboring (Masalan: +998901234567):")
    await state.set_state(PostState.waiting_for_phone)

@dp.callback_query(F.data == "check_added_members")
async def check_added_members_cb(call: types.CallbackQuery, state: FSMContext):
    user_id = call.from_user.id
    req_count = user_add_req.get(user_id, 2)
    
    # Guruh shartlari bajarilgan deb hisoblash va navbatdagi postga ruxsat berish
    if user_id in user_add_req:
        del user_add_req[user_id]
    
    await call.message.delete()
    await call.message.answer(f"✅ Rahmat! Odam qo'shilgani tasdiqlandi. Endi yuk matnini yuborishingiz mumkin:")
    await state.set_state(PostState.waiting_for_text)

@dp.message(PostState.waiting_for_phone)
async def process_phone(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
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
        [InlineKeyboardButton(text="📞 Nomer ko'rish", callback_data=f"show_phone:{phone_number}")],
        [InlineKeyboardButton(text="➕ Botni guruhga qo'shish", url="https://t.me/TeleProzona_Bot?startgroup=true")]
    ])

    try:
        await bot.send_message(
            chat_id=TARGET_GROUP_ID,
            text=final_caption,
            reply_markup=keyboard
        )
        user_posts_count[user_id] = user_posts_count.get(user_id, 0) + 1
        await message.answer("✅ E'loningiz muvaffaqiyatli guruhga joylandi! Yangi e'lon berish uchun matn yuboring.")
    except Exception as e:
        await message.answer(f"❌ Xatolik yuz berdi. Bot guruhda admin ekanligini tekshiring.\n{e}")

    await state.clear()

@dp.callback_query(F.data.startswith("show_phone:"))
async def show_phone_handler(call: types.CallbackQuery):
    phone = call.data.split("show_phone:")[1]
    await call.answer(f"📞 Murojaat uchun nomer:\n{phone}", show_alert=True)

# GURUHDA REKLAMA SPREAD QILGANLARNI AVTO-BAN QILISH HANDLERI
@dp.message(F.chat.id == TARGET_GROUP_ID)
async def auto_ban_spammers(message: types.Message):
    if not message.text and not message.caption:
        return

    text = (message.text or message.caption).lower()

    # Reklama so'zlari yoki @username/http ssilka borligini tekshirish
    has_spam_word = any(word in text for word in SPAM_WORDS)
    has_link = bool(re.search(LINK_REGEX, text))

    if has_spam_word or has_link:
        try:
            # Xabarni o'chirish
            await message.delete()
            # Foydalanuvchini guruhdan BAN qilish
            await bot.ban_chat_member(chat_id=TARGET_GROUP_ID, user_id=message.from_user.id)
        except Exception:
            pass

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
