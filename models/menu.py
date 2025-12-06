from sqlalchemy import Column, Integer, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from database.base import Base

class Menu(Base):
    __tablename__ = "menu"
    
    id = Column(Integer, primary_key=True)
    date = Column(DateTime, nullable=False)
    dish_id = Column(Integer, ForeignKey("dishes.id"), nullable=False)
    available_quantity = Column(Integer, default=0)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    
    dish = relationship("Dish", back_populates="menu_items")

