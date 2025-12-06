import pytest
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import StaticPool
from services.order_service import (
    create_order,
    get_user_orders,
    cancel_order,
    update_order_status,
    get_all_orders
)
from services.user_service import get_or_create_user
from services.menu_management_service import add_dish
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

@pytest.mark.asyncio
async def test_create_order(test_db):
    async_session = test_db
    
    async with async_session() as session:
        user = await get_or_create_user(session, 123456, "testuser", "Test User")
        dish = await add_dish(session, "Test Dish", "Description", 100.0, "Test Category")
        
        order_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
        items = [
            {"dish_id": dish.id, "quantity": 2, "price": dish.price}
        ]
        
        order = await create_order(session, user.id, order_date, items)
        
        assert order is not None
        assert order.user_id == user.id
        assert order.status == OrderStatus.PENDING
        assert order.total_amount == 200.0
        assert len(order.items) == 1
        assert order.items[0].dish_id == dish.id
        assert order.items[0].quantity == 2

@pytest.mark.asyncio
async def test_get_user_orders(test_db):
    async_session = test_db
    
    async with async_session() as session:
        user = await get_or_create_user(session, 123456, "testuser", "Test User")
        dish = await add_dish(session, "Test Dish", "Description", 100.0, "Test Category")
        
        order_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
        items = [{"dish_id": dish.id, "quantity": 1, "price": dish.price}]
        
        order1 = await create_order(session, user.id, order_date, items)
        order2 = await create_order(session, user.id, order_date, items)
        
        orders = await get_user_orders(session, user.id)
        
        assert len(orders) == 2
        assert orders[0].id in [order1.id, order2.id]
        assert orders[1].id in [order1.id, order2.id]

@pytest.mark.asyncio
async def test_get_user_orders_with_status_filter(test_db):
    async_session = test_db
    
    async with async_session() as session:
        user = await get_or_create_user(session, 123456, "testuser", "Test User")
        dish = await add_dish(session, "Test Dish", "Description", 100.0, "Test Category")
        
        order_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
        items = [{"dish_id": dish.id, "quantity": 1, "price": dish.price}]
        
        order = await create_order(session, user.id, order_date, items)
        
        pending_orders = await get_user_orders(session, user.id, OrderStatus.PENDING)
        assert len(pending_orders) == 1
        
        await update_order_status(session, order.id, OrderStatus.CONFIRMED)
        
        confirmed_orders = await get_user_orders(session, user.id, OrderStatus.CONFIRMED)
        assert len(confirmed_orders) == 1
        
        pending_orders_after = await get_user_orders(session, user.id, OrderStatus.PENDING)
        assert len(pending_orders_after) == 0

@pytest.mark.asyncio
async def test_cancel_order(test_db):
    async_session = test_db
    
    async with async_session() as session:
        user = await get_or_create_user(session, 123456, "testuser", "Test User")
        dish = await add_dish(session, "Test Dish", "Description", 100.0, "Test Category")
        
        order_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
        items = [{"dish_id": dish.id, "quantity": 1, "price": dish.price}]
        
        order = await create_order(session, user.id, order_date, items)
        
        success = await cancel_order(session, order.id, user.id)
        assert success is True
        
        await session.refresh(order)
        assert order.status == OrderStatus.CANCELLED

@pytest.mark.asyncio
async def test_update_order_status(test_db):
    async_session = test_db
    
    async with async_session() as session:
        user = await get_or_create_user(session, 123456, "testuser", "Test User")
        dish = await add_dish(session, "Test Dish", "Description", 100.0, "Test Category")
        
        order_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
        items = [{"dish_id": dish.id, "quantity": 1, "price": dish.price}]
        
        order = await create_order(session, user.id, order_date, items)
        
        updated_order = await update_order_status(session, order.id, OrderStatus.CONFIRMED)
        
        assert updated_order is not None
        assert updated_order.status == OrderStatus.CONFIRMED

@pytest.mark.asyncio
async def test_get_all_orders_with_filters(test_db):
    async_session = test_db
    
    async with async_session() as session:
        user1 = await get_or_create_user(session, 111, "user1", "User 1")
        user2 = await get_or_create_user(session, 222, "user2", "User 2")
        dish = await add_dish(session, "Test Dish", "Description", 100.0, "Test Category")
        
        today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        tomorrow = today + timedelta(days=1)
        
        items = [{"dish_id": dish.id, "quantity": 1, "price": dish.price}]
        
        order1 = await create_order(session, user1.id, today, items)
        order2 = await create_order(session, user2.id, tomorrow, items)
        
        all_orders = await get_all_orders(session)
        assert len(all_orders) >= 2
        
        today_orders = await get_all_orders(session, date=today)
        assert len(today_orders) >= 1
        
        user1_orders = await get_all_orders(session, user_id=user1.id)
        assert len(user1_orders) >= 1
        assert all(o.user_id == user1.id for o in user1_orders)









