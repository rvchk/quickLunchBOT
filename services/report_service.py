from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from sqlalchemy.orm import selectinload
from datetime import datetime, timedelta
from models.order import Order, OrderStatus, OrderItem
from models.dish import Dish
from models.user import User
from models.cafe import Cafe
from collections import defaultdict
from typing import Dict, List, Optional, Any

async def get_orders_summary(session: AsyncSession, date: Optional[datetime] = None) -> Dict[str, Any]:
    query = select(Order).options(selectinload(Order.user), selectinload(Order.items))
    if date:
        date_start = date.replace(hour=0, minute=0, second=0, microsecond=0)
        date_end = date.replace(hour=23, minute=59, second=59, microsecond=999999)
        query = query.where(
            and_(
                Order.order_date >= date_start,
                Order.order_date <= date_end
            )
        )
    
    result = await session.execute(query)
    orders = list(result.scalars().all())
    
    total_amount = sum(order.total_amount for order in orders)
    unique_users = len(set(order.user_id for order in orders))
    
    return {
        "total_orders": len(orders),
        "total_amount": total_amount,
        "unique_users": unique_users,
        "orders": orders
    }

async def get_dish_statistics(session: AsyncSession, date: Optional[datetime] = None) -> List[Dict[str, Any]]:
    query = select(OrderItem, Dish, Order)
    query = query.join(Dish, OrderItem.dish_id == Dish.id)
    query = query.join(Order, OrderItem.order_id == Order.id)
    
    if date:
        date_start = date.replace(hour=0, minute=0, second=0, microsecond=0)
        date_end = date.replace(hour=23, minute=59, second=59, microsecond=999999)
        query = query.where(
            and_(
                Order.order_date >= date_start,
                Order.order_date <= date_end,
                Order.status != OrderStatus.CANCELLED
            )
        )
    else:
        query = query.where(Order.status != OrderStatus.CANCELLED)
    
    result = await session.execute(query)
    items = result.all()
    
    dish_stats = defaultdict(lambda: {"quantity": 0, "revenue": 0.0, "name": ""})
    
    for order_item, dish, order in items:
        dish_stats[dish.id]["name"] = dish.name
        dish_stats[dish.id]["quantity"] += order_item.quantity
        dish_stats[dish.id]["revenue"] += order_item.price * order_item.quantity
    
    stats_list = [
        {
            "dish_id": dish_id,
            "name": stats["name"],
            "quantity": stats["quantity"],
            "revenue": stats["revenue"]
        }
        for dish_id, stats in dish_stats.items()
    ]
    
    return sorted(stats_list, key=lambda x: x["quantity"], reverse=True)

async def get_user_statistics(session: AsyncSession, date: Optional[datetime] = None) -> List[Dict[str, Any]]:
    query = select(Order, User)
    query = query.join(User, Order.user_id == User.id)
    
    if date:
        date_start = date.replace(hour=0, minute=0, second=0, microsecond=0)
        date_end = date.replace(hour=23, minute=59, second=59, microsecond=999999)
        query = query.where(
            and_(
                Order.order_date >= date_start,
                Order.order_date <= date_end,
                Order.status != OrderStatus.CANCELLED
            )
        )
    else:
        query = query.where(Order.status != OrderStatus.CANCELLED)
    
    result = await session.execute(query)
    orders = result.all()
    
    user_stats = defaultdict(lambda: {"orders_count": 0, "total_amount": 0.0, "name": ""})
    
    for order, user in orders:
        user_stats[user.id]["name"] = user.full_name or user.username or f"User {user.telegram_id}"
        user_stats[user.id]["orders_count"] += 1
        user_stats[user.id]["total_amount"] += order.total_amount
    
    stats_list = [
        {
            "user_id": user_id,
            "name": stats["name"],
            "orders_count": stats["orders_count"],
            "total_amount": stats["total_amount"],
            "avg_order": stats["total_amount"] / stats["orders_count"] if stats["orders_count"] > 0 else 0
        }
        for user_id, stats in user_stats.items()
    ]
    
    return sorted(stats_list, key=lambda x: x["orders_count"], reverse=True)

async def get_cafe_report(session: AsyncSession, date: datetime, cafe_id: Optional[int] = None) -> Dict[str, Any]:
    """
    Генерирует отчет по заказам для кафе
    
    Args:
        session: Сессия базы данных
        date: Дата для отчета
        cafe_id: ID кафе (опционально, если None - отчет по всем кафе)
    
    Returns:
        Dict с данными отчета по кафе
    """
    date_start = date.replace(hour=0, minute=0, second=0, microsecond=0)
    date_end = date.replace(hour=23, minute=59, second=59, microsecond=999999)
    
    query = select(Order).options(
        selectinload(Order.user),
        selectinload(Order.items).selectinload(OrderItem.dish),
        selectinload(Order.cafe)
    ).where(
        and_(
            Order.order_date >= date_start,
            Order.order_date <= date_end,
            Order.status != OrderStatus.CANCELLED
        )
    )
    
    if cafe_id:
        query = query.where(Order.cafe_id == cafe_id)
    
    result = await session.execute(query)
    orders = list(result.scalars().all())
    
    if cafe_id:
        cafe_result = await session.execute(select(Cafe).where(Cafe.id == cafe_id))
        cafe = cafe_result.scalar_one_or_none()
        cafe_name = cafe.name if cafe else f"Кафе #{cafe_id}"
    else:
        cafe_name = "Все кафе"
    
    report_by_cafe = defaultdict(lambda: {
        "cafe_name": "",
        "orders": [],
        "total_amount": 0.0,
        "total_items": 0,
        "users": set()
    })
    
    for order in orders:
        cafe_key = order.cafe_id if order.cafe_id else 0
        cafe_name_for_order = order.cafe.name if order.cafe else "Без кафе"
        
        report_by_cafe[cafe_key]["cafe_name"] = cafe_name_for_order
        report_by_cafe[cafe_key]["orders"].append(order)
        report_by_cafe[cafe_key]["total_amount"] += order.total_amount
        report_by_cafe[cafe_key]["total_items"] += sum(item.quantity for item in order.items)
        report_by_cafe[cafe_key]["users"].add(order.user_id)
    
    cafe_reports = []
    for cafe_id_key, data in report_by_cafe.items():
        orders_detail = []
        for order in data["orders"]:
            items_text = ", ".join([f"{item.dish.name} x{item.quantity}" for item in order.items])
            orders_detail.append({
                "user_name": order.user.full_name or order.user.username or f"ID {order.user.telegram_id}",
                "telegram_id": order.user.telegram_id,
                "items": items_text,
                "total": order.total_amount,
                "delivery_time": order.delivery_time.strftime("%H:%M") if order.delivery_time else None,
                "delivery_type": order.delivery_type.value if order.delivery_type else None
            })
        
        cafe_reports.append({
            "cafe_id": cafe_id_key,
            "cafe_name": data["cafe_name"],
            "total_orders": len(data["orders"]),
            "total_amount": data["total_amount"],
            "total_items": data["total_items"],
            "unique_users": len(data["users"]),
            "orders": orders_detail
        })
    
    return {
        "date": date,
        "cafe_name": cafe_name,
        "cafes": cafe_reports,
        "total_orders": len(orders),
        "total_amount": sum(r["total_amount"] for r in cafe_reports),
        "total_items": sum(r["total_items"] for r in cafe_reports)
    }

async def get_user_personal_statistics(session: AsyncSession, user_id: int, date_from: Optional[datetime] = None, date_to: Optional[datetime] = None) -> Dict[str, Any]:
    """
    Получает личную статистику пользователя
    
    Args:
        session: Сессия базы данных
        user_id: ID пользователя
        date_from: Начальная дата периода (опционально)
        date_to: Конечная дата периода (опционально)
    
    Returns:
        Dict с личной статистикой пользователя
    """
    query = select(Order).options(
        selectinload(Order.items).selectinload(OrderItem.dish)
    ).where(
        and_(
            Order.user_id == user_id,
            Order.status != OrderStatus.CANCELLED
        )
    )
    
    if date_from:
        query = query.where(Order.order_date >= date_from)
    if date_to:
        query = query.where(Order.order_date <= date_to)
    
    result = await session.execute(query)
    orders = list(result.scalars().all())
    
    total_amount = sum(order.total_amount for order in orders)
    total_items = sum(sum(item.quantity for item in order.items) for order in orders)
    
    favorite_dishes = defaultdict(lambda: {"name": "", "count": 0, "total_amount": 0.0})
    for order in orders:
        for item in order.items:
            favorite_dishes[item.dish_id]["name"] = item.dish.name
            favorite_dishes[item.dish_id]["count"] += item.quantity
            favorite_dishes[item.dish_id]["total_amount"] += item.price * item.quantity
    
    top_dishes = sorted(
        [
            {
                "dish_id": dish_id,
                "name": stats["name"],
                "count": stats["count"],
                "total_amount": stats["total_amount"]
            }
            for dish_id, stats in favorite_dishes.items()
        ],
        key=lambda x: x["count"],
        reverse=True
    )[:5]
    
    avg_order = total_amount / len(orders) if len(orders) > 0 else 0
    
    return {
        "user_id": user_id,
        "orders_count": len(orders),
        "total_amount": total_amount,
        "total_items": total_items,
        "avg_order": avg_order,
        "top_dishes": top_dishes,
        "date_from": date_from,
        "date_to": date_to
    }

async def get_popular_dishes(session: AsyncSession, limit: int = 5) -> List[Dict[str, Any]]:
    """
    Получает топ популярных блюд на основе количества заказов
    
    Args:
        session: Сессия базы данных
        limit: Количество блюд в топе
    
    Returns:
        List с популярными блюдами
    """
    stats = await get_dish_statistics(session, date=None)
    return stats[:limit]








