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

# Oddiy xotiralar
drivers_db = {}
curators_db = {}
banned_users = {}

class RoleState(StatesGroup):
    choosing = State()
    driver_name = State()
    driver_car = State()
    curator_name = State()
    curator_text = State()

async def check_sub(user_id: int) -> bool:
    for ch in REQUIRED_CHANNELS:
        try:
            member = await bot1.get_chat_member(chat_id=ch, user_id=user_id)
            if member.status not in [ChatMemberStatus.CREATOR, ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.MEMBER]:
                return False
        except Exception:
            return False
    return True

def get_sub_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📢 1-Kanalga qo'shilish", url="https://t.me/YukchiForwarder")],
        [InlineKeyboardButton(text="📢 2-Kanalga qo'shilish", url="https://t.me/YukchiForwarderPeople")],
        [InlineKeyboardButton(text="🔄 Tekshirish", callback_data="check_sub")]
    ])

# ================= 1-BOT =================
@dp1.message(F.text == "/start")
async def start1(message: types.Message, state: FSMContext):
    await state.clear()
    user_id = message.from_user.id
    
    if user_id in banned_users:
        await message.answer("⛔️ Siz bloklangansiz!")
        return

    if not await check_sub(user_id):
        await message.answer("⚠️ Botdan foydalanish uchun kanallarimizga obuna bo'ling:", reply_markup=get_sub_kb())
        return

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🚛 Haydovchi", callback_data="role_driver")],
        [InlineKeyboardButton(text="📦 Kurator", callback_data="role_curator")]
    ])
    await message.answer("<b>Assalomu alaykum!</b> Oq yo'l botiga xush kelibsiz. 🌟\n\nIltimos, o'z rolingizni tanlang:", reply_markup=kb)
    await state.set_state(RoleState.choosing)

@dp1.callback_query(F.data == "check_sub")
async def check_sub_cb(call: types.CallbackQuery, state: FSMContext):
    if await check_sub(call.from_user.id):
        await call.message.delete()
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🚛 Haydovchi", callback_data="role_driver")],
            [InlineKeyboardButton(text="📦 Kurator", callback_data="role_curator")]
        ])
        await call.message.answer("✅ Obuna tasdiqlandi! Rolingizni tanlang:", reply_markup=kb)
        await state.set_state(RoleState.choosing)
    else:
        await call.answer("❌ Hali hamma kanallarga qo'shilmadingiz!", show_alert=True)

@dp1.callback_query(F.data == "role_driver", RoleState.choosing)
async def r_driver(call: types.CallbackQuery, state: FSMContext):
    await call.message.edit_text("👤 Ism-sharifingizni kiriting:")
    await state.set_state(RoleState.driver_name)

@dp1.message(RoleState.driver_name, F.text)
async def d_name(message: types.Message, state: FSMContext):
    await state.update_data(name=message.text.strip())
    await message.answer("🚛 Mashinangiz rusumini yozing (masalan: Damas, Cobalt):")
    await state.set_state(RoleState.driver_car)

@dp1.message(RoleState.driver_car, F.text)
async def d_car(message: types.Message, state: FSMContext):
    drivers_db[message.from_user.id] = {"name": (await state.get_data())["name"], "car": message.text.strip()}
    await message.answer("✅ Ro'yxatdan o'tdingiz! Endi yuklarni kuzatishingiz mumkin.")
    await state.clear()

@dp1.callback_query(F.data == "role_curator", RoleState.choosing)
async def r_curator(call: types.CallbackQuery, state: FSMContext):
    await call.message.edit_text("👤 Kurator ism-sharifini kiriting:")
    await state.set_state(RoleState.curator_name)

@dp1.message(RoleState.curator_name, F.text)
async def c_name(message: types.Message, state: FSMContext):
    await state.update_data(c_name=message.text.strip())
    await message.answer("📝 Tayyor yuk e'loningiz matnini to'liq yuboring:")
    await state.set_state(RoleState.curator_text)

@dp1.message(RoleState.curator_text, F.text)
async def c_text(message: types.Message, state: FSMContext):
    data = await state.get_data()
    text = f"📦 <b>YUK E'LONI</b>\n\n{message.text.strip()}\n\n👤 <b>Kurator:</b> {data['c_name']}"
    
    for g_id in TARGET_GROUPS:
        try:
            await bot1.send_message(chat_id=g_id, text=text)
        except:
            pass
    await message.answer("✅ Yuk e'loni guruhlarga yuborildi!")
    await state.clear()


# ================= 2-BOT (Nazoratchi) =================
@dp2.message(F.text == "/start")
async def start2(message: types.Message, state: FSMContext):
    await state.clear()
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⚠️ Shikoyat qilish", callback_data="shikoyat")],
        [InlineKeyboardButton(text="🌐 Support", url=SUPPORT_SITE_URL)]
    ])
    await message.answer("🛡 <b>Nazoratchi Bot</b>\n\nShikoyatingiz bo'lsa tugmani bosing:", reply_markup=kb)

@dp2.callback_query(F.data == "shikoyat")
async def shikoyat_cb(call: types.CallbackQuery):
    await call.message.answer("📝 Shikoyat yoki taklifingizni yozib yuboring, adminga yetkazamiz:")


# ================= WEBHOOKS =================
@app.post(f"/webhook/bot1/{API_TOKEN_1}")
async def wh1(request: Request):
    try:
        update = Update.model_validate(await request.json(), context={"bot": bot1})
        await dp1.feed_update(bot1, update)
        return {"status": "ok"}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.post(f"/webhook/bot2/{API_TOKEN_2}")
async def wh2(request: Request):
    try:
        update = Update.model_validate(await request.json(), context={"bot": bot2})
        await dp2.feed_update(bot2, update)
        return {"status": "ok"}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.get("/")
async def root():
    return {"status": "Bot ishlayapti!"}
