import pytest
from datetime import datetime, timedelta
from utils.validators import (
    validate_order_date,
    check_order_deadline,
    validate_quantity,
    validate_dish_availability,
    validate_order_can_be_cancelled
)

class TestValidateOrderDate:
    def test_past_date(self):
        past_date = datetime.now() - timedelta(days=1)
        is_valid, error_msg = validate_order_date(past_date)
        assert not is_valid
        assert "прошедшую" in error_msg
    
    def test_future_date_too_far(self):
        future_date = datetime.now() + timedelta(days=31)
        is_valid, error_msg = validate_order_date(future_date)
        assert not is_valid
        assert "30 дней" in error_msg
    
    def test_valid_date(self):
        valid_date = datetime.now() + timedelta(days=1)
        is_valid, error_msg = validate_order_date(valid_date)
        assert is_valid
        assert error_msg == ""

class TestCheckOrderDeadline:
    def test_deadline_passed_today(self):
        from config.settings import settings
        now = datetime.now()
        today_order = now.replace(hour=settings.ORDER_DEADLINE_HOUR + 1, minute=0)
        can_order, error_msg = check_order_deadline(today_order)
        assert not can_order
        assert "дедлайн" in error_msg.lower() or "истек" in error_msg.lower()
    
    def test_deadline_not_passed_today(self):
        from config.settings import settings
        now = datetime.now()
        today_order = now.replace(hour=settings.ORDER_DEADLINE_HOUR - 1, minute=0)
        can_order, error_msg = check_order_deadline(today_order)
        assert can_order
    
    def test_future_date(self):
        future_date = datetime.now() + timedelta(days=1)
        can_order, error_msg = check_order_deadline(future_date)
        assert can_order

class TestValidateQuantity:
    def test_zero_quantity(self):
        is_valid, error_msg = validate_quantity(0)
        assert not is_valid
        assert "больше 0" in error_msg
    
    def test_negative_quantity(self):
        is_valid, error_msg = validate_quantity(-1)
        assert not is_valid
    
    def test_too_large_quantity(self):
        is_valid, error_msg = validate_quantity(11, max_quantity=10)
        assert not is_valid
        assert "Максимальное" in error_msg
    
    def test_valid_quantity(self):
        is_valid, error_msg = validate_quantity(5)
        assert is_valid
        assert error_msg == ""

class TestValidateDishAvailability:
    def test_no_availability(self):
        is_valid, error_msg = validate_dish_availability(0, 1)
        assert not is_valid
        assert "закончилось" in error_msg
    
    def test_insufficient_availability(self):
        is_valid, error_msg = validate_dish_availability(3, 5)
        assert not is_valid
        assert "Доступно только" in error_msg
    
    def test_sufficient_availability(self):
        is_valid, error_msg = validate_dish_availability(10, 5)
        assert is_valid
        assert error_msg == ""

class TestValidateOrderCancellation:
    def test_cancel_after_deadline(self):
        from config.settings import settings
        now = datetime.now()
        order_date = now.replace(hour=settings.ORDER_DEADLINE_HOUR + 1, minute=0)
        can_cancel, error_msg = validate_order_can_be_cancelled(order_date)
        assert not can_cancel
        assert "после дедлайна" in error_msg
    
    def test_cancel_before_deadline(self):
        from config.settings import settings
        now = datetime.now()
        order_date = now.replace(hour=settings.ORDER_DEADLINE_HOUR - 1, minute=0)
        can_cancel, error_msg = validate_order_can_be_cancelled(order_date)
        assert can_cancel













