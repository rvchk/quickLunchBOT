from functools import wraps
from typing import Callable, Awaitable, Any
from aiogram.types import Message, CallbackQuery
from database.database import get_session
from services.user_service import is_admin

def admin_required(func: Callable) -> Callable:
    @wraps(func)
    async def wrapper(event: Message | CallbackQuery, *args, **kwargs):
        user_id = event.from_user.id if event.from_user else None
        if not user_id:
            if isinstance(event, Message):
                await event.answer("Ошибка: не удалось определить пользователя")
            elif isinstance(event, CallbackQuery):
                await event.answer("Ошибка: не удалось определить пользователя", show_alert=True)
            return
        
        async for session in get_session():
            if not await is_admin(session, user_id):
                if isinstance(event, Message):
                    await event.answer("У вас нет прав администратора")
                elif isinstance(event, CallbackQuery):
                    await event.answer("У вас нет прав администратора", show_alert=True)
                return
        
        return await func(event, *args, **kwargs)
    
    return wrapper






