"""
Модуль для проверки работоспособности системы
Используется для мониторинга и health checks
"""
from datetime import datetime
from database.database import get_session
from sqlalchemy import text
from loguru import logger

async def check_database_connection() -> tuple[bool, str]:
    """
    Проверяет подключение к базе данных
    
    Returns:
        tuple[bool, str]: (успешно ли подключение, сообщение)
    """
    try:
        async for session in get_session():
            result = await session.execute(text("SELECT 1"))
            result.scalar()
            return True, "База данных доступна"
    except Exception as e:
        logger.error(f"Ошибка подключения к БД: {e}")
        return False, f"Ошибка подключения к БД: {str(e)}"

async def check_system_health() -> dict:
    """
    Проверяет общее состояние системы
    
    Returns:
        dict: Словарь с результатами проверок
    """
    db_status, db_message = await check_database_connection()
    
    return {
        "status": "healthy" if db_status else "unhealthy",
        "timestamp": datetime.now().isoformat(),
        "checks": {
            "database": {
                "status": "ok" if db_status else "error",
                "message": db_message
            }
        }
    }

async def get_system_info() -> dict:
    """
    Возвращает информацию о системе
    
    Returns:
        dict: Информация о системе
    """
    from config.settings import settings
    
    return {
        "bot_token_set": bool(settings.BOT_TOKEN and settings.BOT_TOKEN != "your_bot_token_here"),
        "database_type": "PostgreSQL" if settings.DATABASE_URL.startswith("postgresql") else "SQLite",
        "admin_count": len(settings.ADMIN_IDS),
        "order_deadline": f"{settings.ORDER_DEADLINE_HOUR:02d}:{settings.ORDER_DEADLINE_MINUTE:02d}",
        "daily_report_time": f"{settings.DAILY_REPORT_HOUR:02d}:{settings.DAILY_REPORT_MINUTE:02d}",
        "weekly_report": f"День {settings.WEEKLY_REPORT_DAY}, {settings.WEEKLY_REPORT_HOUR:02d}:{settings.WEEKLY_REPORT_MINUTE:02d}"
    }









