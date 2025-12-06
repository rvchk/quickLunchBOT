import asyncio
import sys
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from loguru import logger
from config.settings import settings
from handlers import start, help, menu, orders, admin, callbacks, edit_order, statistics
from database.database import init_db
from middleware.logging_middleware import LoggingMiddleware
from middleware.error_middleware import ErrorMiddleware
from middleware.unknown_message_middleware import UnknownMessageMiddleware
from middleware.rate_limit_middleware import RateLimitMiddleware
from services.scheduler_service import setup_scheduler
from pathlib import Path

logger.remove()
logger.add(
    sys.stdout,
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan> - <level>{message}</level>",
    level="INFO"
)
logger.add(
    "logs/bot_{time:YYYY-MM-DD}.log",
    rotation="00:00",
    retention="30 days",
    format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function} - {message}",
    level="DEBUG"
)

async def main():
    Path("logs").mkdir(exist_ok=True)
    Path("exports").mkdir(exist_ok=True)
    
    if not settings.BOT_TOKEN:
        logger.error("BOT_TOKEN не установлен в .env файле!")
        return
    
    bot = Bot(token=settings.BOT_TOKEN)
    from config.bot_instance import set_bot
    set_bot(bot)
    dp = Dispatcher(storage=MemoryStorage())
    
    dp.message.middleware(LoggingMiddleware())
    dp.callback_query.middleware(LoggingMiddleware())
    dp.message.middleware(RateLimitMiddleware(max_requests=20, time_window=60))
    dp.callback_query.middleware(RateLimitMiddleware(max_requests=30, time_window=60))
    dp.message.middleware(UnknownMessageMiddleware())
    dp.message.middleware(ErrorMiddleware())
    dp.callback_query.middleware(ErrorMiddleware())
    
    logger.info("Регистрация роутеров...")
    dp.include_router(start.router)
    dp.include_router(help.router)
    dp.include_router(callbacks.router)
    dp.include_router(menu.router)
    dp.include_router(orders.router)
    dp.include_router(edit_order.router)
    dp.include_router(statistics.router)
    dp.include_router(admin.router)
    logger.info("✅ Все роутеры зарегистрированы")
    
    logger.info("Инициализация базы данных...")
    await init_db()
    logger.info("✅ База данных инициализирована")
    
    setup_scheduler(bot)
    logger.info("✅ Планировщик настроен")
    
    logger.info("🚀 Бот запущен и готов к работе!")
    
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())

