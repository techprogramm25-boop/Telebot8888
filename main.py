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

# Bazalar va xotiralar
banned_users = {}          # {user_id: target_str}
drivers_db = {}            # {user_id: {"name": name, "car": car, "phone": phone}}
curators_db = {}           # {user_id: {"name": name, "phone": phone}}
active_loads = {}          # {load_id: {"user_id": ..., "text": ..., "group_msg_ids": {}, "expire_time": ...}}
load_counter = 0

class UserRoleState(StatesGroup):
    choosing_role = State()
    # Haydovchi holatlari
    driver_get_name = State()
    driver_get_car = State()
    # Kurator holatlari
    curator_get_name = State()
    curator_choice_type = State() # qo'lda yoki tayyor
    # Qo'lda yuk kiritish holatlari
    load_from = State()
    load_to = State()
    load_weight = State()
    load_info = State()
    load_urgency = State()
    load_days = State()
    # Tayyor yuk kiritish
    load_ready_text = State()

class AdminState(StatesGroup):
    waiting_for_ban_target = State()
    waiting_for_unban_target = State()
    waiting_for_broadcast = State()

class ComplaintState(StatesGroup):
    waiting_for_complaint_text = State()

PHONE_REGEX = r'(\+?998\s?\d{2}\s?\d{3}\s?\d{2}\s?\d{2}|\b\d{2}\s?\d{3}\s?\d{2}\s?\d{2}\b|\b\d{9}\b)'
LINK_REGEX = r'(https?://[^\s]+|t\.me/[^\s]+|@[a-zA-Z0-9_]+)'
SPAM_WORDS = ["kanalga", "gruppaga", "o'ting", "oting", "murojaat", "arzon", "aksiya", "reklama", "lichkaga", "manga oting", "http", "t.me"]

# ================= UMUMIY ADMIN KEYBOARD (Faqat ro'yxatlar va boshqaruv) =================
def get_admin_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🚛 Haydovchilar", callback_data="admin_list_drivers"),
            InlineKeyboardButton(text="📦 Kuratorlar", callback_data="admin_list_curators")
        ],
        [InlineKeyboardButton(text="📢 Reklama yuborish", callback_data="admin_broadcast")],
        [
            InlineKeyboardButton(text="🚫 Ban qilish", callback_data="admin_ban_user"),
            InlineKeyboardButton(text="✅ Bandan chiqarish", callback_data="admin_unban_user")
        ]
    ])


# ================= 1-BOT Mantiqi =================

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

@dp1.message(F.text == "/start")
async def start_cmd_bot1(message: types.Message, state: FSMContext):
    await state.clear()
    user_id = message.from_user.id

    if user_id in banned_users:
        await message.answer("⛔️ <b>Siz botdan va guruhlardan bloklangansiz!</b>")
        return

    if user_id in ADMINS:
        await message.answer("👨‍💻 <b>Admin Boshqaruv Paneli:</b>", reply_markup=get_admin_keyboard())

    is_subscribed = await check_subscriptions(user_id)
    if not is_subscribed:
        await message.answer(
            "⚠️ <b>Botdan to'liq foydalanish uchun quyidagi kanallarimizga obuna bo'ling:</b>", 
            reply_markup=get_sub_keyboard()
        )
        return

    # Oq va chiroyli formatdagi start xabari
    role_keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🚛 Haydovchi", callback_data="role_driver")],
        [InlineKeyboardButton(text="📦 Kurator", callback_data="role_curator")]
    ])
    
    start_text = (
        "<b>Assalomu alaykum!</b> Oq yo'l botiga xush kelibsiz. 🌟\n\n"
        "Iltimos, botdagi o'z rolingizni tanlang va qulay tarzda faoliyatingizni boshlang:"
    )
    
    await message.answer(start_text, reply_markup=role_keyboard)
    await state.set_state(UserRoleState.choosing_role)

@dp1.callback_query(F.data == "check_sub")
async def check_sub_callback(call: types.CallbackQuery, state: FSMContext):
    if await check_subscriptions(call.from_user.id):
        await call.message.delete()
        role_keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🚛 Haydovchi", callback_data="role_driver")],
            [InlineKeyboardButton(text="📦 Kurator", callback_data="role_curator")]
        ])
        await call.message.answer("✅ Obuna tasdiqlandi! Marhamat, o'z rolingizni tanlang:", reply_markup=role_keyboard)
        await state.set_state(UserRoleState.choosing_role)
    else:
        await call.answer("❌ Siz hali hamma kanallarga qo'shilmadingiz!", show_alert=True)

# --- HAYDOVCHI QAYDI ---
@dp1.callback_query(F.data == "role_driver", UserRoleState.choosing_role)
async def role_driver_chosen(call: types.CallbackQuery, state: FSMContext):
    await call.message.edit_text("👤 Iltimos, ism-sharifingizni to'liq yuboring:")
    await state.set_state(UserRoleState.driver_get_name)

@dp1.message(UserRoleState.driver_get_name)
async def driver_get_name_handler(message: types.Message, state: FSMContext):
    name = message.text.strip()
    await state.update_data(driver_name=name)
    await message.answer("🚛 Endi mashinangizning nomini to'liqligicha yozib yuboring (masalan: Cobalt, Damas, MAN va h.k.):")
    await state.set_state(UserRoleState.driver_get_car)

@dp1.message(UserRoleState.driver_get_car)
async def driver_get_car_handler(message: types.Message, state: FSMContext):
    car = message.text.strip()
    data = await state.get_data()
    user_id = message.from_user.id
    phone = message.from_user.phone_number or "Telegram akkauntdan olindi"
    
    drivers_db[user_id] = {
        "name": data.get("driver_name"),
        "car": car,
        "username": message.from_user.username,
        "phone": phone
    }
    
    await message.answer(
        f"✅ <b>Tabriklaymiz, muvaffaqiyatli ro'yxatdan o'tdingiz!</b>\n\n"
        f"👤 Ism: {data.get('driver_name')}\n"
        f"🚛 Mashina: {car}\n\n"
        f"Sizga mos keladigan yuklar chiqishi bilan xabar beramiz.",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📢 Kanallarimiz", url="https://t.me/YukchiForwarder")],
            [InlineKeyboardButton(text="🌐 Support Sayt", url=SUPPORT_SITE_URL)]
        ])
    )
    await state.clear()

# --- KURATOR QAYDI ---
@dp1.callback_query(F.data == "role_curator", UserRoleState.choosing_role)
async def role_curator_chosen(call: types.CallbackQuery, state: FSMContext):
    await call.message.edit_text("👤 Iltimos, ism-sharifingizni to'liq yuboring:")
    await state.set_state(UserRoleState.curator_get_name)

@dp1.message(UserRoleState.curator_get_name)
async def curator_get_name_handler(message: types.Message, state: FSMContext):
    name = message.text.strip()
    user_id = message.from_user.id
    phone = message.from_user.phone_number or "Telegram"
    
    curators_db[user_id] = {
        "name": name,
        "username": message.from_user.username,
        "phone": phone
    }
    
    choice_kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✍️ Qo'lda kiritish", callback_data="load_manual")],
        [InlineKeyboardButton(text="⚡️ Tayyor e'lon tashlash", callback_data="load_ready")]
    ])
    await message.answer(f"✅ Xush kelibsiz, kurator <b>{name}</b>!\n\nYukni kiritish usulini tanlang:", reply_markup=choice_kb)
    await state.set_state(UserRoleState.curator_choice_type)

@dp1.callback_query(F.data == "load_manual", UserRoleState.curator_choice_type)
async def load_manual_start(call: types.CallbackQuery, state: FSMContext):
    await call.message.edit_text("📍 Yuk <b>qayerdan</b> jo'naydi? (Shahar / Tuman):")
    await state.set_state(UserRoleState.load_from)

@dp1.message(UserRoleState.load_from)
async def load_from_handler(message: types.Message, state: FSMContext):
    await state.update_data(load_from=message.text.strip())
    await message.answer("🎯 Yuk <b>qayerga</b> boradi? (Shahar / Tuman):")
    await state.set_state(UserRoleState.load_to)

@dp1.message(UserRoleState.load_to)
async def load_to_handler(message: types.Message, state: FSMContext):
    await state.update_data(load_to=message.text.strip())
    await message.answer("⚖️ Qanday mashina va yukning vazni qancha? (masalan: Damas, 1 tonna):")
    await state.set_state(UserRoleState.load_weight)

@dp1.message(UserRoleState.load_weight)
async def load_weight_handler(message: types.Message, state: FSMContext):
    await state.update_data(load_weight=message.text.strip())
    await message.answer("📝 Yuk haqida qisqacha ma'lumot bering:")
    await state.set_state(UserRoleState.load_info)

@dp1.message(UserRoleState.load_info)
async def load_info_handler(message: types.Message, state: FSMContext):
    await state.update_data(load_info=message.text.strip())
    urgency_kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔥 Shoshilinch (Tez kerak)", callback_data="urgency_yes")],
        [InlineKeyboardButton(text="⏳ Uncha shoshilinch emas", callback_data="urgency_no")]
    ])
    await message.answer("⚡️ Yuk qanchalik tez kerak?", reply_markup=urgency_kb)
    await state.set_state(UserRoleState.load_urgency)

@dp1.callback_query(F.data.startswith("urgency_"), UserRoleState.load_urgency)
async def load_urgency_handler(call: types.CallbackQuery, state: FSMContext):
    urgency = "Shoshilinch 🔥" if call.data == "urgency_yes" else "Uncha shoshilinch emas ⏳"
    await state.update_data(load_urgency=urgency)
    await call.message.edit_text("⏳ Bu yuk necha kundan keyin avtomatik o'chirib tashlansin? (Faqat raqam yozing, masalan: 1):")
    await state.set_state(UserRoleState.load_days)

@dp1.message(UserRoleState.load_days)
async def load_days_handler(message: types.Message, state: FSMContext):
    if not message.text.strip().isdigit():
        await message.answer("❌ Iltimos, faqat raqam kiriting (masalan: 1, 2, 3):")
        return
    days = int(message.text.strip())
    await state.update_data(load_days=days)
    
    data = await state.get_data()
    await finalize_and_send_load(message, state, data)

@dp1.callback_query(F.data == "load_ready", UserRoleState.curator_choice_type)
async def load_ready_start(call: types.CallbackQuery, state: FSMContext):
    await call.message.edit_text("📝 Tayyor yuk e'loningiz matnini to'liq yuboring:")
    await state.set_state(UserRoleState.load_ready_text)

@dp1.message(UserRoleState.load_ready_text)
async def load_ready_text_handler(message: types.Message, state: FSMContext):
    text = message.text.strip()
    await state.update_data(load_ready_text=text, load_days=1, load_urgency="Tayyor e'lon")
    data = await state.get_data()
    await finalize_and_send_load(message, state, data)

async def finalize_and_send_load(message: types.Message, state: FSMContext, data: dict):
    user = message.from_user
    global load_counter
    load_counter += 1
    load_id = load_counter
    
    if "load_ready_text" in data:
        main_content = data["load_ready_text"]
    else:
        main_content = (
            f"📍 <b>Qayerdan:</b> {data.get('load_from')}\n"
            f"🎯 <b>Qayerga:</b> {data.get('load_to')}\n"
            f"⚖️ <b>Mashina / Vazni:</b> {data.get('load_weight')}\n"
            f"📌 <b>Ma'lumot:</b> {data.get('load_info')}\n"
            f"⚡️ <b>Holati:</b> {data.get('load_urgency')}"
        )
        
    final_caption = (
        f"📦 <b>YUK E'LONI №{load_id}</b>\n\n"
        f"{main_content}\n\n"
        f"_____________________\n"
        f"👤 <b>Kurator:</b> {user.full_name} (@{user.username or 'yoq'})\n"
        f"👨‍💻 <b>Admin:</b> @Yusufxonpro1\n"
        f"📢 <b>Rasmiy kanallarimiz:</b>\n"
        f"• @YukchiForwarder\n"
        f"• @YukchiForwarderPeople"
    )
    
    days = data.get("load_days", 1)
    expire_time = datetime.now() + timedelta(days=days)
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📞 Nomer ko'rish", callback_data=f"show_curator_phone:{user.id}")],
        [InlineKeyboardButton(text="🚛 Mashinam mos keladi (Qabul qilish)", callback_data=f"accept_load:{load_id}")],
        [InlineKeyboardButton(text="🌐 Support sayt", url=SUPPORT_SITE_URL)],
        [InlineKeyboardButton(text="📢 Botlarga o'tish", url=f"https://t.me/{BOT_USERNAME}")]
    ])
    
    group_msg_ids = {}
    for group_id in TARGET_GROUPS:
        try:
            sent_msg = await bot1.send_message(chat_id=group_id, text=final_caption, reply_markup=keyboard)
            group_msg_ids[group_id] = sent_msg.message_id
        except Exception:
            pass
            
    active_loads[load_id] = {
        "user_id": user.id,
        "text": final_caption,
        "group_msg_ids": group_msg_ids,
        "expire_time": expire_time
    }
    
    await message.answer("✅ Yukingiz guruhga muvaffaqiyatli yuborildi va vaqtli o'chish tizimiga qo'shildi!")
    await state.clear()

@dp1.callback_query(F.data.startswith("show_curator_phone:"))
async def show_curator_phone(call: types.CallbackQuery):
    curator_id = int(call.data.split(":")[1])
    curator = curators_db.get(curator_id)
    phone = curator["phone"] if curator else "Mavjud emas"
    await call.answer(f"📞 Kurator raqami: {phone}", show_alert=True)

@dp1.callback_query(F.data.startswith("accept_load:"))
async def accept_load_handler(call: types.CallbackQuery):
    load_id = int(call.data.split(":")[1])
    user = call.from_user
    driver = drivers_db.get(user.id)
    
    if not driver:
        await call.answer("❌ Siz haydovchi sifatida ro'yxatdan o'tmagansiz! /start bosib Haydovchini tanlang.", show_alert=True)
        return
        
    load = active_loads.get(load_id)
    if not load:
        await call.answer("❌ Bu yuk allaqachon o'chirilgan yoki topilmagan!", show_alert=True)
        return
        
    curator_id = load["user_id"]
    
    try:
        notification_text = (
            f"✅ <b>Yukingizga haydovchi topildi!</b>\n\n"
            f"🚛 <b>Haydovchi:</b> {driver['name']}\n"
            f"🚗 <b>Mashinasi:</b> {driver['car']}\n"
            f"📞 <b>Telefon:</b> {driver['phone']}\n"
            f"👤 <b>Username:</b> @{user.username or 'yoq'}"
        )
        await bot1.send_message(chat_id=curator_id, text=notification_text)
    except Exception:
        pass
        
    await call.answer("✅ Buyurtma qabul qilindi! Kuratorga ma'lumotingiz yuborildi.", show_alert=True)


# ================= AVTOMATIK YUKLARNI O'CHIRISH =================

async def background_load_cleaner():
    while True:
        await asyncio.sleep(60)
        now = datetime.now()
        expired_ids = []
        for load_id, data in active_loads.items():
            if now >= data["expire_time"]:
                expired_ids.append(load_id)
                for group_id, msg_id in data["group_msg_ids"].items():
                    try:
                        await bot1.delete_message(chat_id=group_id, message_id=msg_id)
                    except Exception:
                        pass
        for lid in expired_ids:
            active_loads.pop(lid, None)


# ================= UMUMIY ADMIN CALLBACKS & LOGIC =================

async def handle_broadcast_start(call: types.CallbackQuery, state: FSMContext):
    if call.from_user.id not in ADMINS: return
    await call.message.answer("📢 <b>Reklama xabarini yuboring:</b>")
    await state.set_state(AdminState.waiting_for_broadcast)

async def handle_broadcast_process(message: types.Message, state: FSMContext, bot_instance: Bot):
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

async def handle_ban_start(call: types.CallbackQuery, state: FSMContext):
    if call.from_user.id not in ADMINS: return
    await call.message.answer("🚫 Ban qilmoqchi bo'lgan foydalanuvchi ID yoki Username ni yuboring:")
    await state.set_state(AdminState.waiting_for_ban_target)

async def handle_ban_process(message: types.Message, state: FSMContext):
    if message.from_user.id not in ADMINS: return
    target = message.text.strip()
    ban_key = int(target) if target.isdigit() else target
    banned_users[ban_key] = target
    
    if isinstance(ban_key, int):
        for group_id in TARGET_GROUPS:
            try: 
                await bot1.ban_chat_member(chat_id=group_id, user_id=ban_key)
            except Exception: 
                pass
    await message.answer(f"✅ <b>{target}</b> ban qilindi!")
    await state.clear()

async def handle_unban_start(call: types.CallbackQuery, state: FSMContext):
    if call.from_user.id not in ADMINS: return
    if banned_users:
        banned_list_str = "\n".join([f"• <code>{k}</code>" for k in banned_users.keys()])
        await message.answer(f"📋 <b>Ban qilinganlar:</b>\n{banned_list_str}\n\n✅ Bandan chiqarish uchun ID yoki Username ni yuboring:")
    else:
        await message.answer("✅ Hozircha ban qilinganlar yo'q.")
    await state.set_state(AdminState.waiting_for_unban_target)

async def handle_unban_process(message: types.Message, state: FSMContext):
    if message.from_user.id not in ADMINS: return
    target = message.text.strip()
    unban_key = int(target) if target.isdigit() else target
    
    if unban_key in banned_users:
        del banned_users[unban_key]
    
    if isinstance(unban_key, int):
        for group_id in TARGET_GROUPS:
            try: 
                await bot1.unban_chat_member(chat_id=group_id, user_id=unban_key, only_if_banned=True)
            except Exception: 
                pass
        try:
            await bot1.send_message(chat_id=unban_key, text="🎉 <b>Sizga qo'yilgan ban olib tashlandi!</b>")
        except Exception:
            pass
                
    await message.answer(f"✅ <b>{target}</b> bandan chiqarildi!")
    await state.clear()

# --- Bot 1 admin handlers ---
@dp1.callback_query(F.data == "admin_broadcast")
async def b1_broadcast(call: types.CallbackQuery, state: FSMContext): await handle_broadcast_start(call, state)
@dp1.message(AdminState.waiting_for_broadcast)
async def b1_broadcast_pr(message: types.Message, state: FSMContext): await handle_broadcast_process(message, state, bot1)
@dp1.callback_query(F.data == "admin_ban_user")
async def b1_ban(call: types.CallbackQuery, state: FSMContext): await handle_ban_start(call, state)
@dp1.message(AdminState.waiting_for_ban_target)
async def b1_ban_pr(message: types.Message, state: FSMContext): await handle_ban_process(message, state)
@dp1.callback_query(F.data == "admin_unban_user")
async def b1_unban(call: types.CallbackQuery, state: FSMContext): await handle_unban_start(call, state)
@dp1.message(AdminState.waiting_for_unban_target)
async def b1_unban_pr(message: types.Message, state: FSMContext): await handle_unban_process(message, state)

@dp1.callback_query(F.data == "admin_list_drivers")
async def admin_list_drivers(call: types.CallbackQuery):
    if call.from_user.id not in ADMINS: return
    if not drivers_db:
        await call.message.answer("🚛 Hozircha haydovchilar yo'q.")
        return
    text = "🚛 <b>Haydovchilar ro'yxati:</b>\n\n"
    for uid, d in drivers_db.items():
        text += f"• <b>{d['name']}</b> | {d['car']} | Tel: {d['phone']} (ID: <code>{uid}</code>)\n"
    await call.message.answer(text)

@dp1.callback_query(F.data == "admin_list_curators")
async def admin_list_curators(call: types.CallbackQuery):
    if call.from_user.id not in ADMINS: return
    if not curators_db:
        await call.message.answer("📦 Hozircha kuratorlar yo'q.")
        return
    text = "📦 <b>Kuratorlar ro'yxati:</b>\n\n"
    for uid, c in curators_db.items():
        text += f"• <b>{c['name']}</b> | Tel: {c['phone']} (ID: <code>{uid}</code>)\n"
    await call.message.answer(text)


# ================= 2-BOT (Nazoratchi) Mantiqi =================

def get_complaint_keyboard(is_admin: bool = False):
    buttons = [
        [InlineKeyboardButton(text="⚠️ Shikoyat qilish", callback_data="comp_shikoyat")],
        [InlineKeyboardButton(text="❓ Muammo bildirish", callback_data="comp_muammo")],
        [InlineKeyboardButton(text="🌐 Support Sayt", url=SUPPORT_SITE_URL)],
        [InlineKeyboardButton(text="📢 Botlarga o'tish", url=f"https://t.me/{BOT_USERNAME}")]
    ]
    if is_admin:
        buttons.insert(0, [InlineKeyboardButton(text="⚙️ Admin Panel", callback_data="admin_panel_open")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

@dp2.message(F.text == "/start")
async def start_cmd_bot2(message: types.Message, state: FSMContext):
    await state.clear()
    user_id = message.from_user.id

    if user_id in banned_users:
        await message.answer("⛔️ <b>Siz bloklangansiz!</b>")
        return

    is_admin = user_id in ADMINS
    if is_admin:
        await message.answer("👨‍💻 <b>2-bot Admin Paneli:</b>", reply_markup=get_admin_keyboard())

    await message.answer(
        "🛡 <b>Nazoratchi va Xavfsizlik Boti</b>\n\n"
        "Guruh xavfsizligini ta'minlaydi. Murojaat yoki shikoyatingiz bo'lsa pastdagi tugmani bosing:",
        reply_markup=get_complaint_keyboard(is_admin)
    )

@dp2.callback_query(F.data == "admin_panel_open")
async def bot2_open_admin_panel(call: types.CallbackQuery):
    if call.from_user.id not in ADMINS: return
    await call.message.answer("👨‍💻 <b>2-bot Boshqaruv Paneli:</b>", reply_markup=get_admin_keyboard())

# --- Bot 2 admin handlers ---
@dp2.callback_query(F.data == "admin_broadcast")
async def b2_broadcast(call: types.CallbackQuery, state: FSMContext): await handle_broadcast_start(call, state)
@dp2.message(AdminState.waiting_for_broadcast)
async def b2_broadcast_pr(message: types.Message, state: FSMContext): await handle_broadcast_process(message, state, bot2)
@dp2.callback_query(F.data == "admin_ban_user")
async def b2_ban(call: types.CallbackQuery, state: FSMContext): await handle_ban_start(call, state)
@dp2.message(AdminState.waiting_for_ban_target)
async def b2_ban_pr(message: types.Message, state: FSMContext): await handle_ban_process(message, state)
@dp2.callback_query(F.data == "admin_unban_user")
async def b2_unban(call: types.CallbackQuery, state: FSMContext): await handle_unban_start(call, state)
@dp2.message(AdminState.waiting_for_unban_target)
async def b2_unban_pr(message: types.Message, state: FSMContext): await handle_unban_process(message, state)

@dp2.callback_query(F.data.in_({"comp_shikoyat", "comp_muammo"}))
async def complaint_type_chosen(call: types.CallbackQuery, state: FSMContext):
    c_type = "Shikoyat" if call.data == "comp_shikoyat" else "Muammo"
    await state.update_data(complaint_type=c_type)
    await call.message.answer(f"📝 Iltimos, {c_type.lower()}ingiz matni yoki rasmini yuboring:")
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

    await message.answer(f"✅ {c_type} adminga yuborildi!")
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
        except Exception:
            pass


# ================= Webhooks & Startup =================

@app.on_event("startup")
async def startup_event():
    asyncio.create_task(background_load_cleaner())

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
    return {"status": "Tizim to'liq ishlamoqda!"}
