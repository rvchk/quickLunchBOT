from sqlalchemy import Column, Integer, DateTime, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from database.base import Base

class OrderDeadline(Base):
    __tablename__ = "order_deadlines"
    
    id = Column(Integer, primary_key=True)
    date = Column(DateTime, nullable=False)
    deadline_time = Column(DateTime, nullable=False)
    office_id = Column(Integer, ForeignKey("offices.id"), nullable=True)
    cafe_id = Column(Integer, ForeignKey("cafes.id"), nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    
    office = relationship("Office")
    cafe = relationship("Cafe")

