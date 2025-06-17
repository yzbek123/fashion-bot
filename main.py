import os
import asyncpg
from aiogram import Bot, Dispatcher, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from dotenv import load_dotenv

# Загружаем переменные окружения
load_dotenv()

bot = Bot(token=os.getenv("BOT_TOKEN"))
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)

# Состояния для диалога
class UserData(StatesGroup):
    height = State()
    weight = State()
    style = State()

# Команда /start
@dp.message_handler(commands=["start"])
async def start(message: types.Message):
    await UserData.height.set()
    await message.answer("👋 Привет! Давай подберём одежду. Какой у тебя рост (в см)?")

# Обработка роста
@dp.message_handler(state=UserData.height)
async def process_height(message: types.Message, state: FSMContext):
    if not message.text.isdigit():
        await message.answer("📏 Пожалуйста, введи число (например, 170)!")
        return
    
    async with state.proxy() as data:
        data["height"] = int(message.text)
    
    await UserData.next()
    await message.answer("⚖️ Отлично! Теперь укажи свой вес (в кг):")

# Обработка веса
@dp.message_handler(state=UserData.weight)
async def process_weight(message: types.Message, state: FSMContext):
    if not message.text.isdigit():
        await message.answer("⚖️ Пожалуйста, введи число (например, 65)!")
        return
    
    async with state.proxy() as data:
        data["weight"] = int(message.text)
    
    await UserData.next()
    
    # Клавиатура для выбора стиля
    style_keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    styles = ["👔 Классика", "🏃 Спорт", "👖 Повседневный", "🛹 Уличный"]
    style_keyboard.add(*styles)
    await message.answer("🎨 Выбери стиль:", reply_markup=style_keyboard)

# Обработка стиля и сохранение в БД
@dp.message_handler(state=UserData.style)
async def process_style(message: types.Message, state: FSMContext):
    style_map = {
        "👔 Классика": "classic",
        "🏃 Спорт": "sport",
        "👖 Повседневный": "casual",
        "🛹 Уличный": "street"
    }
    
    style = style_map.get(message.text)
    if not style:
        await message.answer("❌ Пожалуйста, выбери стиль из кнопок ниже!")
        return
    
    async with state.proxy() as data:
        data["style"] = style
        
        # Подключаемся к PostgreSQL
        conn = await asyncpg.connect(os.getenv("DATABASE_URL"))
        await conn.execute(
            "INSERT INTO users (user_id, height, weight, style) VALUES ($1, $2, $3, $4)",
            message.from_user.id, data["height"], data["weight"], data["style"]
        )
        await conn.close()
        
        # Рекомендации (заглушка)
        await message.answer(
            f"✅ Данные сохранены!\n"
            f"📏 Рост: {data['height']} см\n"
            f"⚖️ Вес: {data['weight']} кг\n"
            f"🎨 Стиль: {message.text}\n\n"
            f"Вот твои рекомендации: [здесь будут ссылки на одежду]",
            reply_markup=types.ReplyKeyboardRemove()
        )
    
    await state.finish()

if __name__ == "__main__":
    from aiogram import executor
    executor.start_polling(dp)
