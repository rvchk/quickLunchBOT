from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Message, CallbackQuery
from typing import Callable, Dict, Any, Awaitable
from collections import defaultdict
from datetime import datetime, timedelta
from loguru import logger

class RateLimitMiddleware(BaseMiddleware):
    def __init__(self, max_requests: int = 10, time_window: int = 60):
        self.max_requests = max_requests
        self.time_window = time_window
        self.user_requests: Dict[int, list[datetime]] = defaultdict(list)
    
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        user_id = None
        if isinstance(event, (Message, CallbackQuery)) and event.from_user:
            user_id = event.from_user.id
        
        if user_id:
            now = datetime.now()
            user_requests = self.user_requests[user_id]
            
            user_requests[:] = [req_time for req_time in user_requests 
                               if now - req_time < timedelta(seconds=self.time_window)]
            
            if len(user_requests) >= self.max_requests:
                logger.warning(f"Rate limit exceeded for user {user_id}")
                if isinstance(event, Message):
                    await event.answer(
                        "⚠️ <b>Слишком много запросов</b>\n\n"
                        "Пожалуйста, подождите немного перед следующим запросом.",
                        parse_mode="HTML"
                    )
                elif isinstance(event, CallbackQuery):
                    await event.answer(
                        "Слишком много запросов. Пожалуйста, подождите.",
                        show_alert=True
                    )
                return
            
            user_requests.append(now)
        
        return await handler(event, data)






