from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Message, CallbackQuery
from loguru import logger
from typing import Callable, Dict, Any, Awaitable

class ErrorMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        try:
            return await handler(event, data)
        except Exception as e:
            logger.error(f"Error in handler: {e}", exc_info=True)
            
            if isinstance(event, Message):
                try:
                    await event.answer(
                        "Произошла ошибка при обработке запроса. "
                        "Попробуйте позже или обратитесь к администратору."
                    )
                except Exception as inner_e:
                    logger.error(f"Error in error handler: {inner_e}", exc_info=True)
            elif isinstance(event, CallbackQuery):
                try:
                    error_str = str(e)
                    if "message is not modified" in error_str.lower():
                        await event.answer()
                        return
                    
                    await event.answer(
                        "Произошла ошибка при обработке запроса. "
                        "Попробуйте позже или обратитесь к администратору.",
                        show_alert=True
                    )
                except Exception as inner_e:
                    logger.error(f"Error in error handler: {inner_e}", exc_info=True)
            return None








