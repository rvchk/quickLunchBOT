from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from database.base import Base

class Cafe(Base):
    __tablename__ = "cafes"
    
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    office_id = Column(Integer, ForeignKey("offices.id"), nullable=True)
    contact_info = Column(String, nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    
    office = relationship("Office", back_populates="cafes")
    menu_items = relationship("CafeMenu", back_populates="cafe", cascade="all, delete-orphan")
    orders = relationship("Order", back_populates="cafe")

