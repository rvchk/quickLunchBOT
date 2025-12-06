import asyncio
import sys
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from loguru import logger
from config.settings import settings
from handlers import start, menu, orders, admin, callbacks, edit_order, help, statistics
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

bot_instance = None

async def set_bot_photo(bot: Bot):
    photo_paths = [
        Path("assets/images/chef.png"),
        Path("assets/images/chef.jpg"),
        Path("assets/images/bot_photo.png"),
        Path("assets/images/bot_photo.jpg"),
        Path("images/chef.png"),
        Path("images/chef.jpg"),
        Path("chef.png"),
        Path("chef.jpg"),
    ]
    
    for photo_path in photo_paths:
        if photo_path.exists():
            try:
                file_size = photo_path.stat().st_size
                logger.info(f"Найдена иконка бота: {photo_path} (размер: {file_size/1024:.1f} KB)")
                
                if file_size > 10 * 1024 * 1024:
                    logger.warning(f"Файл {photo_path} слишком большой ({file_size} байт). Максимальный размер: 10MB")
                    continue
                
                logger.info(
                    f"Для установки иконки бота:\n"
                    f"1. Откройте @BotFather в Telegram\n"
                    f"2. Отправьте /mybots\n"
                    f"3. Выберите вашего бота\n"
                    f"4. Нажмите 'Edit Botpic' и загрузите файл: {photo_path.absolute()}\n"
                )
                return
            except Exception as e:
                logger.error(f"Ошибка при проверке файла {photo_path}: {e}")
                continue
    
    logger.info("Иконка бота не найдена. Фото можно установить вручную через @BotFather")

async def main():
    global bot_instance
    
    Path("logs").mkdir(exist_ok=True)
    Path("exports").mkdir(exist_ok=True)
    
    if not settings.BOT_TOKEN:
        logger.error("BOT_TOKEN не установлен в .env файле!")
        return
    
    bot_instance = Bot(token=settings.BOT_TOKEN)
    from config.bot_instance import set_bot
    set_bot(bot_instance)
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
    logger.info("✅ Роутер start зарегистрирован")
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
    
    setup_scheduler(bot_instance)
    logger.info("✅ Планировщик настроен")
    
    await set_bot_photo(bot_instance)
    logger.info("✅ Фото бота проверено")
    
    logger.info("🚀 Бот запущен и готов к работе!")
    logger.info(f"🔑 BOT_TOKEN: {settings.BOT_TOKEN[:20]}...")
    logger.info(f"👤 ADMIN_IDS: {settings.ADMIN_IDS}")
    
    await dp.start_polling(bot_instance)

if __name__ == '__main__':
    asyncio.run(main())

