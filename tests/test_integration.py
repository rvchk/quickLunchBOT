import pytest
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import StaticPool
from services.user_service import get_or_create_user, is_admin
from services.menu_management_service import add_dish, load_menu_for_date
from services.order_service import create_order, get_user_orders, cancel_order
from services.menu_service import get_menu_for_date
from models.order import OrderStatus
from models.user import UserRole
from database.base import Base
from config.settings import settings

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

@pytest.mark.asyncio
async def test_full_order_flow(test_db):
    """Тест полного цикла создания заказа"""
    async_session = test_db
    
    async with async_session() as session:
        user = await get_or_create_user(session, 123456, "testuser", "Test User")
        dish1 = await add_dish(session, "Dish 1", "Description 1", 100.0, "Category")
        dish2 = await add_dish(session, "Dish 2", "Description 2", 200.0, "Category")
        
        order_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
        
        await load_menu_for_date(session, order_date, [dish1.id, dish2.id], [10, 10])
        
        items = [
            {"dish_id": dish1.id, "quantity": 2, "price": dish1.price},
            {"dish_id": dish2.id, "quantity": 1, "price": dish2.price}
        ]
        
        order = await create_order(session, user.id, order_date, items)
        
        assert order is not None
        assert order.total_amount == 400.0
        assert len(order.items) == 2
        
        orders = await get_user_orders(session, user.id, OrderStatus.PENDING)
        assert len(orders) == 1
        assert orders[0].id == order.id

@pytest.mark.asyncio
async def test_user_admin_role(test_db):
    """Тест назначения роли администратора"""
    async_session = test_db
    
    original_admin_ids = settings.ADMIN_IDS.copy()
    settings.ADMIN_IDS = [999999]
    
    try:
        async with async_session() as session:
            admin_user = await get_or_create_user(session, 999999, "admin", "Admin User")
            regular_user = await get_or_create_user(session, 111111, "user", "Regular User")
            
            assert await is_admin(session, admin_user.telegram_id) is True
            assert await is_admin(session, regular_user.telegram_id) is False
    finally:
        settings.ADMIN_IDS = original_admin_ids

@pytest.mark.asyncio
async def test_order_cancellation_flow(test_db):
    """Тест процесса отмены заказа"""
    async_session = test_db
    
    async with async_session() as session:
        user = await get_or_create_user(session, 123456, "testuser", "Test User")
        dish = await add_dish(session, "Test Dish", "Description", 100.0, "Category")
        
        order_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
        items = [{"dish_id": dish.id, "quantity": 1, "price": dish.price}]
        
        order = await create_order(session, user.id, order_date, items)
        
        pending_orders = await get_user_orders(session, user.id, OrderStatus.PENDING)
        assert len(pending_orders) == 1
        
        success = await cancel_order(session, order.id, user.id)
        assert success is True
        
        pending_orders_after = await get_user_orders(session, user.id, OrderStatus.PENDING)
        assert len(pending_orders_after) == 0
        
        cancelled_orders = await get_user_orders(session, user.id, OrderStatus.CANCELLED)
        assert len(cancelled_orders) == 1

@pytest.mark.asyncio
async def test_menu_availability_after_order(test_db):
    """Тест доступности меню после создания заказа"""
    async_session = test_db
    
    async with async_session() as session:
        user = await get_or_create_user(session, 123456, "testuser", "Test User")
        dish = await add_dish(session, "Limited Dish", "Description", 100.0, "Category")
        
        order_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
        
        await load_menu_for_date(session, order_date, [dish.id], [5])
        
        menu_before = await get_menu_for_date(session, order_date)
        available_before = menu_before[0][1].available_quantity
        assert available_before == 5
        
        items = [{"dish_id": dish.id, "quantity": 2, "price": dish.price}]
        order = await create_order(session, user.id, order_date, items)
        
        menu_item = menu_before[0][1]
        menu_item.available_quantity -= items[0]["quantity"]
        await session.commit()
        
        menu_after = await get_menu_for_date(session, order_date)
        available_after = menu_after[0][1].available_quantity
        assert available_after == 3









