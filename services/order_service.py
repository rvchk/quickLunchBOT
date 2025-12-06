"""
Сервис для работы с заказами
Обеспечивает создание, получение, обновление и отмену заказов
"""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, String
from sqlalchemy.orm import selectinload
from datetime import datetime
from models.order import Order, OrderItem, OrderStatus
from models.user import User
from models.dish import Dish
from typing import List, Dict, Optional, Any

async def create_order(
    session: AsyncSession, 
    user_id: int, 
    order_date: datetime, 
    items: List[Dict[str, Any]],
    cafe_id: Optional[int] = None,
    delivery_time: Optional[datetime] = None,
    delivery_type: Optional[Any] = None
) -> Order:
    """
    Создает новый заказ с защитой от race condition
    
    Args:
        session: Сессия базы данных
        user_id: ID пользователя
        order_date: Дата заказа
        items: Список позиций заказа [{"dish_id": int, "quantity": int, "price": float}]
        cafe_id: ID кафе (опционально)
        delivery_time: Время доставки (опционально)
        delivery_type: Тип доставки (опционально)
    
    Returns:
        Order: Созданный заказ
    
    Raises:
        ValueError: Если блюдо недоступно в нужном количестве
    """
    from sqlalchemy import select
    from models.cafe_menu import CafeMenu
    
    date_start = order_date.replace(hour=0, minute=0, second=0, microsecond=0)
    date_end = order_date.replace(hour=23, minute=59, second=59, microsecond=999999)
    
    if cafe_id:
        for item in items:
            result = await session.execute(
                select(CafeMenu)
                .where(
                    CafeMenu.cafe_id == cafe_id,
                    CafeMenu.dish_id == item['dish_id'],
                    CafeMenu.date >= date_start,
                    CafeMenu.date <= date_end
                )
                .with_for_update()
            )
            menu_item = result.scalar_one_or_none()
            
            if not menu_item:
                raise ValueError(f"Блюдо с ID {item['dish_id']} не найдено в меню кафе на эту дату")
            
            if menu_item.available_quantity < item['quantity']:
                raise ValueError(
                    f"Доступно только {menu_item.available_quantity} порций блюда с ID {item['dish_id']}, "
                    f"запрошено {item['quantity']}"
                )
            
            menu_item.available_quantity -= item['quantity']
    
    total_amount = sum(item['price'] * item['quantity'] for item in items)
    
    order = Order(
        user_id=user_id,
        cafe_id=cafe_id,
        order_date=order_date,
        delivery_time=delivery_time,
        delivery_type=delivery_type,
        status=OrderStatus.PENDING,
        total_amount=total_amount
    )
    session.add(order)
    await session.flush()
    
    for item in items:
        order_item = OrderItem(
            order_id=order.id,
            dish_id=item['dish_id'],
            quantity=item['quantity'],
            price=item['price']
        )
        session.add(order_item)
    
    await session.commit()
    await session.refresh(order)
    return order

async def get_user_orders(
    session: AsyncSession, 
    user_id: int, 
    status: Optional[OrderStatus] = None, 
    date_from: Optional[datetime] = None, 
    date_to: Optional[datetime] = None
) -> List[Order]:
    """
    Получает список заказов пользователя с опциональными фильтрами
    
    Args:
        session: Сессия базы данных
        user_id: ID пользователя
        status: Фильтр по статусу (опционально)
        date_from: Начальная дата для фильтрации (опционально)
        date_to: Конечная дата для фильтрации (опционально)
    
    Returns:
        list[Order]: Список заказов пользователя
    """
    from models.order import OrderItem
    query = select(Order).options(
        selectinload(Order.items).selectinload(OrderItem.dish),
        selectinload(Order.user)
    ).where(Order.user_id == user_id)
    if status:
        query = query.where(Order.status == status)
    if date_from:
        query = query.where(Order.order_date >= date_from)
    if date_to:
        query = query.where(Order.order_date <= date_to)
    query = query.order_by(Order.order_date.desc())
    
    result = await session.execute(query)
    return list(result.scalars().all())

async def search_user_orders_by_dish(session: AsyncSession, user_id: int, dish_name: str) -> List[Order]:
    """
    Поиск заказов пользователя по названию блюда (case-insensitive)
    
    Args:
        session: Сессия базы данных
        user_id: ID пользователя
        dish_name: Название блюда для поиска (частичное совпадение)
    
    Returns:
        list[Order]: Список заказов, содержащих блюдо с указанным названием
    """
    from models.dish import Dish
    from models.order import OrderItem
    
    # Ищем блюда по названию (case-insensitive)
    dish_query = select(Dish.id).where(Dish.name.ilike(f"%{dish_name}%"))
    dish_result = await session.execute(dish_query)
    dish_ids = [row[0] for row in dish_result.all()]
    
    if not dish_ids:
        return []
    
    # Ищем заказы, содержащие эти блюда
    order_items_query = select(OrderItem.order_id).where(OrderItem.dish_id.in_(dish_ids))
    order_items_result = await session.execute(order_items_query)
    order_ids = list(set([row[0] for row in order_items_result.all()]))
    
    if not order_ids:
        return []
    
    # Получаем заказы пользователя
    query = select(Order).options(selectinload(Order.items), selectinload(Order.user)).where(
        and_(
            Order.user_id == user_id,
            Order.id.in_(order_ids)
        )
    ).order_by(Order.order_date.desc())
    
    result = await session.execute(query)
    return list(result.scalars().all())

async def get_order_by_id(session: AsyncSession, order_id: int, user_id: Optional[int] = None) -> Optional[Order]:
    from models.order import OrderItem
    query = select(Order).options(
        selectinload(Order.items).selectinload(OrderItem.dish),
        selectinload(Order.user),
        selectinload(Order.cafe)
    ).where(Order.id == order_id)
    if user_id:
        query = query.where(Order.user_id == user_id)
    
    result = await session.execute(query)
    return result.scalar_one_or_none()

async def cancel_order(session: AsyncSession, order_id: int, user_id: int) -> bool:
    order = await get_order_by_id(session, order_id, user_id)
    if not order:
        return False
    
    if order.status == OrderStatus.CANCELLED:
        return False
    
    from services.cafe_service import get_cafe_menu_for_date
    
    if order.cafe_id:
        date_start = order.order_date.replace(hour=0, minute=0, second=0, microsecond=0)
        date_end = order.order_date.replace(hour=23, minute=59, second=59, microsecond=999999)
        
        from models.cafe_menu import CafeMenu
        for item in order.items:
            result = await session.execute(
                select(CafeMenu).where(
                    CafeMenu.cafe_id == order.cafe_id,
                    CafeMenu.dish_id == item.dish_id,
                    CafeMenu.date >= date_start,
                    CafeMenu.date <= date_end
                )
            )
            menu_item = result.scalar_one_or_none()
            if menu_item:
                menu_item.available_quantity += item.quantity
    
    order.status = OrderStatus.CANCELLED
    await session.commit()
    return True

async def update_order_status(
    session: AsyncSession, 
    order_id: int, 
    new_status: OrderStatus, 
    admin_id: Optional[int] = None
) -> Optional[Order]:
    """
    Обновление статуса заказа (для администраторов)
    
    Args:
        session: Сессия базы данных
        order_id: ID заказа
        new_status: Новый статус заказа
        admin_id: ID администратора (опционально, для логирования)
    
    Returns:
        Order: Обновленный заказ или None, если заказ не найден
    """
    query = select(Order).options(
        selectinload(Order.items).selectinload(OrderItem.dish),
        selectinload(Order.user)
    ).where(Order.id == order_id)
    result = await session.execute(query)
    order = result.scalar_one_or_none()
    
    if not order:
        return None
    
    old_status = order.status
    
    if order.cafe_id:
        from models.cafe_menu import CafeMenu
        date_start = order.order_date.replace(hour=0, minute=0, second=0, microsecond=0)
        date_end = order.order_date.replace(hour=23, minute=59, second=59, microsecond=999999)
        
        if new_status == OrderStatus.CANCELLED and old_status != OrderStatus.CANCELLED:
            for item in order.items:
                result = await session.execute(
                    select(CafeMenu).where(
                        CafeMenu.cafe_id == order.cafe_id,
                        CafeMenu.dish_id == item.dish_id,
                        CafeMenu.date >= date_start,
                        CafeMenu.date <= date_end
                    )
                )
                menu_item = result.scalar_one_or_none()
                if menu_item:
                    menu_item.available_quantity += item.quantity
        elif old_status == OrderStatus.CANCELLED and new_status != OrderStatus.CANCELLED:
            for item in order.items:
                result = await session.execute(
                    select(CafeMenu).where(
                        CafeMenu.cafe_id == order.cafe_id,
                        CafeMenu.dish_id == item.dish_id,
                        CafeMenu.date >= date_start,
                        CafeMenu.date <= date_end
                    )
                )
                menu_item = result.scalar_one_or_none()
                if menu_item and menu_item.available_quantity >= item.quantity:
                    menu_item.available_quantity -= item.quantity
    
    order.status = new_status
    order.updated_at = datetime.now()
    await session.commit()
    await session.refresh(order)
    return order

async def get_all_orders(
    session: AsyncSession, 
    date: Optional[datetime] = None, 
    user_id: Optional[int] = None, 
    status: Optional[OrderStatus] = None,
    search_term: Optional[str] = None
) -> List[Order]:
    """
    Получает все заказы с опциональными фильтрами (для администраторов)
    
    Args:
        session: Сессия базы данных
        date: Фильтр по дате (опционально)
        user_id: Фильтр по пользователю (опционально)
        status: Фильтр по статусу (опционально)
        search_term: Поиск по имени пользователя, username или ID (опционально)
    
    Returns:
        list[Order]: Список заказов, отсортированный по дате (новые первые)
    """
    from models.order import OrderItem
    query = select(Order).options(
        selectinload(Order.items).selectinload(OrderItem.dish),
        selectinload(Order.user)
    )
    if date:
        date_start = date.replace(hour=0, minute=0, second=0, microsecond=0)
        date_end = date.replace(hour=23, minute=59, second=59, microsecond=999999)
        query = query.where(
            and_(
                Order.order_date >= date_start,
                Order.order_date <= date_end
            )
        )
    if user_id:
        query = query.where(Order.user_id == user_id)
    if status:
        query = query.where(Order.status == status)
    
    if search_term:
        from models.user import User
        query = query.join(User, Order.user_id == User.id)
        search_filter = or_(
            User.full_name.ilike(f"%{search_term}%"),
            User.username.ilike(f"%{search_term}%"),
            User.telegram_id.cast(String).ilike(f"%{search_term}%")
        )
        query = query.where(search_filter)
    
    query = query.order_by(Order.order_date.desc())
    
    result = await session.execute(query)
    return list(result.scalars().all())

async def update_order(
    session: AsyncSession, 
    order_id: int, 
    user_id: int, 
    items: Optional[List[Dict[str, Any]]] = None
) -> Optional[Order]:
    order = await get_order_by_id(session, order_id, user_id)
    if not order:
        return None
    
    if order.status != OrderStatus.PENDING:
        return None
    
    if items:
        for item in order.items:
            await session.delete(item)
        
        total_amount = sum(item['price'] * item['quantity'] for item in items)
        order.total_amount = total_amount
        
        for item_data in items:
            order_item = OrderItem(
                order_id=order.id,
                dish_id=item_data['dish_id'],
                quantity=item_data['quantity'],
                price=item_data['price']
            )
            session.add(order_item)
    
    order.updated_at = datetime.now()
    await session.commit()
    await session.refresh(order)
    return order

async def add_item_to_order(session: AsyncSession, order_id: int, user_id: int, dish_id: int, quantity: int, price: float) -> bool:
    order = await get_order_by_id(session, order_id, user_id)
    if not order or order.status != OrderStatus.PENDING:
        return False
    
    from models.dish import Dish
    result = await session.execute(select(Dish).where(Dish.id == dish_id))
    dish = result.scalar_one_or_none()
    if not dish:
        return False
    
    order_item = OrderItem(
        order_id=order.id,
        dish_id=dish_id,
        quantity=quantity,
        price=price
    )
    session.add(order_item)
    
    order.total_amount += price * quantity
    order.updated_at = datetime.now()
    
    await session.commit()
    return True

async def remove_item_from_order(session: AsyncSession, order_id: int, user_id: int, item_id: int) -> bool:
    order = await get_order_by_id(session, order_id, user_id)
    if not order or order.status != OrderStatus.PENDING:
        return False
    
    from models.order import OrderItem
    result = await session.execute(select(OrderItem).where(OrderItem.id == item_id, OrderItem.order_id == order_id))
    item = result.scalar_one_or_none()
    if not item:
        return False
    
    order.total_amount -= item.price * item.quantity
    await session.delete(item)
    
    if order.total_amount < 0:
        order.total_amount = 0
    
    order.updated_at = datetime.now()
    await session.commit()
    return True

