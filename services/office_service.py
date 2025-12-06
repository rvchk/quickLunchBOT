from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from models.office import Office
from typing import List, Optional

async def get_all_offices(session: AsyncSession, active_only: bool = True) -> List[Office]:
    query = select(Office)
    if active_only:
        query = query.where(Office.is_active == True)
    query = query.order_by(Office.name)
    result = await session.execute(query)
    return list(result.scalars().all())

async def get_office_by_id(session: AsyncSession, office_id: int) -> Optional[Office]:
    result = await session.execute(select(Office).where(Office.id == office_id))
    return result.scalar_one_or_none()

async def create_office(session: AsyncSession, name: str, address: Optional[str] = None) -> Office:
    office = Office(name=name, address=address)
    session.add(office)
    await session.commit()
    await session.refresh(office)
    return office

async def update_office(session: AsyncSession, office_id: int, name: Optional[str] = None, 
                       address: Optional[str] = None, is_active: Optional[bool] = None) -> Optional[Office]:
    office = await get_office_by_id(session, office_id)
    if not office:
        return None
    
    if name is not None:
        office.name = name
    if address is not None:
        office.address = address
    if is_active is not None:
        office.is_active = is_active
    
    await session.commit()
    await session.refresh(office)
    return office

async def delete_office(session: AsyncSession, office_id: int) -> bool:
    office = await get_office_by_id(session, office_id)
    if not office:
        return False
    
    await session.delete(office)
    await session.commit()
    return True

