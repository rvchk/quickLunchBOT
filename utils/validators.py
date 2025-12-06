from datetime import datetime, time, timedelta
from typing import Tuple
from config.settings import settings

def validate_order_date(order_date: datetime) -> Tuple[bool, str]:
    today = datetime.now().date()
    max_future_date = today + timedelta(days=30)
    
    if order_date.date() < today:
        return False, "Нельзя заказать на прошедшую дату"
    
    if order_date.date() > max_future_date:
        return False, "Нельзя заказать более чем на 30 дней вперед"
    
    return True, ""

def check_order_deadline(order_date: datetime) -> Tuple[bool, str]:
    now = datetime.now()
    deadline_time = time(settings.ORDER_DEADLINE_HOUR, settings.ORDER_DEADLINE_MINUTE)
    
    if order_date.date() == now.date():
        current_time = now.time()
        if current_time >= deadline_time:
            return False, f"Дедлайн заказа на сегодня истек. Заказы принимаются до {settings.ORDER_DEADLINE_HOUR:02d}:{settings.ORDER_DEADLINE_MINUTE:02d}"
    elif order_date.date() < now.date():
        deadline_datetime = datetime.combine(order_date.date(), deadline_time)
        if now >= deadline_datetime:
            return False, f"Дедлайн заказа на {order_date.strftime('%d.%m.%Y')} истек. Заказы принимаются до {settings.ORDER_DEADLINE_HOUR:02d}:{settings.ORDER_DEADLINE_MINUTE:02d}"
    return True, ""

def validate_quantity(quantity: int, max_quantity: int = 10) -> Tuple[bool, str]:
    if quantity < 1:
        return False, "Количество должно быть больше 0"
    if quantity > max_quantity:
        return False, f"Максимальное количество: {max_quantity}"
    return True, ""

def validate_dish_availability(available_quantity: int, requested_quantity: int) -> Tuple[bool, str]:
    if available_quantity < 1:
        return False, "Блюдо закончилось"
    if available_quantity < requested_quantity:
        return False, f"Доступно только {available_quantity} порций"
    return True, ""

def validate_order_can_be_cancelled(order_date: datetime) -> Tuple[bool, str]:
    now = datetime.now()
    deadline_time = now.replace(
        hour=settings.ORDER_DEADLINE_HOUR,
        minute=settings.ORDER_DEADLINE_MINUTE,
        second=0,
        microsecond=0
    )
    
    if order_date.date() == now.date() and now >= deadline_time:
        return False, "Нельзя отменить заказ после дедлайна"
    
    return True, ""

