from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from datetime import datetime
from models.dish import Dish
from models.menu import Menu
from utils.cache import cache_result
from typing import List, Tuple, Optional

async def get_menu_for_date(session: AsyncSession, date: datetime) -> List[Tuple[Dish, Menu]]:
    date_start = date.replace(hour=0, minute=0, second=0, microsecond=0)
    date_end = date.replace(hour=23, minute=59, second=59, microsecond=999999)
    
    result = await session.execute(
        select(Menu, Dish)
        .join(Dish, Menu.dish_id == Dish.id)
        .where(
            Menu.date >= date_start,
            Menu.date <= date_end,
            Dish.available == True
        )
        .order_by(Dish.category, Dish.name)
    )
    
    return [(dish, menu) for menu, dish in result.all()]

@cache_result(ttl_seconds=600)
async def get_dish_categories(session: AsyncSession) -> List[str]:
    result = await session.execute(
        select(Dish.category)
        .where(Dish.available == True)
        .distinct()
    )
    return [row[0] for row in result.all() if row[0]]

async def get_dish_by_id(session: AsyncSession, dish_id: int) -> Optional[Dish]:
    result = await session.execute(select(Dish).where(Dish.id == dish_id))
    return result.scalar_one_or_none()

async def get_menu_item(session: AsyncSession, date: datetime, dish_id: int) -> Optional[Menu]:
    date_start = date.replace(hour=0, minute=0, second=0, microsecond=0)
    date_end = date.replace(hour=23, minute=59, second=59, microsecond=999999)
    
    result = await session.execute(
        select(Menu)
        .where(
            Menu.date >= date_start,
            Menu.date <= date_end,
            Menu.dish_id == dish_id
        )
    )
    return result.scalar_one_or_none()








