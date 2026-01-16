from aiogram import Bot, Dispatcher, types
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram.utils import executor
import asyncio
import aiosqlite

TOKEN = "8384817318:AAEq1Vi19ZgOSx3gA_gMSDVGbBNeWxS05g8"  # BotFather-dən aldığın token

bot = Bot(token=TOKEN)
dp = Dispatcher(bot)

# Database init
asyncio.run(init_db())

# /start komandası
@dp.message_handler(commands=["start"])
async def start(message: types.Message):
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(KeyboardButton("Problemi paylaş"))
    kb.add(KeyboardButton("Problemləri gör"))
    await message.answer("Salam! Anonim şəkildə ailəvi problemlərini paylaş və başqalarına kömək et.", reply_markup=kb)

# Problemi yazmaq
user_states = {}

@dp.message_handler(lambda message: message.text == "Problemi paylaş")
async def share_problem(message: types.Message):
    user_states[message.from_user.id] = "waiting_problem"
    await message.answer("Problemini yaz, bütün mesaj anonim qalacaq:")

@dp.message_handler(lambda message: user_states.get(message.from_user.id) == "waiting_problem")
async def save_problem(message: types.Message):
    async with aiosqlite.connect("anon_bot.db") as db:
        await db.execute("INSERT INTO problems (user_id, text) VALUES (?, ?)", (message.from_user.id, message.text))
        await db.commit()
    user_states[message.from_user.id] = None
    await message.answer("Problemin paylaşıldı, digər insanlar sənə kömək mesajı yazacaq.")

# Problemləri görmək
@dp.message_handler(lambda message: message.text == "Problemləri gör")
async def view_problems(message: types.Message):
    async with aiosqlite.connect("anon_bot.db") as db:
        cursor = await db.execute("SELECT id, text FROM problems ORDER BY id DESC LIMIT 5")
        problems = await cursor.fetchall()
    if not problems:
        await message.answer("Heç bir problem yoxdur.")
        return
    for p in problems:
        btn = ReplyKeyboardMarkup(resize_keyboard=True)
        btn.add(KeyboardButton(f"Kömək et {p[0]}"))
        await message.answer(f"Problem #{p[0]}:\n{p[1]}", reply_markup=btn)

# Kömək etmək
@dp.message_handler(lambda message: message.text.startswith("Kömək et"))
async def reply_problem(message: types.Message):
    problem_id = int(message.text.split()[2])
    user_states[message.from_user.id] = f"replying_{problem_id}"
    await message.answer("Cavabını yaz:")

@dp.message_handler(lambda message: user_states.get(message.from_user.id, "").startswith("replying_"))
async def save_reply(message: types.Message):
    problem_id = int(user_states[message.from_user.id].split("_")[1])
    async with aiosqlite.connect("anon_bot.db") as db:
        await db.execute("INSERT INTO replies (problem_id, text) VALUES (?, ?)", (problem_id, message.text))
        # Cavabı problem sahibinə göndər
        cursor = await db.execute("SELECT user_id FROM problems WHERE id=?", (problem_id,))
        row = await cursor.fetchone()
        if row:
            await bot.send_message(row[0], f"Anonim cavab:\n{message.text}")
        await db.commit()
    user_states[message.from_user.id] = None
    await message.answer("Cavab göndərildi.")

executor.start_polling(dp, skip_updates=True)