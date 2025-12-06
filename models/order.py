from sqlalchemy import Column, Integer, Float, DateTime, ForeignKey, Enum, Index, String
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
import enum
from database.base import Base

class OrderStatus(enum.Enum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    CANCELLED = "cancelled"
    COMPLETED = "completed"

class DeliveryType(enum.Enum):
    DELIVERY = "delivery"
    PICKUP = "pickup"

class Order(Base):
    __tablename__ = "orders"
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    cafe_id = Column(Integer, ForeignKey("cafes.id"), nullable=True, index=True)
    order_date = Column(DateTime, nullable=False, index=True)
    delivery_time = Column(DateTime, nullable=True)
    delivery_type = Column(Enum(DeliveryType), nullable=True)
    status = Column(Enum(OrderStatus), default=OrderStatus.PENDING, index=True)
    total_amount = Column(Float, default=0.0)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    
    user = relationship("User", back_populates="orders")
    cafe = relationship("Cafe", back_populates="orders")
    items = relationship("OrderItem", back_populates="order", cascade="all, delete-orphan")
    
    __table_args__ = (
        Index('idx_order_user_date', 'user_id', 'order_date'),
        Index('idx_order_date_status', 'order_date', 'status'),
    )

class OrderItem(Base):
    __tablename__ = "order_items"
    
    id = Column(Integer, primary_key=True)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=False)
    dish_id = Column(Integer, ForeignKey("dishes.id"), nullable=False)
    quantity = Column(Integer, nullable=False)
    price = Column(Float, nullable=False)
    
    order = relationship("Order", back_populates="items")
    dish = relationship("Dish", back_populates="order_items")

