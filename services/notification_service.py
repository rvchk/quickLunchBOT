from aiogram import Bot
from database.database import get_session
from services.user_service import is_admin
from models.user import UserRole
from sqlalchemy import select
from models.user import User
from loguru import logger
from typing import List

async def notify_admins_about_new_order(bot: Bot, order_info: str):
    async for session in get_session():
        result = await session.execute(
            select(User).where(User.role == UserRole.MANAGER)
        )
        admins = list(result.scalars().all())
        
        notification_text = f"🔔 Новый заказ!\n\n{order_info}"
        
        for admin in admins:
            try:
                await bot.send_message(admin.telegram_id, notification_text)
            except Exception as e:
                logger.error(f"Не удалось отправить уведомление админу {admin.telegram_id}: {e}")

async def notify_user_about_order_change(bot: Bot, user_id: int, message: str):
    try:
        await bot.send_message(user_id, message)
    except Exception as e:
        logger.error(f"Не удалось отправить уведомление пользователю {user_id}: {e}")

async def notify_users_about_menu_change(bot: Bot, message: str):
    async for session in get_session():
        from services.user_service import get_all_users
        users = await get_all_users(session)
        
        active_users = [u for u in users if not (hasattr(u, 'is_blocked') and u.is_blocked)]
        
        for user in active_users:
            try:
                await bot.send_message(user.telegram_id, message)
            except Exception as e:
                logger.error(f"Не удалось отправить уведомление пользователю {user.telegram_id}: {e}")

async def notify_user_about_order_status(bot: Bot, user_telegram_id: int, message: str):
    try:
        await bot.send_message(user_telegram_id, message)
    except Exception as e:
        logger.error(f"Не удалось отправить уведомление пользователю {user_telegram_id}: {e}")



