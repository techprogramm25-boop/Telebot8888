import asyncio
import logging
from aiogram import Bot, Dispatcher, executor, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

# API sozlamalari
API_TOKEN = '8735824882:AAGdS6WeHfTz2RenWRYUnNxleNESNXc1F4Y'

# Faqat ruxsat berilgan adminlar ID ro'yxati
ADMINS = [6977836294, 8409259397]

logging.basicConfig(level=logging.INFO)
bot = Bot(token=API_TOKEN, parse_mode=types.ParseMode.HTML)
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)

# Guruhlarni saqlash uchun baza (ishga tushganda bot admin bo'lgan guruhlar yig'iladi)
groups_db = set()

# FSM (Holatlar)
class PostState(StatesGroup):
    waiting_for_content = State()
    waiting_for_decoration = State()
    waiting_for_days = State()
    confirm_publish = State()

# Inline Tugmalar
def get_decoration_keyboard():
    keyboard = InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        InlineKeyboardButton("✨ Bezatish (Ha)", callback_data="decorate_yes"),
        InlineKeyboardButton("❌ Oddiy (Yo'q)", callback_data="decorate_no")
    )
    return keyboard

def get_days_keyboard():
    keyboard = InlineKeyboardMarkup(row_width=3)
    buttons = [InlineKeyboardButton(f"{i} kun", callback_data=f"days_{i}") for i in range(1, 10)]
    keyboard.add(*buttons)
    return keyboard

def get_confirm_keyboard():
    keyboard = InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        InlineKeyboardButton("🚀 Tarqatish", callback_data="confirm_yes"),
        InlineKeyboardButton("🚫 Bekor qilish", callback_data="confirm_no")
    )
    return keyboard

# Bot guruhga qo'shilganda guruh ID sini eslab qolish
@dp.my_chat_member_handler()
async def bot_added_to_group(update: types.ChatMemberUpdated):
    if update.new_chat_member.status in [types.ChatMemberStatus.MEMBER, types.ChatMemberStatus.ADMINISTRATOR]:
        groups_db.add(update.chat.id)

# START Buyrug'i (Faqat adminlar uchun)
@dp.message_handler(commands=['start'], chat_type=types.ChatType.PRIVATE)
async def start_cmd(message: types.Message):
    if message.from_user.id not in ADMINS:
        await message.reply("⛔️ Sizga ushbu botdan foydalanish uchun ruxsat berilmagan.")
        return

    await message.answer(
        "<b>@Yusufxonpro1 Siz uchun Tayyor!</b>\n\n"
        "Yuk/E'lon matnini yoki rasmini yuboring:"
    )
    await PostState.waiting_for_content.set()

# Yukni qabul qilish
@dp.message_handler(state=PostState.waiting_for_content, content_types=types.ContentTypes.ANY)
async def process_content(message: types.Message, state: FSMContext):
    await state.update_data(content_message_id=message.message_id, chat_id=message.chat.id)
    await message.answer("Yuk qabul qilindi! Post bezatilsinmi?", reply_markup=get_decoration_keyboard())
    await PostState.waiting_for_decoration.set()

# Bezatish tanlovi
@dp.callback_query_handler(state=PostState.waiting_for_decoration)
async def process_decoration(call: types.CallbackQuery, state: FSMContext):
    decorate = call.data == "decorate_yes"
    await state.update_data(decorate=decorate)
    await call.message.edit_text("E'lon necha kun tursin? (1 dan 9 kungacha tanlang):", reply_markup=get_days_keyboard())
    await PostState.waiting_for_days.set()

# Kunni tanlash
@dp.callback_query_handler(state=PostState.waiting_for_days)
async def process_days(call: types.CallbackQuery, state: FSMContext):
    days = int(call.data.split("_")[1])
    await state.update_data(days=days)
    await call.message.edit_text(f"E'lon <b>{days} kun</b> davomida tarqatiladi. Tasdiqlaysizmi?", reply_markup=get_confirm_keyboard())
    await PostState.confirm_publish.set()

# Avto-ochirish funksiyasi
async def auto_delete_job(chat_id, message_id, seconds):
    await asyncio.sleep(seconds)
    try:
        await bot.delete_message(chat_id=chat_id, message_id=message_id)
    except Exception:
        pass

# Tarqatishni tasdiqlash
@dp.callback_query_handler(state=PostState.confirm_publish)
async def process_confirm(call: types.CallbackQuery, state: FSMContext):
    if call.data == "confirm_no":
        await call.message.edit_text("❌ Tarqatish bekor qilindi. Yangi yuk uchun /start bosing.")
        await state.finish()
        return

    data = await state.get_data()
    days = data['days']
    decorate = data['decorate']
    content_id = data['content_message_id']
    delete_after_seconds = days * 86400  # Kunni sekundga aylantirish

    await call.message.edit_text("⏳ Yuk tarqatilmoqda...")

    sent_count = 0
    for group_id in list(groups_db):
        try:
            # Postni o'tkazish/tarqatish
            sent_msg = await bot.forward_message(chat_id=group_id, from_chat_id=call.message.chat.id, message_id=content_id)
            
            if decorate:
                # Agar bezatish tanlangan bo'lsa, ostiga belgi qo'yish
                await bot.send_message(group_id, "📦 <b>YUK E'LONI</b>\n<i>Murojaat uchun adminga yozing.</i>", reply_to_message_id=sent_msg.message_id)

            # Avto-ochirish taymerini yoqish
            asyncio.create_task(auto_delete_job(group_id, sent_msg.message_id, delete_after_seconds))
            sent_count += 1
        except Exception:
            continue

    await call.message.answer(f"✅ Yuk muvaffaqiyatli {sent_count} ta guruh/kanalga tarqatildi va {days} kundan keyin avto-o'chiriladi.")
    await state.finish()

if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
