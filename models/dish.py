from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from database.base import Base

class Dish(Base):
    __tablename__ = "dishes"
    
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    description = Column(String, nullable=True)
    price = Column(Float, nullable=False)
    category = Column(String, nullable=True)
    available = Column(Boolean, default=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    
    order_items = relationship("OrderItem", back_populates="dish")
    menu_items = relationship("Menu", back_populates="dish")
    cafe_menu_items = relationship("CafeMenu", back_populates="dish")





