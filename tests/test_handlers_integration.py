"""
Интеграционные тесты для handlers
Тестируют взаимодействие handlers с базой данных и сервисами
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timedelta
from aiogram.types import User, Message, CallbackQuery, Chat
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import StaticPool
from services.user_service import get_or_create_user
from services.menu_management_service import add_dish, load_menu_for_date
from services.order_service import create_order
from models.order import OrderStatus
from database.base import Base

@pytest.fixture
async def test_db():
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool
    )
    async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    yield async_session
    
    await engine.dispose()

@pytest.fixture
def mock_user():
    """Создает мок пользователя Telegram"""
    user = User(
        id=123456,
        is_bot=False,
        first_name="Test",
        username="testuser",
        language_code="ru"
    )
    return user

@pytest.fixture
def mock_message(mock_user):
    """Создает мок сообщения"""
    chat = Chat(id=123456, type="private")
    message = Message(
        message_id=1,
        date=datetime.now(),
        chat=chat,
        from_user=mock_user,
        text="/start"
    )
    return message

@pytest.fixture
def mock_callback(mock_user):
    """Создает мок callback query"""
    chat = Chat(id=123456, type="private")
    message = Message(
        message_id=1,
        date=datetime.now(),
        chat=chat,
        from_user=mock_user
    )
    callback = CallbackQuery(
        id="test_callback",
        from_user=mock_user,
        message=message,
        data="test_data"
    )
    return callback

@pytest.mark.asyncio
async def test_start_command_creates_user(test_db, mock_message):
    """Тест создания пользователя при команде /start"""
    from handlers.start import cmd_start
    
    async_session = test_db
    
    with patch('handlers.start.get_session') as mock_get_session:
        mock_session = AsyncMock()
        mock_get_session.return_value.__aiter__.return_value = [mock_session]
        
        with patch('handlers.start.get_or_create_user') as mock_get_user:
            mock_user_obj = MagicMock()
            mock_user_obj.role.value = "user"
            mock_get_user.return_value = mock_user_obj
            
            await cmd_start(mock_message)
            
            mock_get_user.assert_called_once()

@pytest.mark.asyncio
async def test_order_creation_flow_integration(test_db):
    """Интеграционный тест полного цикла создания заказа"""
    async_session = test_db
    
    async with async_session() as session:
        user = await get_or_create_user(session, 123456, "testuser", "Test User")
        dish = await add_dish(session, "Test Dish", "Description", 100.0, "Category")
        
        order_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
        await load_menu_for_date(session, order_date, [dish.id], [10])
        
        items = [{"dish_id": dish.id, "quantity": 2, "price": dish.price}]
        order = await create_order(session, user.id, order_date, items)
        
        assert order is not None
        assert order.user_id == user.id
        assert order.status == OrderStatus.PENDING
        assert order.total_amount == 200.0
        assert len(order.items) == 1
        assert order.items[0].quantity == 2

@pytest.mark.asyncio
async def test_menu_loading_integration(test_db):
    """Интеграционный тест загрузки меню"""
    async_session = test_db
    
    async with async_session() as session:
        dish1 = await add_dish(session, "Dish 1", "Desc", 100.0, "Category A")
        dish2 = await add_dish(session, "Dish 2", "Desc", 200.0, "Category B")
        
        menu_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
        
        menus = await load_menu_for_date(
            session,
            menu_date,
            [dish1.id, dish2.id],
            [5, 10]
        )
        
        assert len(menus) == 2
        
        from services.menu_service import get_menu_for_date
        menu_items = await get_menu_for_date(session, menu_date)
        
        assert len(menu_items) == 2
        dish_ids = {item[0].id for item in menu_items}
        assert dish1.id in dish_ids
        assert dish2.id in dish_ids









