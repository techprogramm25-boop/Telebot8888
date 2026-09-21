import os
import re
import logging
import random
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

API_TOKEN = os.getenv("BOT_TOKEN", import os
import re
import logging
import random
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

API_TOKEN = os.getenv("BOT_TOKEN", "8735824882:AAH0NB1cIxSnvXzWunCO53BnNo8rehsBv8Q")

ADMINS = [6977836294, 8409259397]
REQUIRED_CHANNEL = "@YukchiForwarder"

# Ikki ta guruh ID raqamlari ro'yxati
TARGET_GROUPS = [-1003968416767, -1003775919755]

SUPPORT_SITE_URL = "https://vercell-flax.vercel.app/"
BOT_USERNAME = "TeleProzona_Bot"

logging.basicConfig(level=logging.INFO)

bot = Bot(
    token=API_TOKEN, 
    default=DefaultBotProperties(parse_mode=ParseMode.HTML)
)

storage = MemoryStorage()
dp = Dispatcher(storage=storage)
app = FastAPI()

user_posts_count = {}     
user_add_req = {}        
banned_users = {}         
user_last_post_time = {}  

class PostState(StatesGroup):
    waiting_for_text = State()
    waiting_for_phone = State()

class AdminState(StatesGroup):
    waiting_for_ban_target = State()
    waiting_for_broadcast = State()

PHONE_REGEX = r'(\+?998\s?\d{2}\s?\d{3}\s?\d{2}\s?\d{2}|\b\d{2}\s?\d{3}\s?\d{2}\s?\d{2}\b|\b\d{9}\b)'
LINK_REGEX = r'(https?://[^\s]+|t\.me/[^\s]+|@[a-zA-Z0-9_]+)'
SPAM_WORDS = ["kanalga", "gruppaga", "o'ting", "oting", "murojaat", "arzon", "aksiya", "reklama", "lichkaga", "manga oting"]

async def check_subscription(user_id: int) -> bool:
    try:
        member = await bot.get_chat_member(chat_id=REQUIRED_CHANNEL, user_id=user_id)
        return member.status in [ChatMemberStatus.CREATOR, ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.MEMBER]
    except Exception:
        return False

async def delete_message_after_delay(chat_id: int, message_id: int, delay_seconds: int = 3600):
    await asyncio.sleep(delay_seconds)
    try:
        await bot.delete_message(chat_id=chat_id, message_id=message_id)
    except Exception:
        pass

def get_sub_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📢 1-Guruhga qo'shilish", url="https://t.me/YukchiForwarder")],
        [InlineKeyboardButton(text="📢 2-Guruhga qo'shilish (@YukchiForwarderPeople)", url="https://t.me/YukchiForwarderPeople")],
        [InlineKeyboardButton(text="🔄 Tekshirish", callback_data="check_sub")]
    ])

def get_add_members_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕ 1-Guruhga odam qo'shish", url="https://t.me/YukchiForwarder")],
        [InlineKeyboardButton(text="➕ 2-Guruhga odam qo'shish", url="https://t.me/YukchiForwarderPeople")],
        [InlineKeyboardButton(text="🔄 Qo'shdim, tekshirish", callback_data="check_added_members")]
    ])

def get_admin_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📢 Reklama yuborish", callback_data="admin_broadcast")],
        [
            InlineKeyboardButton(text="🚫 Ban qilish", callback_data="admin_ban_user"),
            InlineKeyboardButton(text="✅ Bandan chiqarish", callback_data="admin_unban_list")
        ]
    ])

@dp.message(F.text == "/start")
async def start_cmd(message: types.Message, state: FSMContext):
    user_id = message.from_user.id

    if user_id in banned_users:
        await message.answer("⛔️ <b>Siz botdan va guruhlardan bloklangansiz!</b>")
        return

    if user_id in ADMINS:
        await message.answer(
            "👨‍💻 <b>Hush kelibsiz Admin!</b>\n\nBoshqaruv paneli:",
            reply_markup=get_admin_keyboard()
        )

    welcome_text = (
        "<b>Assalomu Alaykum!</b> 😎\n\n"
        "📢 Yukingiz bo‘lsa — guruhlarimizga joylang!\n"
        "🚛 Mashinangiz bo‘lsa — o'zingizga mos yukni toping!\n\n"
        "👨‍💻 <b>Admin:</b> @Yusufxonpro1\n\n"
        "📢 <b>Rasmiy kanalimiz:</b> @YukchiForwarder\n"
        "📢 <b>Rasmiy Kanalimiz:</b> @YukchiForwarderPeople\n\n"
        "<b>E'lon joylash uchun yuk matnini yuboring:</b>"
    )

    is_subscribed = await check_subscription(user_id)
    if not is_subscribed:
        await message.answer(
            f"{welcome_text}\n\n⚠️ <b>Botdan foydalanish uchun avval guruhlarimizga qo'shiling!</b>", 
            reply_markup=get_sub_keyboard()
        )
        return

    await message.answer(welcome_text)
    await state.set_state(PostState.waiting_for_text)

@dp.callback_query(F.data == "admin_broadcast")
async def admin_broadcast_start(call: types.CallbackQuery, state: FSMContext):
    if call.from_user.id not in ADMINS:
        return
    await call.message.answer(
        "📢 <b>Reklama xabarini yuboring!</b>\n\n"
        "Matn, rasm yoki video yuborishingiz mumkin:"
    )
    await state.set_state(AdminState.waiting_for_broadcast)

@dp.message(AdminState.waiting_for_broadcast)
async def admin_broadcast_process(message: types.Message, state: FSMContext):
    if message.from_user.id not in ADMINS:
        return

    success_count = 0
    for group_id in TARGET_GROUPS:
        try:
            await message.copy_to(chat_id=group_id)
            success_count += 1
        except Exception:
            pass

    await message.answer(f"✅ <b>Reklama {success_count} ta guruhga muvaffaqiyatli yuborildi!</b>")
    await state.clear()

@dp.callback_query(F.data == "admin_ban_user")
async def admin_ban_start(call: types.CallbackQuery, state: FSMContext):
    if call.from_user.id not in ADMINS:
        return
    await call.message.answer("🚫 Ban qilmoqchi bo'lgan foydalanuvchining <b>ID / Username</b> yuboring:")
    await state.set_state(AdminState.waiting_for_ban_target)

@dp.message(AdminState.waiting_for_ban_target)
async def admin_ban_process(message: types.Message, state: FSMContext):
    if message.from_user.id not in ADMINS:
        return

    target = message.text.strip()
    ban_key = int(target) if target.isdigit() else target
    banned_users[ban_key] = target

    if isinstance(ban_key, int):
        for group_id in TARGET_GROUPS:
            try:
                await bot.ban_chat_member(chat_id=group_id, user_id=ban_key)
            except Exception:
                pass

    await message.answer(f"✅ <b>{target}</b> barcha guruhlardan BAN qilindi!")
    await state.clear()

@dp.callback_query(F.data == "admin_unban_list")
async def admin_unban_list(call: types.CallbackQuery):
    if call.from_user.id not in ADMINS:
        return

    if not banned_users:
        await call.message.answer("📜 Hozircha ban bo'lganlar yo'q.")
        return

    buttons = []
    for uid, uname in banned_users.items():
        buttons.append([InlineKeyboardButton(text=f"🔓 {uname}", callback_data=f"unban:{uid}")])

    kb = InlineKeyboardMarkup(inline_keyboard=buttons)
    await call.message.answer("Bandan chiqarish uchun tanlang:", reply_markup=kb)

@dp.callback_query(F.data.startswith("unban:"))
async def admin_unban_process(call: types.CallbackQuery):
    if call.from_user.id not in ADMINS:
        return

    raw_uid = call.data.split("unban:")[1]
    uid = int(raw_uid) if raw_uid.isdigit() else raw_uid

    if uid in banned_users:
        del banned_users[uid]
        if isinstance(uid, int):
            for group_id in TARGET_GROUPS:
                try:
                    await bot.unban_chat_member(chat_id=group_id, user_id=uid)
                except Exception:
                    pass
        await call.message.edit_text("✅ Barcha guruhlardan bandan chiqarildi!")
    else:
        await call.answer("Topilmadi.", show_alert=True)

@dp.callback_query(F.data == "check_sub")
async def check_sub_callback(call: types.CallbackQuery, state: FSMContext):
    if await check_subscription(call.from_user.id):
        await call.message.delete()
        await call.message.answer("✅ Obuna tasdiqlandi! Endi yuk matnini yoki rasmini yuborishingiz mumkin:")
        await state.set_state(PostState.waiting_for_text)
    else:
        await call.answer("❌ Siz hali guruhga qo'shilmadingiz!", show_alert=True)

@dp.message(PostState.waiting_for_text)
async def process_text(message: types.Message, state: FSMContext):
    user_id = message.from_user.id

    if user_id in banned_users:
        await message.answer("⛔️ Siz bloklangansiz!")
        return

    if not await check_subscription(user_id):
        await message.answer("⚠️ Botdan foydalanish uchun guruhga a'zo bo'ling!", reply_markup=get_sub_keyboard())
        return

    if user_id not in ADMINS and user_id in user_last_post_time:
        last_time = user_last_post_time[user_id]
        time_diff = datetime.now() - last_time
        if time_diff < timedelta(minutes=3):
            remaining_seconds = int((timedelta(minutes=3) - time_diff).total_seconds())
            rem_min = remaining_seconds // 60
            rem_sec = remaining_seconds % 60
            time_str = f"{rem_min} daqiqa {rem_sec} soniya" if rem_min > 0 else f"{rem_sec} soniya"
            await message.answer(
                f"⏱ <b>Har 3 daqiqada faqat 1 marta e'lon berishingiz mumkin!</b>\n\n"
                f"Yangi e'lon joylash uchun yana <b>{time_str}</b> kuting."
            )
            return

    posts_count = user_posts_count.get(user_id, 0)

    if user_id not in ADMINS and posts_count > 0 and posts_count % 8 == 0:
        if user_id not in user_add_req:
            user_add_req[user_id] = random.randint(2, 5)

        req_count = user_add_req[user_id]
        await message.answer(
            f"🛑 <b>Diqqat!</b> Siz {posts_count} ta e'lon joyladingiz.\n\n"
            f"Yangi e'lon joylashni davom ettirish uchun guruhlarga kamida <b>{req_count} ta odam</b> qo'shishingiz kerak!\n\n"
            "Odam qo'shib bo'lgach, pastdagi tekshirish tugmasini bosing:",
            reply_markup=get_add_members_keyboard()
        )
        return

    raw_text = message.text or message.caption or ""
    photo_id = message.photo[-1].file_id if message.photo else None

    cleaned = re.sub(PHONE_REGEX, "", raw_text)
    cleaned = re.sub(LINK_REGEX, "", cleaned).strip()

    await state.update_data(cleaned_text=cleaned, photo_id=photo_id)
    await message.answer("Endi murojaat uchun <b>Telefon raqamingizni</b> yuboring (Masalan: +998901234567):")
    await state.set_state(PostState.waiting_for_phone)

@dp.callback_query(F.data == "check_added_members")
async def check_added_members_cb(call: types.CallbackQuery, state: FSMContext):
    user_id = call.from_user.id
    if user_id in user_add_req:
        del user_add_req[user_id]

    await call.message.delete()
    await call.message.answer("✅ Rahmat! Odam qo'shilgani tasdiqlandi. Endi yuk e'lonini yuborishingiz mumkin:")
    await state.set_state(PostState.waiting_for_text)

@dp.message(PostState.waiting_for_phone)
async def process_phone(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    phone_number = message.text.strip()
    data = await state.get_data()
    cleaned_text = data.get("cleaned_text", "")
    photo_id = data.get("photo_id")

    # E'lon tagida Admin va ikkala kanal ko'rsatiladigan qism
    final_caption = (
        f"{cleaned_text}\n\n"
        "_____________________\n"
        "👨‍💻 <b>Admin:</b> @Yusufxonpro1\n"
        "📢 <b>Rasmiy kanalimiz:</b> @YukchiForwarder\n"
        "📢 <b>Rasmiy Kanalimiz:</b> @YukchiForwarderPeople"
    )

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📞 Nomer ko'rish", callback_data=f"show_phone:{phone_number}")],
        [
            InlineKeyboardButton(text="🌐 Support Sayt", url=SUPPORT_SITE_URL),
            InlineKeyboardButton(text="🤖 Botga o'tish", url=f"https://t.me/{BOT_USERNAME}")
        ]
    ])

    try:
        for group_id in TARGET_GROUPS:
            if photo_id:
                await bot.send_photo(
                    chat_id=group_id,
                    photo=photo_id,
                    caption=final_caption,
                    reply_markup=keyboard
                )
            else:
                await bot.send_message(
                    chat_id=group_id,
                    text=final_caption,
                    reply_markup=keyboard
                )

        user_posts_count[user_id] = user_posts_count.get(user_id, 0) + 1
        user_last_post_time[user_id] = datetime.now()

        await message.answer("✅ E'loningiz barcha guruhlarga muvaffaqiyatli joylandi! Yangi e'lon berish uchun matn yoki rasm yuboring.")
    except Exception as e:
        await message.answer(f"❌ Xatolik yuz berdi. Bot guruhlarda admin ekanligini tekshiring.\n{e}")

    await state.clear()

@dp.callback_query(F.data.startswith("show_phone:"))
async def show_phone_handler(call: types.CallbackQuery):
    phone = call.data.split("show_phone:")[1]
    await call.answer(f"📞 Murojaat uchun nomer:\n{phone}", show_alert=True)

@dp.message(lambda message: message.chat.id in TARGET_GROUPS)
async def handle_group_messages(message: types.Message):
    user_id = message.from_user.id

    if user_id in ADMINS:
        return

    text = (message.text or message.caption or "").lower()
    has_spam_word = any(word in text for word in SPAM_WORDS)
    has_link = bool(re.search(LINK_REGEX, text))

    if has_spam_word or has_link:
        try:
            await message.delete()
            for group_id in TARGET_GROUPS:
                try:
                    await bot.ban_chat_member(chat_id=group_id, user_id=user_id)
                except Exception:
                    pass
            banned_users[user_id] = message.from_user.full_name
        except Exception:
            pass
        return

    try:
        group_chat_id = message.chat.id
        await message.delete()

        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🤖 Bot orqali yuk yuborish", url=f"https://t.me/{BOT_USERNAME}")]
        ])

        warn_msg = await message.answer(
            f"❗️ <b>{message.from_user.first_name}</b>, guruhga to'g'ridan-to'g'ri e'lon tashlash taqiqlangan!\n\n"
            "E'lon joylash uchun pastdagi tugma orqali botga o'ting:",
            reply_markup=kb
        )

        asyncio.create_task(delete_message_after_delay(group_chat_id, warn_msg.message_id, 3600))
    except Exception:
        pass

@app.post("/")
async def handle_webhook(request: Request):
    try:
        data = await request.json()
        update = Update.model_validate(data, context={"bot": bot})
        await dp.feed_update(bot, update)
        return {"status": "ok"}
    except Exception as e:
        logging.error(f"Webhook error: {e}")
        return {"status": "error", "message": str(e)}

@app.get("/")
async def root():
    return {"status": "Bot serveri faol va ishlamoqda ff!"}")

ADMINS = [6977836294, 8409259397]
REQUIRED_CHANNEL = "@YukchiForwarder"

# Ikki ta guruh ID raqamlari ro'yxati
TARGET_GROUPS = [-1003968416767, -1003775919755]

SUPPORT_SITE_URL = "https://vercell-flax.vercel.app/"
BOT_USERNAME = "TeleProzona_Bot"

logging.basicConfig(level=logging.INFO)

bot = Bot(
    token=API_TOKEN, 
    default=DefaultBotProperties(parse_mode=ParseMode.HTML)
)

storage = MemoryStorage()
dp = Dispatcher(storage=storage)
app = FastAPI()

user_posts_count = {}     
user_add_req = {}        
banned_users = {}         
user_last_post_time = {}  

class PostState(StatesGroup):
    waiting_for_text = State()
    waiting_for_phone = State()

class AdminState(StatesGroup):
    waiting_for_ban_target = State()
    waiting_for_broadcast = State()

PHONE_REGEX = r'(\+?998\s?\d{2}\s?\d{3}\s?\d{2}\s?\d{2}|\b\d{2}\s?\d{3}\s?\d{2}\s?\d{2}\b|\b\d{9}\b)'
LINK_REGEX = r'(https?://[^\s]+|t\.me/[^\s]+|@[a-zA-Z0-9_]+)'
SPAM_WORDS = ["kanalga", "gruppaga", "o'ting", "oting", "murojaat", "arzon", "aksiya", "reklama", "lichkaga", "manga oting"]

async def check_subscription(user_id: int) -> bool:
    try:
        member = await bot.get_chat_member(chat_id=REQUIRED_CHANNEL, user_id=user_id)
        return member.status in [ChatMemberStatus.CREATOR, ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.MEMBER]
    except Exception:
        return False

async def delete_message_after_delay(chat_id: int, message_id: int, delay_seconds: int = 3600):
    await asyncio.sleep(delay_seconds)
    try:
        await bot.delete_message(chat_id=chat_id, message_id=message_id)
    except Exception:
        pass

def get_sub_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📢 1-Guruhga qo'shilish", url="https://t.me/YukchiForwarder")],
        [InlineKeyboardButton(text="📢 2-Guruhga qo'shilish (@YukchiForwarderPeople)", url="https://t.me/YukchiForwarderPeople")],
        [InlineKeyboardButton(text="🔄 Tekshirish", callback_data="check_sub")]
    ])

def get_add_members_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕ 1-Guruhga odam qo'shish", url="https://t.me/YukchiForwarder")],
        [InlineKeyboardButton(text="➕ 2-Guruhga odam qo'shish", url="https://t.me/YukchiForwarderPeople")],
        [InlineKeyboardButton(text="🔄 Qo'shdim, tekshirish", callback_data="check_added_members")]
    ])

def get_admin_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📢 Reklama yuborish", callback_data="admin_broadcast")],
        [
            InlineKeyboardButton(text="🚫 Ban qilish", callback_data="admin_ban_user"),
            InlineKeyboardButton(text="✅ Bandan chiqarish", callback_data="admin_unban_list")
        ]
    ])

@dp.message(F.text == "/start")
async def start_cmd(message: types.Message, state: FSMContext):
    user_id = message.from_user.id

    if user_id in banned_users:
        await message.answer("⛔️ <b>Siz botdan va guruhlardan bloklangansiz!</b>")
        return

    if user_id in ADMINS:
        await message.answer(
            "👨‍💻 <b>Hush kelibsiz Admin!</b>\n\nBoshqaruv paneli:",
            reply_markup=get_admin_keyboard()
        )

    welcome_text = (
        "<b>Assalomu Alaykum!</b> 😎\n\n"
        "📢 Yukingiz bo‘lsa — guruhlarimizga joylang!\n"
        "🚛 Mashinangiz bo‘lsa — o'zingizga mos yukni toping!\n\n"
        "👨‍💻 <b>Admin:</b> @Yusufxonpro1\n\n"
        "📢 <b>Rasmiy kanalimiz:</b> @YukchiForwarder\n"
        "📢 <b>Rasmiy Kanalimiz:</b> @YukchiForwarderPeople\n\n"
        "<b>E'lon joylash uchun yuk matnini yuboring:</b>"
    )

    is_subscribed = await check_subscription(user_id)
    if not is_subscribed:
        await message.answer(
            f"{welcome_text}\n\n⚠️ <b>Botdan foydalanish uchun avval guruhlarimizga qo'shiling!</b>", 
            reply_markup=get_sub_keyboard()
        )
        return

    await message.answer(welcome_text)
    await state.set_state(PostState.waiting_for_text)

@dp.callback_query(F.data == "admin_broadcast")
async def admin_broadcast_start(call: types.CallbackQuery, state: FSMContext):
    if call.from_user.id not in ADMINS:
        return
    await call.message.answer(
        "📢 <b>Reklama xabarini yuboring!</b>\n\n"
        "Matn, rasm yoki video yuborishingiz mumkin:"
    )
    await state.set_state(AdminState.waiting_for_broadcast)

@dp.message(AdminState.waiting_for_broadcast)
async def admin_broadcast_process(message: types.Message, state: FSMContext):
    if message.from_user.id not in ADMINS:
        return

    success_count = 0
    for group_id in TARGET_GROUPS:
        try:
            await message.copy_to(chat_id=group_id)
            success_count += 1
        except Exception:
            pass

    await message.answer(f"✅ <b>Reklama {success_count} ta guruhga muvaffaqiyatli yuborildi!</b>")
    await state.clear()

@dp.callback_query(F.data == "admin_ban_user")
async def admin_ban_start(call: types.CallbackQuery, state: FSMContext):
    if call.from_user.id not in ADMINS:
        return
    await call.message.answer("🚫 Ban qilmoqchi bo'lgan foydalanuvchining <b>ID / Username</b> yuboring:")
    await state.set_state(AdminState.waiting_for_ban_target)

@dp.message(AdminState.waiting_for_ban_target)
async def admin_ban_process(message: types.Message, state: FSMContext):
    if message.from_user.id not in ADMINS:
        return

    target = message.text.strip()
    ban_key = int(target) if target.isdigit() else target
    banned_users[ban_key] = target

    if isinstance(ban_key, int):
        for group_id in TARGET_GROUPS:
            try:
                await bot.ban_chat_member(chat_id=group_id, user_id=ban_key)
            except Exception:
                pass

    await message.answer(f"✅ <b>{target}</b> barcha guruhlardan BAN qilindi!")
    await state.clear()

@dp.callback_query(F.data == "admin_unban_list")
async def admin_unban_list(call: types.CallbackQuery):
    if call.from_user.id not in ADMINS:
        return

    if not banned_users:
        await call.message.answer("📜 Hozircha ban bo'lganlar yo'q.")
        return

    buttons = []
    for uid, uname in banned_users.items():
        buttons.append([InlineKeyboardButton(text=f"🔓 {uname}", callback_data=f"unban:{uid}")])

    kb = InlineKeyboardMarkup(inline_keyboard=buttons)
    await call.message.answer("Bandan chiqarish uchun tanlang:", reply_markup=kb)

@dp.callback_query(F.data.startswith("unban:"))
async def admin_unban_process(call: types.CallbackQuery):
    if call.from_user.id not in ADMINS:
        return

    raw_uid = call.data.split("unban:")[1]
    uid = int(raw_uid) if raw_uid.isdigit() else raw_uid

    if uid in banned_users:
        del banned_users[uid]
        if isinstance(uid, int):
            for group_id in TARGET_GROUPS:
                try:
                    await bot.unban_chat_member(chat_id=group_id, user_id=uid)
                except Exception:
                    pass
        await call.message.edit_text("✅ Barcha guruhlardan bandan chiqarildi!")
    else:
        await call.answer("Topilmadi.", show_alert=True)

@dp.callback_query(F.data == "check_sub")
async def check_sub_callback(call: types.CallbackQuery, state: FSMContext):
    if await check_subscription(call.from_user.id):
        await call.message.delete()
        await call.message.answer("✅ Obuna tasdiqlandi! Endi yuk matnini yoki rasmini yuborishingiz mumkin:")
        await state.set_state(PostState.waiting_for_text)
    else:
        await call.answer("❌ Siz hali guruhga qo'shilmadingiz!", show_alert=True)

@dp.message(PostState.waiting_for_text)
async def process_text(message: types.Message, state: FSMContext):
    user_id = message.from_user.id

    if user_id in banned_users:
        await message.answer("⛔️ Siz bloklangansiz!")
        return

    if not await check_subscription(user_id):
        await message.answer("⚠️ Botdan foydalanish uchun guruhga a'zo bo'ling!", reply_markup=get_sub_keyboard())
        return

    if user_id not in ADMINS and user_id in user_last_post_time:
        last_time = user_last_post_time[user_id]
        time_diff = datetime.now() - last_time
        if time_diff < timedelta(minutes=3):
            remaining_seconds = int((timedelta(minutes=3) - time_diff).total_seconds())
            rem_min = remaining_seconds // 60
            rem_sec = remaining_seconds % 60
            time_str = f"{rem_min} daqiqa {rem_sec} soniya" if rem_min > 0 else f"{rem_sec} soniya"
            await message.answer(
                f"⏱ <b>Har 3 daqiqada faqat 1 marta e'lon berishingiz mumkin!</b>\n\n"
                f"Yangi e'lon joylash uchun yana <b>{time_str}</b> kuting."
            )
            return

    posts_count = user_posts_count.get(user_id, 0)

    if user_id not in ADMINS and posts_count > 0 and posts_count % 8 == 0:
        if user_id not in user_add_req:
            user_add_req[user_id] = random.randint(2, 5)

        req_count = user_add_req[user_id]
        await message.answer(
            f"🛑 <b>Diqqat!</b> Siz {posts_count} ta e'lon joyladingiz.\n\n"
            f"Yangi e'lon joylashni davom ettirish uchun guruhlarga kamida <b>{req_count} ta odam</b> qo'shishingiz kerak!\n\n"
            "Odam qo'shib bo'lgach, pastdagi tekshirish tugmasini bosing:",
            reply_markup=get_add_members_keyboard()
        )
        return

    raw_text = message.text or message.caption or ""
    photo_id = message.photo[-1].file_id if message.photo else None

    cleaned = re.sub(PHONE_REGEX, "", raw_text)
    cleaned = re.sub(LINK_REGEX, "", cleaned).strip()

    await state.update_data(cleaned_text=cleaned, photo_id=photo_id)
    await message.answer("Endi murojaat uchun <b>Telefon raqamingizni</b> yuboring (Masalan: +998901234567):")
    await state.set_state(PostState.waiting_for_phone)

@dp.callback_query(F.data == "check_added_members")
async def check_added_members_cb(call: types.CallbackQuery, state: FSMContext):
    user_id = call.from_user.id
    if user_id in user_add_req:
        del user_add_req[user_id]

    await call.message.delete()
    await call.message.answer("✅ Rahmat! Odam qo'shilgani tasdiqlandi. Endi yuk e'lonini yuborishingiz mumkin:")
    await state.set_state(PostState.waiting_for_text)

@dp.message(PostState.waiting_for_phone)
async def process_phone(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    phone_number = message.text.strip()
    data = await state.get_data()
    cleaned_text = data.get("cleaned_text", "")
    photo_id = data.get("photo_id")

    # E'lon tagida Admin va ikkala kanal ko'rsatiladigan qism
    final_caption = (
        f"{cleaned_text}\n\n"
        "_____________________\n"
        "👨‍💻 <b>Admin:</b> @Yusufxonpro1\n"
        "📢 <b>Rasmiy kanalimiz:</b> @YukchiForwarder\n"
        "📢 <b>Rasmiy Kanalimiz:</b> @YukchiForwarderPeople"
    )

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📞 Nomer ko'rish", callback_data=f"show_phone:{phone_number}")],
        [
            InlineKeyboardButton(text="🌐 Support Sayt", url=SUPPORT_SITE_URL),
            InlineKeyboardButton(text="🤖 Botga o'tish", url=f"https://t.me/{BOT_USERNAME}")
        ]
    ])

    try:
        for group_id in TARGET_GROUPS:
            if photo_id:
                await bot.send_photo(
                    chat_id=group_id,
                    photo=photo_id,
                    caption=final_caption,
                    reply_markup=keyboard
                )
            else:
                await bot.send_message(
                    chat_id=group_id,
                    text=final_caption,
                    reply_markup=keyboard
                )

        user_posts_count[user_id] = user_posts_count.get(user_id, 0) + 1
        user_last_post_time[user_id] = datetime.now()

        await message.answer("✅ E'loningiz barcha guruhlarga muvaffaqiyatli joylandi! Yangi e'lon berish uchun matn yoki rasm yuboring.")
    except Exception as e:
        await message.answer(f"❌ Xatolik yuz berdi. Bot guruhlarda admin ekanligini tekshiring.\n{e}")

    await state.clear()

@dp.callback_query(F.data.startswith("show_phone:"))
async def show_phone_handler(call: types.CallbackQuery):
    phone = call.data.split("show_phone:")[1]
    await call.answer(f"📞 Murojaat uchun nomer:\n{phone}", show_alert=True)

@dp.message(lambda message: message.chat.id in TARGET_GROUPS)
async def handle_group_messages(message: types.Message):
    user_id = message.from_user.id

    if user_id in ADMINS:
        return

    text = (message.text or message.caption or "").lower()
    has_spam_word = any(word in text for word in SPAM_WORDS)
    has_link = bool(re.search(LINK_REGEX, text))

    if has_spam_word or has_link:
        try:
            await message.delete()
            for group_id in TARGET_GROUPS:
                try:
                    await bot.ban_chat_member(chat_id=group_id, user_id=user_id)
                except Exception:
                    pass
            banned_users[user_id] = message.from_user.full_name
        except Exception:
            pass
        return

    try:
        group_chat_id = message.chat.id
        await message.delete()

        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🤖 Bot orqali yuk yuborish", url=f"https://t.me/{BOT_USERNAME}")]
        ])

        warn_msg = await message.answer(
            f"❗️ <b>{message.from_user.first_name}</b>, guruhga to'g'ridan-to'g'ri e'lon tashlash taqiqlangan!\n\n"
            "E'lon joylash uchun pastdagi tugma orqali botga o'ting:",
            reply_markup=kb
        )

        asyncio.create_task(delete_message_after_delay(group_chat_id, warn_msg.message_id, 3600))
    except Exception:
        pass

@app.post("/")
async def handle_webhook(request: Request):
    try:
        data = await request.json()
        update = Update.model_validate(data, context={"bot": bot})
        await dp.feed_update(bot, update)
        return {"status": "ok"}
    except Exception as e:
        logging.error(f"Webhook error: {e}")
        return {"status": "error", "message": str(e)}

@app.get("/")
async def root():
    return {"status": "Bot serveri faol va ishlamoqda ff!"}
