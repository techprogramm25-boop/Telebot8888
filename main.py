import re
import logging
import asyncio
from datetime import datetime, timedelta
from fastapi import FastAPI, Request
from aiogram import Bot, Dispatcher, types, F
from aiogram.enums import ParseMode, ChatMemberStatus
from aiogram.client.default import DefaultBotProperties
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, Update

# ================= CONFIGURATION =================
API_TOKEN_1 = "8726416871:AAEKluMhwL7k4eP0RkchwvF_f82VQmLgc3A"
API_TOKEN_2 = "8112720689:AAFR_KtcgUYH3vBlsFZcBRj4qH3SGCwI2Zo"

ADMINS = [6977836294, 8409259397]

REQUIRED_CHANNELS = ["@YukchiForwarder", "@YukchiForwarderPeople"]
TARGET_GROUPS = [-1003968416767, -1003775919755]
SUPPORT_SITE_URL = "https://vercell-flax.vercel.app/"
BOT_USERNAME = "TeleProzona_Bot"

logging.basicConfig(level=logging.INFO)

bot1 = Bot(token=API_TOKEN_1, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp1 = Dispatcher(storage=MemoryStorage())

bot2 = Bot(token=API_TOKEN_2, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp2 = Dispatcher(storage=MemoryStorage())

app = FastAPI()

user_posts_count = {}      
banned_users = {}          
user_last_post_time = {}  

class PostState(StatesGroup):
    waiting_for_text = State()
    waiting_for_phone = State()

class AdminState(StatesGroup):
    waiting_for_ban_target = State()
    waiting_for_broadcast = State()

class ComplaintState(StatesGroup):
    waiting_for_complaint_text = State()

PHONE_REGEX = r'(\+?998\s?\d{2}\s?\d{3}\s?\d{2}\s?\d{2}|\b\d{2}\s?\d{3}\s?\d{2}\s?\d{2}\b|\b\d{9}\b)'
LINK_REGEX = r'(https?://[^\s]+|t\.me/[^\s]+|@[a-zA-Z0-9_]+)'
SPAM_WORDS = ["kanalga", "gruppaga", "o'ting", "oting", "murojaat", "arzon", "aksiya", "reklama", "lichkaga", "manga oting", "http", "t.me"]

# ================= 1-BOT (E'lon boti) Mantiqi =================

async def check_subscriptions(user_id: int) -> bool:
    for channel in REQUIRED_CHANNELS:
        try:
            member = await bot1.get_chat_member(chat_id=channel, user_id=user_id)
            if member.status not in [ChatMemberStatus.CREATOR, ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.MEMBER]:
                return False
        except Exception:
            return False
    return True

def get_sub_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📢 1-Kanalga qo'shilish", url="https://t.me/YukchiForwarder")],
        [InlineKeyboardButton(text="📢 2-Kanalga qo'shilish", url="https://t.me/YukchiForwarderPeople")],
        [InlineKeyboardButton(text="🔄 Tekshirish", callback_data="check_sub")]
    ])

def get_admin_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📢 Reklama yuborish", callback_data="admin_broadcast")],
        [
            InlineKeyboardButton(text="🚫 Ban qilish", callback_data="admin_ban_user"),
            InlineKeyboardButton(text="✅ Bandan chiqarish", callback_data="admin_unban_list")
        ]
    ])

@dp1.message(F.text == "/start")
async def start_cmd_bot1(message: types.Message, state: FSMContext):
    await state.clear()
    user_id = message.from_user.id

    if user_id in banned_users:
        await message.answer("⛔️ <b>Siz botdan va guruhlardan bloklangansiz!</b>")
        return

    if user_id in ADMINS:
        await message.answer("👨‍💻 <b>Xush kelibsiz Admin!</b>\n\nBoshqaruv paneli:", reply_markup=get_admin_keyboard())

    welcome_text = (
        "<b>Assalomu Alaykum!</b> 😎\n\n"
        "📢 Yukingiz bo‘lsa — guruhlarimizga joylang!\n"
        "🚛 Mashinangiz bo‘lsa — o'zingizga mos yukni toping!\n\n"
        "👨‍💻 <b>Admin:</b> @Yusufxonpro1\n\n"
        "📢 <b>Rasmiy kanallarimiz:</b>\n"
        "• @YukchiForwarder\n"
        "• @YukchiForwarderPeople\n\n"
        "<b>E'lon joylash uchun yuk matnini yuboring:</b>"
    )

    is_subscribed = await check_subscriptions(user_id)
    if not is_subscribed:
        await message.answer(
            f"{welcome_text}\n\n⚠️ <b>Botdan foydalanish uchun avval ikkala kanalimizga ham qo'shiling!</b>", 
            reply_markup=get_sub_keyboard()
        )
        return

    await message.answer(welcome_text)
    await state.set_state(PostState.waiting_for_text)

@dp1.callback_query(F.data == "admin_broadcast")
async def admin_broadcast_start(call: types.CallbackQuery, state: FSMContext):
    if call.from_user.id not in ADMINS: return
    await call.message.answer("📢 <b>Reklama xabarini yuboring!</b>")
    await state.set_state(AdminState.waiting_for_broadcast)

@dp1.message(AdminState.waiting_for_broadcast)
async def admin_broadcast_process(message: types.Message, state: FSMContext):
    if message.from_user.id not in ADMINS: return
    success_count = 0
    for group_id in TARGET_GROUPS:
        try:
            await message.copy_to(chat_id=group_id)
            success_count += 1
        except Exception:
            pass
    await message.answer(f"✅ <b>Reklama {success_count} ta guruhga yuborildi!</b>")
    await state.clear()

@dp1.callback_query(F.data == "admin_ban_user")
async def admin_ban_start(call: types.CallbackQuery, state: FSMContext):
    if call.from_user.id not in ADMINS: return
    await call.message.answer("🚫 Ban qilmoqchi bo'lgan foydalanuvchi ID/Username yuboring:")
    await state.set_state(AdminState.waiting_for_ban_target)

@dp1.message(AdminState.waiting_for_ban_target)
async def admin_ban_process(message: types.Message, state: FSMContext):
    if message.from_user.id not in ADMINS: return
    target = message.text.strip()
    ban_key = int(target) if target.isdigit() else target
    banned_users[ban_key] = target
    if isinstance(ban_key, int):
        for group_id in TARGET_GROUPS:
            try: await bot1.ban_chat_member(chat_id=group_id, user_id=ban_key)
            except Exception: pass
    await message.answer(f"✅ <b>{target}</b> ban qilindi!")
    await state.clear()

@dp1.callback_query(F.data == "check_sub")
async def check_sub_callback(call: types.CallbackQuery, state: FSMContext):
    if await check_subscriptions(call.from_user.id):
        await call.message.delete()
        await call.message.answer("✅ Obuna tasdiqlandi! Endi yuk matnini yuboring:")
        await state.set_state(PostState.waiting_for_text)
    else:
        await call.answer("❌ Siz hali hamma kanallarga qo'shilmadingiz!", show_alert=True)

@dp1.message(PostState.waiting_for_text)
async def process_text(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    if user_id in banned_users: return
    
    if user_id not in ADMINS and user_id in user_last_post_time:
        time_diff = datetime.now() - user_last_post_time[user_id]
        if time_diff < timedelta(minutes=3):
            await message.answer("⏱ <b>Har 3 daqiqada 1 ta e'lon berishingiz mumkin! Kuting.</b>")
            return

    raw_text = message.text or message.caption or ""
    photo_id = message.photo[-1].file_id if message.photo else None
    
    # Matn ichidagi har qanday telefon raqamini va havolalarni tozalab tashlaymiz
    cleaned = re.sub(PHONE_REGEX, "", raw_text)
    cleaned = re.sub(LINK_REGEX, "", cleaned).strip()

    await state.update_data(cleaned_text=cleaned, photo_id=photo_id)
    await message.answer("Endi murojaat uchun <b>Telefon raqamingizni</b> yuboring:")
    await state.set_state(PostState.waiting_for_phone)

@dp1.message(PostState.waiting_for_phone)
async def process_phone(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    phone_number = message.text.strip()
    data = await state.get_data()
    
    # Matn ichidan nomer olib tashlandi, faqat oxirida kanallar va admin chiqadi (Tel matnda ko'rinmaydi)
    final_caption = (
        f"{data.get('cleaned_text', '')}\n\n"
        f"_____________________\n"
        f"👨‍💻 <b>Admin:</b> @Yusufxonpro1\n"
        f"📢 <b>Rasmiy kanalimiz:</b> @YukchiForwarder\n"
        f"📢 <b>Rasmiy Kanalimiz:</b> @YukchiForwarderPeople"
    )
    
    # E'lon ostidagi 3 ta tugma (Nomer faqat tugmani bosganda chiqadi)
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📞 Nomer ko'rish", callback_data=f"show_phone:{phone_number}")],
        [InlineKeyboardButton(text="🌐 Support sayt", url=SUPPORT_SITE_URL)],
        [InlineKeyboardButton(text="📢 Kanallarimiz", url="https://t.me/YukchiForwarder")]
    ])

    try:
        for group_id in TARGET_GROUPS:
            if data.get("photo_id"):
                await bot1.send_photo(chat_id=group_id, photo=data.get("photo_id"), caption=final_caption, reply_markup=keyboard)
            else:
                await bot1.send_message(chat_id=group_id, text=final_caption, reply_markup=keyboard)
        user_last_post_time[user_id] = datetime.now()
        await message.answer("✅ E'loningiz muvaffaqiyatli guruhga joylandi!")
    except Exception as e:
        await message.answer(f"❌ Xatolik: {e}")
    await state.clear()

@dp1.callback_query(F.data.startswith("show_phone:"))
async def show_phone_handler(call: types.CallbackQuery):
    await call.answer(f"📞 Nomer: {call.data.split('show_phone:')[1]}", show_alert=True)


# ================= 2-BOT (Himoya va Shikoyat boti) Mantiqi =================

def get_complaint_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⚠️ Shikoyat qilish", callback_data="comp_shikoyat")],
        [InlineKeyboardButton(text="❓ Muammo bildirish", callback_data="comp_muammo")],
        [InlineKeyboardButton(text="🌐 Support Sayt", url=SUPPORT_SITE_URL)]
    ])

@dp2.message(F.text == "/start")
async def start_cmd_bot2(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer(
        "🛡 <b>Xavfsizlik va Qo'llab-quvvatlash boti</b>\n\n"
        "Bu bot guruhlarni hackerlar va reklamalardan himoya qiladi.\n"
        "Adminlarga murojaat qilish yoki saytimizga o'tish uchun pastdagi tugmalardan foydalaning:",
        reply_markup=get_complaint_keyboard()
    )

@dp2.callback_query(F.data.in_({"comp_shikoyat", "comp_muammo"}))
async def complaint_type_chosen(call: types.CallbackQuery, state: FSMContext):
    c_type = "Shikoyat" if call.data == "comp_shikoyat" else "Muammo"
    await state.update_data(complaint_type=c_type)
    await call.message.answer(f"📝 Iltimos, {c_type.lower()}ingiz bo'yicha to'liq matn yoki rasm yuboring:")
    await state.set_state(ComplaintState.waiting_for_complaint_text)

@dp2.message(ComplaintState.waiting_for_complaint_text)
async def process_complaint_text(message: types.Message, state: FSMContext):
    data = await state.get_data()
    c_type = data.get("complaint_type", "Murojaat")
    user = message.from_user
    
    user_info = f"👤 <b>Kimdan:</b> {user.full_name} (@{user.username or 'yoq'}, ID: <code>{user.id}</code>)\n📌 <b>Turi:</b> {c_type}"
    
    for admin_id in ADMINS:
        try:
            if message.photo:
                await bot2.send_photo(chat_id=admin_id, photo=message.photo[-1].file_id, caption=f"{user_info}\n\n💬 <b>Xabar:</b> {message.caption or ''}")
            else:
                await bot2.send_message(chat_id=admin_id, text=f"{user_info}\n\n💬 <b>Xabar:</b> {message.text}")
        except Exception:
            pass

    await message.answer(f"✅ Sizning {c_type.lower()}ingiz adminlarga yuborildi!")
    await state.clear()

@dp2.message(lambda message: message.chat.id in TARGET_GROUPS)
async def security_group_guard(message: types.Message):
    user_id = message.from_user.id
    if user_id in ADMINS:
        return

    text = (message.text or message.caption or "").lower()
    has_spam = any(w in text for w in SPAM_WORDS)
    has_link = bool(re.search(LINK_REGEX, text))

    if has_spam or has_link:
        try:
            await message.delete()
            for group_id in TARGET_GROUPS:
                try:
                    await bot2.ban_chat_member(chat_id=group_id, user_id=user_id)
                except Exception:
                    pass
            banned_users[user_id] = message.from_user.full_name
            
            for admin_id in ADMINS:
                try:
                    await bot2.send_message(admin_id, f"🚨 <b>Hujum/Reklama bloklandi!</b>\nFoydalanuvchi: {message.from_user.full_name} (<code>{user_id}</code>) guruhdan haydaldi.")
                except Exception:
                    pass
        except Exception:
            pass


# ================= FastAPI Webhook Endpoints =================

@app.post(f"/webhook/bot1/{API_TOKEN_1}")
async def webhook_bot1(request: Request):
    try:
        json_data = await request.json()
        update = Update.model_validate(json_data, context={"bot": bot1})
        await dp1.feed_update(bot1, update)
        return {"status": "ok"}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.post(f"/webhook/bot2/{API_TOKEN_2}")
async def webhook_bot2(request: Request):
    try:
        json_data = await request.json()
        update = Update.model_validate(json_data, context={"bot": bot2})
        await dp2.feed_update(bot2, update)
        return {"status": "ok"}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.get("/")
async def root():
    return {"status": "Bot serveri to'liq ishlamoqda!"}
