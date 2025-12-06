from aiogram import BaseMiddleware
from aiogram.types import TelegramObject
from loguru import logger
from typing import Callable, Dict, Any, Awaitable

class LoggingMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        if hasattr(event, 'from_user') and event.from_user:
            user = event.from_user
            logger.info(
                f"User {user.id} (@{user.username}) - "
                f"Action: {type(event).__name__}"
            )
        return await handler(event, data)













