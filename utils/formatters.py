from datetime import datetime
from typing import List
from models.order import Order

def format_order(order: Order) -> str:
    """Форматирует заказ с улучшенным визуальным оформлением"""
    status_emoji = {
        "pending": "⏳",
        "confirmed": "✅",
        "cancelled": "❌",
        "completed": "🎉"
    }
    
    status_text = {
        "pending": "Ожидает подтверждения",
        "confirmed": "Подтвержден",
        "cancelled": "Отменен",
        "completed": "Выполнен"
    }
    
    emoji = status_emoji.get(order.status.value, "📋")
    status = status_text.get(order.status.value, order.status.value)
    
    items_text = "\n".join([
        f"  {i+1}️ {item.dish.name}\n"
        f"     {item.quantity} шт. × {item.price:.0f} ₽ = {item.price * item.quantity:.0f} ₽"
        for i, item in enumerate(order.items)
    ])
    
    return f"""
📦 Заказ #{order.id}

📅 Дата: {order.order_date.strftime('%d.%m.%Y')}
{emoji} Статус: {status}

🍽️ Блюда в заказе:
{items_text}

💰 Итого к оплате: {order.total_amount:.0f} ₽
    """

def format_date(date: datetime) -> str:
    return date.strftime('%d.%m.%Y')

def format_datetime(dt: datetime) -> str:
    return dt.strftime('%d.%m.%Y %H:%M')





