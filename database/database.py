from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.pool import NullPool, QueuePool
from config.settings import settings
from database.base import Base
from loguru import logger

engine = None
async_session = None

async def init_db():
    """
    Инициализация подключения к базе данных
    Поддерживает SQLite (для разработки) и PostgreSQL (для продакшена)
    """
    global engine, async_session
    
    database_url = settings.DATABASE_URL
    
    # Определяем параметры подключения в зависимости от типа БД
    connect_args = {}
    pool_kwargs = {}
    
    if database_url.startswith("sqlite"):
        # SQLite для локальной разработки
        database_url = database_url.replace("sqlite:///", "sqlite+aiosqlite:///")
        connect_args = {"check_same_thread": False}
        logger.info("Используется SQLite база данных (локальная разработка)")
        engine = create_async_engine(
            database_url,
            echo=False,
            poolclass=NullPool,  # SQLite не поддерживает пулы
            connect_args=connect_args
        )
    elif database_url.startswith("postgresql://") or database_url.startswith("postgresql+asyncpg://"):
        # PostgreSQL для продакшена
        if not database_url.startswith("postgresql+asyncpg://"):
            database_url = database_url.replace("postgresql://", "postgresql+asyncpg://")
        
        # Настройки пула для PostgreSQL
        pool_kwargs = {
            "pool_size": 5,
            "max_overflow": 10,
            "pool_pre_ping": True,  # Проверка соединения перед использованием
            "pool_recycle": 3600,   # Переиспользование соединений каждый час
        }
        logger.info("Используется PostgreSQL база данных (продакшен)")
        engine = create_async_engine(
            database_url,
            echo=False,
            poolclass=QueuePool,
            **pool_kwargs
        )
    else:
        logger.warning(f"Неизвестный тип базы данных: {database_url}. Используются стандартные настройки.")
        engine = create_async_engine(database_url, echo=False)
    
    async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    # Создаем таблицы если их нет
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("База данных инициализирована успешно")
    except Exception as e:
        logger.error(f"Ошибка при инициализации базы данных: {e}")
        raise

async def get_session():
    if async_session is None:
        logger.error("База данных не инициализирована! Вызовите init_db() перед использованием.")
        raise RuntimeError("База данных не инициализирована. Вызовите init_db() перед использованием.")
    
    async with async_session() as session:
        try:
            yield session
        except Exception as e:
            await session.rollback()
            logger.error(f"Ошибка в сессии базы данных: {e}", exc_info=True)
            raise

