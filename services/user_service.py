from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from models.user import User, UserRole
from config.settings import settings
from typing import Optional, List, Any

async def get_or_create_user(
    session: AsyncSession, 
    telegram_id: int, 
    username: Optional[str] = None, 
    full_name: Optional[str] = None
) -> User:
    result = await session.execute(select(User).where(User.telegram_id == telegram_id))
    user = result.scalar_one_or_none()
    
    if not user:
        role = UserRole.MANAGER if telegram_id in settings.ADMIN_IDS else UserRole.USER
        user = User(
            telegram_id=telegram_id,
            username=username,
            full_name=full_name,
            role=role
        )
        session.add(user)
        try:
            await session.commit()
            await session.refresh(user)
        except IntegrityError:
            await session.rollback()
            result = await session.execute(select(User).where(User.telegram_id == telegram_id))
            user = result.scalar_one_or_none()
            if not user:
                raise
    else:
        if username and user.username != username:
            user.username = username
        if full_name and user.full_name != full_name:
            user.full_name = full_name
        await session.commit()
    
    return user

async def is_manager(session: AsyncSession, telegram_id: int) -> bool:
    result = await session.execute(
        select(User).where(
            User.telegram_id == telegram_id,
            User.role == UserRole.MANAGER
        )
    )
    user = result.scalar_one_or_none()
    return user is not None

async def is_admin(session: AsyncSession, telegram_id: int) -> bool:
    return await is_manager(session, telegram_id)

async def get_all_users(session: AsyncSession) -> List[User]:
    result = await session.execute(select(User).order_by(User.created_at.desc()))
    return list(result.scalars().all())

async def get_user_by_id(session: AsyncSession, user_id: int) -> Optional[User]:
    result = await session.execute(select(User).where(User.id == user_id))
    return result.scalar_one_or_none()

async def update_user(session: AsyncSession, user_id: int, **kwargs: Any) -> Optional[User]:
    result = await session.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    
    if not user:
        return None
    
    for key, value in kwargs.items():
        if hasattr(user, key):
            setattr(user, key, value)
    
    await session.commit()
    await session.refresh(user)
    return user

async def create_user_with_office(
    session: AsyncSession,
    telegram_id: int,
    full_name: Optional[str] = None,
    username: Optional[str] = None,
    office_id: Optional[int] = None
) -> User:
    result = await session.execute(select(User).where(User.telegram_id == telegram_id))
    existing_user = result.scalar_one_or_none()
    
    if existing_user:
        if full_name:
            existing_user.full_name = full_name
        if username:
            existing_user.username = username
        if office_id is not None:
            existing_user.office_id = office_id
        await session.commit()
        await session.refresh(existing_user)
        return existing_user
    
    user = User(
        telegram_id=telegram_id,
        full_name=full_name,
        username=username,
        office_id=office_id,
        role=UserRole.USER
    )
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return user

async def get_user_by_telegram_id(session: AsyncSession, telegram_id: int) -> Optional[User]:
    result = await session.execute(select(User).where(User.telegram_id == telegram_id))
    return result.scalar_one_or_none()

async def update_user_office(session: AsyncSession, user_id: int, office_id: Optional[int]) -> Optional[User]:
    user = await get_user_by_id(session, user_id)
    if not user:
        return None
    
    user.office_id = office_id
    await session.commit()
    await session.refresh(user)
    return user



