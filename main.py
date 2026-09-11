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

# Adminlar ID ro'yxati
ADMINS = [6977836294, 8409259397]

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

# Ma'lumotlar bazasi (xotirada)
user_posts_count = {}   
user_add_req = {}      
banned_users = {}       # {user_id: "username_yoki_nomer"}

class PostState(StatesGroup):
    waiting_for_text = State()
    waiting_for_phone = State()

class AdminState(StatesGroup):
    waiting_for_ban_target = State()

PHONE_REGEX = r'(\+?998\s?\d{2}\s?\d{3}\s?\d{2}\s?\d{2}|\b\d{2}\s?\d{3}\s?\d{2}\s?\d{2}\b|\b\d{9}\b)'
LINK_REGEX = r'(https?://[^\s]+|t\.me/[^\s]+|@[a-zA-Z0-9_]+)'
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

# Admin panel tugmalari
def get_admin_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🚫 Ban qilish", callback_data="admin_ban_user"),
            InlineKeyboardButton(text="✅ Bandan chiqarish", callback_data="admin_unban_list")
        ]
    ])

@dp.message(F.text == "/start")
async def start_cmd(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    
    # Ban bo'lgan foydalanuvchini bloklash
    if user_id in banned_users:
        await message.answer("⛔️ **Siz botdan va guruhdan bloklangansiz!** Yuk tashlay olmaysiz.")
        return

    # Adminlar uchun alohida ko'rinish
    if user_id in ADMINS:
        await message.answer(
            "👨‍💻 **Hush kelibsiz Admin!**\n\nBoshqaruv panelidan foydalanishingiz mumkin:",
            reply_markup=get_admin_keyboard()
        )

    is_subscribed = await check_subscription(user_id)
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

# ADMIN: BAN QILISH BUYRUG'I
@dp.callback_query(F.data == "admin_ban_user")
async def admin_ban_start(call: types.CallbackQuery, state: FSMContext):
    if call.from_user.id not in ADMINS:
        return
    await call.message.answer("🚫 Ban qilmoqchi bo'lgan foydalanuvchining **Username** (masalan `@username`) yoki **ID / Nomerini** yuboring:")
    await state.set_state(AdminState.waiting_for_ban_target)

@dp.message(AdminState.waiting_for_ban_target)
async def admin_ban_process(message: types.Message, state: FSMContext):
    if message.from_user.id not in ADMINS:
        return
    
    target = message.text.strip()
    # ID yoki Username orqali belgilash
    ban_key = int(target) if target.isdigit() else target
    banned_users[ban_key] = target

    # Agar ID bo'lsa Telegram guruhdan ham BAN qilish
    if isinstance(ban_key, int):
        try:
            await bot.ban_chat_member(chat_id=TARGET_GROUP_ID, user_id=ban_key)
        except Exception:
            pass

    await message.answer(f"✅ **{target}** muvaffaqiyatli bloklandi (BAN qilindi)!")
    await state.clear()

# ADMIN: BANDAN CHIQARISH RO'YXATI
@dp.callback_query(F.data == "admin_unban_list")
async def admin_unban_list(call: types.CallbackQuery):
    if call.from_user.id not in ADMINS:
        return

    if not banned_users:
        await call.message.answer("📜 Hozircha ban bo'lgan foydalanuvchilar yo'q.")
        return

    buttons = []
    for uid, uname in banned_users.items():
        buttons.append([InlineKeyboardButton(text=f"🔓 {uname}", callback_data=f"unban:{uid}")])
    
    kb = InlineKeyboardMarkup(inline_keyboard=buttons)
    await call.message.answer("Qaysi foydalanuvchini bandan chiqarmoqchisiz? Tanlang:", reply_markup=kb)

# ADMIN: BANDAN CHIQARISH
@dp.callback_query(F.data.startswith("unban:"))
async def admin_unban_process(call: types.CallbackQuery):
    if call.from_user.id not in ADMINS:
        return

    raw_uid = call.data.split("unban:")[1]
    uid = int(raw_uid) if raw_uid.isdigit() else raw_uid

    if uid in banned_users:
        del banned_users[uid]
        if isinstance(uid, int):
            try:
                await bot.unban_chat_member(chat_id=TARGET_GROUP_ID, user_id=uid)
            except Exception:
                pass
        await call.message.edit_text("✅ Foydalanuvchi muvaffaqiyatli bandan chiqarildi!")
    else:
        await call.answer("Bu foydalanuvchi ro'yxatda topilmadi.", show_alert=True)

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

    if user_id in banned_users:
        await message.answer("⛔️ Siz bloklangansiz!")
        return

    if not await check_subscription(user_id):
        await message.answer("⚠️ Botdan foydalanish uchun guruhga a'zo bo'ling!", reply_markup=get_sub_keyboard())
        return

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
    cleaned = re.sub(PHONE_REGEX, "", raw_text)
    cleaned = re.sub(LINK_REGEX, "", cleaned).strip()

    await state.update_data(cleaned_text=cleaned)
    await message.answer("Endi murojaat uchun <b>Telefon raqamingizni</b> yuboring (Masalan: +998901234567):")
    await state.set_state(PostState.waiting_for_phone)

@dp.callback_query(F.data == "check_added_members")
async def check_added_members_cb(call: types.CallbackQuery, state: FSMContext):
    user_id = call.from_user.id
    if user_id in user_add_req:
        del user_add_req[user_id]
    
    await call.message.delete()
    await call.message.answer("✅ Rahmat! Odam qo'shilgani tasdiqlandi. Endi yuk matnini yuborishingiz mumkin:")
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

@dp.message(F.chat.id == TARGET_GROUP_ID)
async def auto_ban_spammers(message: types.Message):
    if not message.text and not message.caption:
        return

    text = (message.text or message.caption).lower()
    has_spam_word = any(word in text for word in SPAM_WORDS)
    has_link = bool(re.search(LINK_REGEX, text))

    if has_spam_word or has_link:
        try:
            await message.delete()
            await bot.ban_chat_member(chat_id=TARGET_GROUP_ID, user_id=message.from_user.id)
            banned_users[message.from_user.id] = message.from_user.full_name
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
