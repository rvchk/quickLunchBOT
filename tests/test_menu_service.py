import pytest
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import StaticPool
from services.menu_management_service import (
    add_dish,
    get_all_dishes,
    update_dish,
    delete_dish,
    load_menu_for_date
)
from services.menu_service import (
    get_menu_for_date,
    get_dish_categories
)
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
async def test_add_dish(test_db):
    async_session = test_db
    
    async with async_session() as session:
        dish = await add_dish(session, "Test Dish", "Test Description", 150.0, "Test Category")
        
        assert dish is not None
        assert dish.name == "Test Dish"
        assert dish.description == "Test Description"
        assert dish.price == 150.0
        assert dish.category == "Test Category"
        assert dish.available is True

@pytest.mark.asyncio
async def test_get_all_dishes(test_db):
    async_session = test_db
    
    async with async_session() as session:
        dish1 = await add_dish(session, "Dish 1", "Desc 1", 100.0, "Category A")
        dish2 = await add_dish(session, "Dish 2", "Desc 2", 200.0, "Category B")
        
        dishes = await get_all_dishes(session)
        
        assert len(dishes) >= 2
        dish_names = [d.name for d in dishes]
        assert "Dish 1" in dish_names
        assert "Dish 2" in dish_names

@pytest.mark.asyncio
async def test_update_dish(test_db):
    async_session = test_db
    
    async with async_session() as session:
        dish = await add_dish(session, "Original Name", "Original Desc", 100.0, "Category")
        
        updated_dish = await update_dish(session, dish.id, name="Updated Name", price=150.0)
        
        assert updated_dish is not None
        assert updated_dish.name == "Updated Name"
        assert updated_dish.price == 150.0
        assert updated_dish.description == "Original Desc"

@pytest.mark.asyncio
async def test_delete_dish(test_db):
    async_session = test_db
    
    async with async_session() as session:
        dish = await add_dish(session, "To Delete", "Desc", 100.0, "Category")
        dish_id = dish.id
        
        success = await delete_dish(session, dish_id)
        assert success is True
        
        dishes = await get_all_dishes(session)
        dish_ids = [d.id for d in dishes]
        assert dish_id not in dish_ids

@pytest.mark.asyncio
async def test_load_menu_for_date(test_db):
    async_session = test_db
    
    async with async_session() as session:
        dish1 = await add_dish(session, "Dish 1", "Desc", 100.0, "Category")
        dish2 = await add_dish(session, "Dish 2", "Desc", 200.0, "Category")
        
        menu_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
        
        menus = await load_menu_for_date(
            session,
            menu_date,
            [dish1.id, dish2.id],
            [10, 20]
        )
        
        assert len(menus) == 2
        menu_dict = {m.dish_id: m.available_quantity for m in menus}
        assert menu_dict[dish1.id] == 10
        assert menu_dict[dish2.id] == 20

@pytest.mark.asyncio
async def test_get_menu_for_date(test_db):
    async_session = test_db
    
    async with async_session() as session:
        dish = await add_dish(session, "Menu Dish", "Desc", 100.0, "Category")
        
        menu_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
        
        await load_menu_for_date(session, menu_date, [dish.id], [5])
        
        menu_items = await get_menu_for_date(session, menu_date)
        
        assert len(menu_items) == 1
        assert menu_items[0][0].id == dish.id
        assert menu_items[0][1].available_quantity == 5

@pytest.mark.asyncio
async def test_get_dish_categories(test_db):
    async_session = test_db
    
    async with async_session() as session:
        await add_dish(session, "Dish 1", "Desc", 100.0, "Category A")
        await add_dish(session, "Dish 2", "Desc", 200.0, "Category B")
        await add_dish(session, "Dish 3", "Desc", 300.0, "Category A")
        
        categories = await get_dish_categories(session)
        
        assert "Category A" in categories
        assert "Category B" in categories









