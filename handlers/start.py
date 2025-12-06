from aiogram import Router
from aiogram.types import Message
from aiogram.filters import Command
from database.database import get_session
from services.user_service import get_or_create_user
from config.settings import settings
from loguru import logger

router = Router()

@router.message(Command("start"))
async def cmd_start(message: Message):
    user_id = message.from_user.id
    username = message.from_user.username or "без username"
    first_name = message.from_user.first_name or "пользователь"
    
    logger.info(f"🔵 ПОЛУЧЕНА КОМАНДА /start от пользователя {user_id} (@{username})")
    
    try:
        user_is_admin = user_id in settings.ADMIN_IDS
        logger.info(f"🔵 Проверка прав администратора: {user_is_admin}")
        
        try:
            async for session in get_session():
                try:
                    user = await get_or_create_user(
                        session,
                        user_id,
                        message.from_user.username,
                        message.from_user.full_name
                    )
                    logger.info(f"🔵 Пользователь {user_id} найден/создан: {user.full_name if user else 'None'}")
                    
                    from services.user_service import is_admin
                    db_admin_check = await is_admin(session, user.telegram_id)
                    user_is_admin = user_is_admin or db_admin_check
                    logger.info(f"🔵 Пользователь {user_id} является администратором: {user_is_admin}")
                    break
                except Exception as e:
                    logger.error(f"🔴 Ошибка при работе с базой данных: {e}", exc_info=True)
                    break
        except Exception as e:
            logger.warning(f"🟡 Не удалось подключиться к базе данных: {e}")
        
        from utils.keyboards import get_main_menu_keyboard
        
        keyboard = get_main_menu_keyboard(is_admin=user_is_admin)
        
        welcome_text = f"""👋 <b>Добро пожаловать!</b>

Привет, <b>{first_name}</b>! 👨‍🍳

Я помогу вам организовать заказы на обед быстро и удобно.

📋 <b>Что я умею:</b>

✨ Создавать и управлять заказами
📊 Просматривать историю заказов
🛒 Управлять корзиной
📅 Выбирать блюда на любую дату

💡 Выберите действие из меню ниже 👇"""
        
        logger.info(f"🔵 Отправка приветственного сообщения пользователю {user_id}")
        sent_message = await message.answer(
            welcome_text,
            reply_markup=keyboard,
            parse_mode="HTML"
        )
        logger.info(f"✅ Приветственное сообщение успешно отправлено пользователю {user_id}, message_id: {sent_message.message_id}")
        
    except Exception as e:
        logger.error(f"🔴 КРИТИЧЕСКАЯ ОШИБКА в обработчике /start: {e}", exc_info=True)
        try:
            await message.answer("👋 Добро пожаловать! Произошла ошибка. Попробуйте позже.")
            logger.info(f"✅ Отправлено сообщение об ошибке пользователю {user_id}")
        except Exception as send_error:
            logger.error(f"🔴 Не удалось отправить даже сообщение об ошибке: {send_error}", exc_info=True)

