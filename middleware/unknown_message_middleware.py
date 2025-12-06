from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Message
from aiogram.fsm.context import FSMContext
from typing import Callable, Dict, Any, Awaitable
from loguru import logger

class UnknownMessageMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        # Если это сообщение с текстом (не команда), проверяем состояние
        if isinstance(event, Message) and event.text and not event.text.startswith('/'):
            state: FSMContext = data.get('state')
            if state:
                current_state = await state.get_state()
                # Если есть активное FSM состояние, пропускаем сообщение к обработчикам
                # Обработчики состояний сами решат, что с ним делать
                if current_state:
                    logger.debug(f"User {event.from_user.id} sent text '{event.text[:50]}' during FSM state {current_state} - allowing state handlers to process")
                    return await handler(event, data)
        
        # Выполняем handler для всех остальных случаев
        return await handler(event, data)






