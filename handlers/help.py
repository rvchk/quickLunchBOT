from aiogram import Router
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from config.settings import settings
from utils.keyboards import get_back_keyboard

router = Router()

@router.message(Command("help"))
async def cmd_help(message: Message):
    help_text = f"""
📖 <b>Помощь</b>

🎯 <b>Основные функции:</b>

🍽️ <b>Создать заказ</b>
   Выберите дату и блюда для заказа

📦 <b>Мои заказы</b>
   Просмотрите ваши текущие заказы

📊 <b>История</b>
   Посмотрите историю всех ваших заказов

⏰ <b>Дедлайн заказа:</b>

До <b>{settings.ORDER_DEADLINE_HOUR:02d}:{settings.ORDER_DEADLINE_MINUTE:02d}</b> дня заказа

⌨️ <b>Команды:</b>

/start - Главное меню
/menu - Просмотр меню
/orders - Мои заказы
/help - Эта справка
/cancel - Отменить текущую операцию

💡 <b>Совет:</b> Используйте кнопки для навигации по боту
    """
    await message.answer(help_text, reply_markup=get_back_keyboard())

@router.message(Command("background"))
async def cmd_background(message: Message):
    """Инструкция по изменению фона чата"""
    background_help = """
🎨 Как изменить фон чата:

1️⃣ Откройте чат с ботом
2️⃣ Нажмите на название чата вверху
3️⃣ Нажмите на иконку фона (или "Chat Background")
4️⃣ Выберите готовый фон или загрузите свой

📱 Альтернативный способ:
• Settings → Appearance → Chat Background

💡 Совет: Выберите светлый фон для лучшей читаемости сообщений бота
    """
    await message.answer(background_help, reply_markup=get_back_keyboard())





