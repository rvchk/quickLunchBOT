import pytest
from datetime import datetime
from models.user import User, UserRole
from models.dish import Dish
from models.order import Order, OrderItem, OrderStatus
from models.menu import Menu

class TestUserModel:
    def test_user_creation(self):
        user = User(
            telegram_id=123456,
            username="test_user",
            full_name="Test User",
            role=UserRole.USER
        )
        assert user.telegram_id == 123456
        assert user.username == "test_user"
        assert user.role == UserRole.USER
    
    def test_user_default_role(self):
        user = User(telegram_id=123456)
        assert user.role == UserRole.USER

class TestDishModel:
    def test_dish_creation(self):
        dish = Dish(
            name="Борщ",
            description="Классический борщ",
            price=250.0,
            category="Первые блюда"
        )
        assert dish.name == "Борщ"
        assert dish.price == 250.0
        assert dish.available == True

class TestOrderModel:
    def test_order_creation(self):
        order = Order(
            user_id=1,
            order_date=datetime.now(),
            status=OrderStatus.PENDING,
            total_amount=500.0
        )
        assert order.status == OrderStatus.PENDING
        assert order.total_amount == 500.0
    
    def test_order_item_creation(self):
        item = OrderItem(
            order_id=1,
            dish_id=1,
            quantity=2,
            price=250.0
        )
        assert item.quantity == 2
        assert item.price == 250.0

class TestMenuModel:
    def test_menu_creation(self):
        menu = Menu(
            date=datetime.now(),
            dish_id=1,
            available_quantity=50
        )
        assert menu.available_quantity == 50













