from sqlalchemy import Column, Integer, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from database.base import Base

class CafeMenu(Base):
    __tablename__ = "cafe_menu"
    
    id = Column(Integer, primary_key=True)
    cafe_id = Column(Integer, ForeignKey("cafes.id"), nullable=False)
    dish_id = Column(Integer, ForeignKey("dishes.id"), nullable=False)
    date = Column(DateTime, nullable=False)
    available_quantity = Column(Integer, default=0)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    
    cafe = relationship("Cafe", back_populates="menu_items")
    dish = relationship("Dish", back_populates="cafe_menu_items")

