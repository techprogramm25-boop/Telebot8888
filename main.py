import os
import logging
from fastapi import FastAPI, Request
from aiogram import Bot, Dispatcher, types, F
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, Update

API_TOKEN = os.getenv("BOT_TOKEN", "8735824882:AAGdS6WeHfTz2RenWRYUnNxleNESNXc1F4Y")
ADMINS = [6977836294, 8409259397]

logging.basicConfig(level=logging.INFO)

bot = Bot(token=API_TOKEN, parse_mode=ParseMode.HTML)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

app = FastAPI()

# Guruhlarni saqlash ro'yxati
groups_db = set()

class PostState(StatesGroup):
    waiting_for_content = State()
    waiting_for_decoration = State()
    waiting_for_days = State()
    confirm_publish = State()

def get_decoration_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✨ Bezatish (Ha)", callback_data="decorate_yes"),
            InlineKeyboardButton(text="❌ Oddiy (Yo'q)", callback_data="decorate_no")
        ]
    ])

def get_days_keyboard():
    buttons = []
    row = []
    for i in range(1, 10):
        row.append(InlineKeyboardButton(text=f"{i} kun", callback_data=f"days_{i}"))
        if len(row) == 3:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_confirm_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🚀 Tarqatish", callback_data="confirm_yes"),
            InlineKeyboardButton(text="🚫 Bekor qilish", callback_data="confirm_no")
        ]
    ])

@dp.my_chat_member()
async def bot_added_to_group(update: types.ChatMemberUpdated):
    if update.new_chat_member.status in ["member", "administrator"]:
        groups_db.add(update.chat.id)

@dp.message(F.text == "/start")
async def start_cmd(message: types.Message, state: FSMContext):
    if message.from_user.id not in ADMINS:
        await message.reply("⛔️ Sizga ushbu botdan foydalanish uchun ruxsat berilmagan.")
        return

    await message.answer(
        "<b>@Yusufxonpro1 Siz uchun Tayyor!</b>\n\n"
        "Yuk/E'lon matnini yoki rasmini yuboring:"
    )
    await state.set_state(PostState.waiting_for_content)

@dp.message(PostState.waiting_for_content)
async def process_content(message: types.Message, state: FSMContext):
    await state.update_data(content_message_id=message.message_id, chat_id=message.chat.id)
    await message.answer("Yuk qabul qilindi! Post bezatilsinmi?", reply_markup=get_decoration_keyboard())
    await state.set_state(PostState.waiting_for_decoration)

@dp.callback_query(PostState.waiting_for_decoration)
async def process_decoration(call: types.CallbackQuery, state: FSMContext):
    decorate = call.data == "decorate_yes"
    await state.update_data(decorate=decorate)
    await call.message.edit_text("E'lon necha kun tursin? (1 dan 9 kungacha tanlang):", reply_markup=get_days_keyboard())
    await state.set_state(PostState.waiting_for_days)

@dp.callback_query(PostState.waiting_for_days)
async def process_days(call: types.CallbackQuery, state: FSMContext):
    days = int(call.data.split("_")[1])
    await state.update_data(days=days)
    await call.message.edit_text(f"E'lon <b>{days} kun</b> davomida tarqatiladi. Tasdiqlaysizmi?", reply_markup=get_confirm_keyboard())
    await state.set_state(PostState.confirm_publish)

@dp.callback_query(PostState.confirm_publish)
async def process_confirm(call: types.CallbackQuery, state: FSMContext):
    if call.data == "confirm_no":
        await call.message.edit_text("❌ Tarqatish bekor qilindi. Yangi yuk uchun /start bosing.")
        await state.clear()
        return

    data = await state.get_data()
    days = data['days']
    decorate = data['decorate']
    content_id = data['content_message_id']

    await call.message.edit_text("⏳ Yuk tarqatilmoqda...")

    sent_count = 0
    for group_id in list(groups_db):
        try:
            sent_msg = await bot.forward_message(chat_id=group_id, from_chat_id=call.message.chat.id, message_id=content_id)
            
            if decorate:
                await bot.send_message(
                    group_id, 
                    "📦 <b>YUK E'LONI</b>\n<i>Murojaat uchun adminga yozing.</i>", 
                    reply_to_message_id=sent_msg.message_id
                )
            sent_count += 1
        except Exception:
            continue

    await call.message.answer(f"✅ Yuk muvaffaqiyatli {sent_count} ta guruhga tarqatildi! (Muddati: {days} kun)")
    await state.clear()

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
    return {"status": "Bot ishlamoqda!"}
