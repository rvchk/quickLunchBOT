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
        f"  {i+1}️⃣ <b>{item.dish.name}</b>\n"
        f"     {item.quantity} шт. × {item.price:.0f} ₽ = <b>{item.price * item.quantity:.0f} ₽</b>"
        for i, item in enumerate(order.items)
    ])
    
    return f"""
📦 <b>Заказ #{order.id}</b>

📅 <b>Дата:</b> {order.order_date.strftime('%d.%m.%Y')}
{emoji} <b>Статус:</b> {status}

🍽️ <b>Блюда в заказе:</b>
{items_text}

💰 <b>Итого к оплате:</b> {order.total_amount:.0f} ₽
    """

def format_date(date: datetime) -> str:
    return date.strftime('%d.%m.%Y')

def format_datetime(dt: datetime) -> str:
    return dt.strftime('%d.%m.%Y %H:%M')





