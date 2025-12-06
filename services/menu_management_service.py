from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime
from models.dish import Dish
from models.menu import Menu
from utils.cache import clear_cache
from typing import List, Optional, Any

async def add_dish(
    session: AsyncSession, 
    name: str, 
    description: Optional[str], 
    price: float, 
    category: str
) -> Dish:
    dish = Dish(
        name=name,
        description=description,
        price=price,
        category=category,
        available=True
    )
    session.add(dish)
    await session.commit()
    await session.refresh(dish)
    clear_cache("get_dish_categories")
    return dish

async def get_all_dishes(session: AsyncSession) -> List[Dish]:
    result = await session.execute(select(Dish).order_by(Dish.category, Dish.name))
    return list(result.scalars().all())

async def get_dish_by_id(session: AsyncSession, dish_id: int) -> Optional[Dish]:
    result = await session.execute(select(Dish).where(Dish.id == dish_id))
    return result.scalar_one_or_none()

async def update_dish(session: AsyncSession, dish_id: int, **kwargs: Any) -> Optional[Dish]:
    result = await session.execute(select(Dish).where(Dish.id == dish_id))
    dish = result.scalar_one_or_none()
    
    if not dish:
        return None
    
    for key, value in kwargs.items():
        if hasattr(dish, key):
            setattr(dish, key, value)
    
    await session.commit()
    await session.refresh(dish)
    clear_cache("get_dish_categories")
    return dish

async def delete_dish(session: AsyncSession, dish_id: int) -> bool:
    result = await session.execute(select(Dish).where(Dish.id == dish_id))
    dish = result.scalar_one_or_none()
    
    if not dish:
        return False
    
    await session.delete(dish)
    await session.commit()
    clear_cache("get_dish_categories")
    return True

async def load_menu_for_date(
    session: AsyncSession, 
    date: datetime, 
    dish_ids: List[int], 
    quantities: List[int]
) -> List[Menu]:
    date_start = date.replace(hour=0, minute=0, second=0, microsecond=0)
    date_end = date.replace(hour=23, minute=59, second=59, microsecond=999999)
    
    existing_result = await session.execute(
        select(Menu).where(
            Menu.date >= date_start,
            Menu.date <= date_end
        )
    )
    existing_menus = {menu.dish_id: menu for menu in existing_result.scalars().all()}
    
    new_menus = []
    for dish_id, quantity in zip(dish_ids, quantities):
        if dish_id in existing_menus:
            existing_menus[dish_id].available_quantity = quantity
        else:
            menu = Menu(
                date=date,
                dish_id=dish_id,
                available_quantity=quantity
            )
            session.add(menu)
            new_menus.append(menu)
    
    await session.commit()
    for menu in new_menus:
        await session.refresh(menu)
    
    return new_menus + list(existing_menus.values())



