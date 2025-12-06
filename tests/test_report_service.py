import pytest
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import StaticPool
from services.report_service import (
    get_orders_summary,
    get_dish_statistics,
    get_user_statistics
)
from services.user_service import get_or_create_user
from services.menu_management_service import add_dish
from services.order_service import create_order, update_order_status
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
async def test_get_orders_summary(test_db):
    async_session = test_db
    
    async with async_session() as session:
        user1 = await get_or_create_user(session, 111, "user1", "User 1")
        user2 = await get_or_create_user(session, 222, "user2", "User 2")
        dish = await add_dish(session, "Test Dish", "Description", 100.0, "Category")
        
        today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        items = [{"dish_id": dish.id, "quantity": 1, "price": dish.price}]
        
        order1 = await create_order(session, user1.id, today, items)
        order2 = await create_order(session, user2.id, today, items)
        
        summary = await get_orders_summary(session, today)
        
        assert summary["total_orders"] == 2
        assert summary["unique_users"] == 2
        assert summary["total_amount"] == 200.0

@pytest.mark.asyncio
async def test_get_dish_statistics(test_db):
    async_session = test_db
    
    async with async_session() as session:
        user = await get_or_create_user(session, 123456, "testuser", "Test User")
        dish1 = await add_dish(session, "Dish 1", "Desc", 100.0, "Category")
        dish2 = await add_dish(session, "Dish 2", "Desc", 200.0, "Category")
        
        today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        
        items1 = [{"dish_id": dish1.id, "quantity": 2, "price": dish1.price}]
        items2 = [{"dish_id": dish2.id, "quantity": 1, "price": dish2.price}]
        
        await create_order(session, user.id, today, items1)
        await create_order(session, user.id, today, items2)
        
        stats = await get_dish_statistics(session, today)
        
        assert len(stats) == 2
        dish_stats = {s["name"]: s for s in stats}
        assert "Dish 1" in dish_stats
        assert dish_stats["Dish 1"]["quantity"] == 2
        assert dish_stats["Dish 1"]["revenue"] == 200.0
        assert dish_stats["Dish 2"]["quantity"] == 1
        assert dish_stats["Dish 2"]["revenue"] == 200.0

@pytest.mark.asyncio
async def test_get_user_statistics(test_db):
    async_session = test_db
    
    async with async_session() as session:
        user1 = await get_or_create_user(session, 111, "user1", "User 1")
        user2 = await get_or_create_user(session, 222, "user2", "User 2")
        dish = await add_dish(session, "Test Dish", "Description", 100.0, "Category")
        
        today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        items = [{"dish_id": dish.id, "quantity": 1, "price": dish.price}]
        
        order1 = await create_order(session, user1.id, today, items)
        order2 = await create_order(session, user1.id, today, items)
        order3 = await create_order(session, user2.id, today, items)
        
        await update_order_status(session, order1.id, OrderStatus.CONFIRMED)
        await update_order_status(session, order2.id, OrderStatus.CONFIRMED)
        await update_order_status(session, order3.id, OrderStatus.CONFIRMED)
        
        stats = await get_user_statistics(session, today)
        
        assert len(stats) == 2
        user_stats = {s["name"]: s for s in stats}
        assert "User 1" in user_stats or "user1" in user_stats
        assert "User 2" in user_stats or "user2" in user_stats
        
        user1_stat = next(s for s in stats if s["name"] in ["User 1", "user1"])
        assert user1_stat["orders_count"] == 2
        assert user1_stat["total_amount"] == 200.0
        assert user1_stat["avg_order"] == 100.0









