from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from models.order_deadline import OrderDeadline
from datetime import datetime
from typing import List, Optional

async def get_deadline_for_date(session: AsyncSession, date: datetime, 
                                office_id: Optional[int] = None,
                                cafe_id: Optional[int] = None) -> Optional[OrderDeadline]:
    date_start = date.replace(hour=0, minute=0, second=0, microsecond=0)
    date_end = date.replace(hour=23, minute=59, second=59, microsecond=999999)
    
    query = select(OrderDeadline).where(
        and_(
            OrderDeadline.date >= date_start,
            OrderDeadline.date <= date_end,
            OrderDeadline.is_active == True
        )
    )
    
    if office_id:
        query = query.where(OrderDeadline.office_id == office_id)
    if cafe_id:
        query = query.where(OrderDeadline.cafe_id == cafe_id)
    
    query = query.order_by(OrderDeadline.deadline_time.desc())
    result = await session.execute(query)
    return result.scalar_one_or_none()

async def create_deadline(session: AsyncSession, date: datetime, deadline_time: datetime,
                         office_id: Optional[int] = None, cafe_id: Optional[int] = None) -> OrderDeadline:
    deadline = OrderDeadline(
        date=date,
        deadline_time=deadline_time,
        office_id=office_id,
        cafe_id=cafe_id
    )
    session.add(deadline)
    await session.commit()
    await session.refresh(deadline)
    return deadline

async def get_all_deadlines(session: AsyncSession, active_only: bool = True) -> List[OrderDeadline]:
    query = select(OrderDeadline)
    if active_only:
        query = query.where(OrderDeadline.is_active == True)
    query = query.order_by(OrderDeadline.date.desc(), OrderDeadline.deadline_time.desc())
    result = await session.execute(query)
    return list(result.scalars().all())

async def update_deadline(session: AsyncSession, deadline_id: int,
                         deadline_time: Optional[datetime] = None,
                         is_active: Optional[bool] = None) -> Optional[OrderDeadline]:
    result = await session.execute(select(OrderDeadline).where(OrderDeadline.id == deadline_id))
    deadline = result.scalar_one_or_none()
    if not deadline:
        return None
    
    if deadline_time is not None:
        deadline.deadline_time = deadline_time
    if is_active is not None:
        deadline.is_active = is_active
    
    await session.commit()
    await session.refresh(deadline)
    return deadline

async def delete_deadline(session: AsyncSession, deadline_id: int) -> bool:
    result = await session.execute(select(OrderDeadline).where(OrderDeadline.id == deadline_id))
    deadline = result.scalar_one_or_none()
    if not deadline:
        return False
    
    await session.delete(deadline)
    await session.commit()
    return True

