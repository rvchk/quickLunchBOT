import pytest
from datetime import datetime
from utils.formatters import format_date, format_datetime, format_order
from models.order import Order, OrderItem, OrderStatus
from models.user import User, UserRole
from models.dish import Dish

class TestFormatDate:
    def test_format_date(self):
        date = datetime(2024, 12, 1)
        result = format_date(date)
        assert result == "01.12.2024"
    
    def test_format_datetime(self):
        dt = datetime(2024, 12, 1, 14, 30)
        result = format_datetime(dt)
        assert "01.12.2024" in result
        assert "14:30" in result

class TestFormatOrder:
    def test_format_order(self):
        user = User(
            id=1,
            telegram_id=123456,
            username="test_user",
            full_name="Test User",
            role=UserRole.USER
        )
        
        dish1 = Dish(id=1, name="Борщ", price=250.0)
        dish2 = Dish(id=2, name="Салат", price=180.0)
        
        order = Order(
            id=1,
            user_id=1,
            order_date=datetime(2024, 12, 1),
            status=OrderStatus.PENDING,
            total_amount=430.0,
            user=user
        )
        
        item1 = OrderItem(
            id=1,
            order_id=1,
            dish_id=1,
            quantity=1,
            price=250.0,
            dish=dish1
        )
        
        item2 = OrderItem(
            id=2,
            order_id=1,
            dish_id=2,
            quantity=1,
            price=180.0,
            dish=dish2
        )
        
        order.items = [item1, item2]
        
        result = format_order(order)
        
        assert "Заказ #1" in result
        assert "Борщ" in result
        assert "Салат" in result
        assert "430" in result
        assert "₽" in result













