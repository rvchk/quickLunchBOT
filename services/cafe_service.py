from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from models.cafe import Cafe
from models.cafe_menu import CafeMenu
from datetime import datetime
from typing import List, Optional

async def get_all_cafes(session: AsyncSession, office_id: Optional[int] = None, active_only: bool = True) -> List[Cafe]:
    query = select(Cafe)
    if active_only:
        query = query.where(Cafe.is_active == True)
    if office_id:
        query = query.where(Cafe.office_id == office_id)
    query = query.order_by(Cafe.name)
    result = await session.execute(query)
    return list(result.scalars().all())

async def get_cafe_by_id(session: AsyncSession, cafe_id: int) -> Optional[Cafe]:
    result = await session.execute(select(Cafe).where(Cafe.id == cafe_id))
    return result.scalar_one_or_none()

async def create_cafe(session: AsyncSession, name: str, office_id: Optional[int] = None, 
                      contact_info: Optional[str] = None) -> Cafe:
    cafe = Cafe(name=name, office_id=office_id, contact_info=contact_info)
    session.add(cafe)
    await session.commit()
    await session.refresh(cafe)
    return cafe

async def update_cafe(session: AsyncSession, cafe_id: int, name: Optional[str] = None,
                     office_id: Optional[int] = None, contact_info: Optional[str] = None,
                     is_active: Optional[bool] = None) -> Optional[Cafe]:
    cafe = await get_cafe_by_id(session, cafe_id)
    if not cafe:
        return None
    
    if name is not None:
        cafe.name = name
    if office_id is not None:
        cafe.office_id = office_id
    if contact_info is not None:
        cafe.contact_info = contact_info
    if is_active is not None:
        cafe.is_active = is_active
    
    await session.commit()
    await session.refresh(cafe)
    return cafe

async def delete_cafe(session: AsyncSession, cafe_id: int) -> bool:
    cafe = await get_cafe_by_id(session, cafe_id)
    if not cafe:
        return False
    
    await session.delete(cafe)
    await session.commit()
    return True

async def get_cafe_menu_for_date(session: AsyncSession, cafe_id: int, date: datetime) -> List[CafeMenu]:
    date_start = date.replace(hour=0, minute=0, second=0, microsecond=0)
    date_end = date.replace(hour=23, minute=59, second=59, microsecond=999999)
    
    query = select(CafeMenu).where(
        and_(
            CafeMenu.cafe_id == cafe_id,
            CafeMenu.date >= date_start,
            CafeMenu.date <= date_end
        )
    )
    result = await session.execute(query)
    return list(result.scalars().all())

async def load_cafe_menu_for_date(session: AsyncSession, cafe_id: int, date: datetime,
                                  dish_ids: List[int], quantities: List[int]) -> List[CafeMenu]:
    date_start = date.replace(hour=0, minute=0, second=0, microsecond=0)
    
    menu_items = []
    for dish_id, quantity in zip(dish_ids, quantities):
        existing = await session.execute(
            select(CafeMenu).where(
                and_(
                    CafeMenu.cafe_id == cafe_id,
                    CafeMenu.dish_id == dish_id,
                    CafeMenu.date >= date_start,
                    CafeMenu.date < date_start.replace(day=date_start.day + 1)
                )
            )
        )
        existing_item = existing.scalar_one_or_none()
        
        if existing_item:
            existing_item.available_quantity = quantity
            menu_items.append(existing_item)
        else:
            menu_item = CafeMenu(
                cafe_id=cafe_id,
                dish_id=dish_id,
                date=date_start,
                available_quantity=quantity
            )
            session.add(menu_item)
            menu_items.append(menu_item)
    
    await session.commit()
    for item in menu_items:
        await session.refresh(item)
    return menu_items

